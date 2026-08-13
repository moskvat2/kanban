import asyncio
from collections import defaultdict

from fastapi import WebSocket
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.access import OWNER, board_role
from app.core.serializers import board_detail
from app.db.database import SessionLocal
from app.models import Board, BoardMember, Column, User
from app.schemas.board import MemberOut


class BoardConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[int, set[WebSocket]] = defaultdict(set)
        self._user_ids: dict[WebSocket, int] = {}
        self.loop: asyncio.AbstractEventLoop | None = None

    async def connect(self, board_id: int, websocket: WebSocket, user_id: int) -> None:
        await websocket.accept()
        if self.loop is None:
            self.loop = asyncio.get_running_loop()
        self._connections[board_id].add(websocket)
        self._user_ids[websocket] = user_id

    def disconnect(self, board_id: int, websocket: WebSocket) -> None:
        self._connections.get(board_id, set()).discard(websocket)
        self._user_ids.pop(websocket, None)
        if not self._connections.get(board_id):
            self._connections.pop(board_id, None)

    def is_subscribed(self, board_id: int) -> bool:
        return bool(self._connections.get(board_id))

    async def broadcast_board(self, board_id: int) -> None:
        connections = list(self._connections.get(board_id, []))
        if not connections:
            return
        with SessionLocal() as db:
            board = _load_board(db, board_id)
            if board is None:
                return
            for ws in connections:
                user = db.get(User, self._user_ids.get(ws))
                role = board_role(db, board, user) if user else None
                if role is None:
                    await _safe_send(ws, {"type": "board_deleted"})
                    continue
                payload = board_detail(board, role).model_dump(mode="json")
                await _safe_send(ws, {"type": "board_update", "board": payload})

    async def broadcast_members(self, board_id: int) -> None:
        connections = list(self._connections.get(board_id, []))
        if not connections:
            return
        with SessionLocal() as db:
            board = _load_board(db, board_id)
            if board is None:
                return
            owner = MemberOut(
                user_id=board.owner_id,
                name=board.owner.name,
                email=board.owner.email,
                role=OWNER,
                created_at=board.created_at,
            )
            members = [
                MemberOut(
                    user_id=member.user_id,
                    name=member.user.name,
                    email=member.user.email,
                    role=member.role,
                    created_at=member.created_at,
                )
                for member in sorted(board.members, key=lambda m: m.created_at)
            ]
            payload = [owner, *members]
            dump = [member.model_dump(mode="json") for member in payload]
        for ws in connections:
            await _safe_send(ws, {"type": "members_update", "members": dump})

    async def broadcast_deleted(self, board_id: int) -> None:
        connections = list(self._connections.get(board_id, []))
        for ws in connections:
            await _safe_send(ws, {"type": "board_deleted"})


async def _safe_send(websocket: WebSocket, message: dict) -> None:
    try:
        await websocket.send_json(message)
    except Exception:
        pass


def _load_board(db: Session, board_id: int) -> Board | None:
    return db.scalar(
        select(Board)
        .options(
            joinedload(Board.owner),
            selectinload(Board.columns).selectinload(Column.cards),
            selectinload(Board.members).selectinload(BoardMember.user),
        )
        .where(Board.id == board_id)
    )


manager = BoardConnectionManager()


def notify_board_changed(board_id: int) -> None:
    if not manager.is_subscribed(board_id) or manager.loop is None:
        return
    asyncio.run_coroutine_threadsafe(manager.broadcast_board(board_id), manager.loop)


def notify_members_changed(board_id: int) -> None:
    if not manager.is_subscribed(board_id) or manager.loop is None:
        return
    asyncio.run_coroutine_threadsafe(manager.broadcast_members(board_id), manager.loop)


def notify_board_deleted(board_id: int) -> None:
    if not manager.is_subscribed(board_id) or manager.loop is None:
        return
    asyncio.run_coroutine_threadsafe(manager.broadcast_deleted(board_id), manager.loop)
