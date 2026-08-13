from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.access import (
    EDITOR,
    OWNER,
    VIEWER,
    BoardAccess,
    ColumnAccess,
    get_board_access,
    get_column_access,
    require_role,
)
from app.core.security_deps import get_current_user
from app.core.serializers import board_detail, board_summary
from app.core.ws import notify_board_changed, notify_board_deleted, notify_members_changed
from app.db.database import get_db
from app.models import Board, BoardMember, Card, Column, User
from app.schemas.board import (
    BoardCreate,
    BoardDetail,
    BoardOut,
    BoardSummary,
    BoardUpdate,
    ColumnCreate,
    ColumnReorderItem,
    ColumnUpdate,
    MemberCreate,
    MemberOut,
    MemberRoleUpdate,
)

router = APIRouter()


@router.get("", response_model=list[BoardSummary])
def list_boards(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    member_subq = select(BoardMember.board_id).where(BoardMember.user_id == user.id)
    boards = db.scalars(
        select(Board)
        .where(or_(Board.owner_id == user.id, Board.id.in_(member_subq)))
        .options(
            selectinload(Board.columns).selectinload(Column.cards),
            selectinload(Board.members),
        )
        .order_by(Board.created_at.desc())
    ).all()
    return [board_summary(board, _board_role(board, user)) for board in boards]


@router.post("", response_model=BoardSummary, status_code=status.HTTP_201_CREATED)
def create_board(
    payload: BoardCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    board = Board(title=payload.title, description=payload.description, owner_id=user.id)
    db.add(board)
    db.commit()
    db.refresh(board)
    return board_summary(board, OWNER)


@router.get("/{board_id}", response_model=BoardDetail)
def get_board(access: BoardAccess = Depends(get_board_access)):
    return board_detail(access.board, access.role)


@router.patch("/{board_id}", response_model=BoardOut)
def update_board(
    payload: BoardUpdate,
    access: BoardAccess = Depends(get_board_access),
    db: Session = Depends(get_db),
):
    require_role(access.role, OWNER, EDITOR)
    board = access.board
    if payload.title is not None:
        board.title = payload.title
    if payload.description is not None:
        board.description = payload.description
    db.commit()
    db.refresh(board)
    notify_board_changed(board.id)
    return board


@router.delete("/{board_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_board(
    access: BoardAccess = Depends(get_board_access),
    db: Session = Depends(get_db),
):
    require_role(access.role, OWNER)
    notify_board_deleted(access.board.id)
    db.delete(access.board)
    db.commit()


@router.post("/{board_id}/columns", response_model=BoardDetail, status_code=status.HTTP_201_CREATED)
def create_column(
    payload: ColumnCreate,
    access: BoardAccess = Depends(get_board_access),
    db: Session = Depends(get_db),
):
    require_role(access.role, OWNER, EDITOR)
    board = access.board
    max_position = max((c.position for c in board.columns), default=-1)
    db.add(Column(board_id=board.id, title=payload.title, position=max_position + 1))
    db.commit()
    notify_board_changed(board.id)
    return _get_board_detail(db, board.id, access.role)


@router.patch("/columns/{column_id}", response_model=BoardDetail)
def update_column(
    column_id: int,
    payload: ColumnUpdate,
    db: Session = Depends(get_db),
    access: ColumnAccess = Depends(get_column_access),
):
    require_role(access.role, OWNER, EDITOR)
    if payload.title is not None:
        access.column.title = payload.title
    db.commit()
    notify_board_changed(access.column.board_id)
    return _get_board_detail(db, access.column.board_id, access.role)


@router.delete("/columns/{column_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_column(
    column_id: int,
    db: Session = Depends(get_db),
    access: ColumnAccess = Depends(get_column_access),
):
    require_role(access.role, OWNER, EDITOR)
    board_id = access.column.board_id
    db.delete(access.column)
    db.commit()
    _renumber_columns(db, board_id)
    notify_board_changed(board_id)


@router.patch("/{board_id}/columns/reorder", response_model=BoardDetail)
def reorder_columns(
    items: list[ColumnReorderItem],
    access: BoardAccess = Depends(get_board_access),
    db: Session = Depends(get_db),
):
    require_role(access.role, OWNER, EDITOR)
    board = access.board
    ids = {item.id for item in items}
    positions = {item.id: item.position for item in items}
    if len(ids) != len(board.columns) or ids != {c.id for c in board.columns}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lista de colunas incompatível com o quadro",
        )
    for column in board.columns:
        column.position = positions[column.id]
    db.commit()
    notify_board_changed(board.id)
    return _get_board_detail(db, board.id, access.role)


@router.get("/{board_id}/members", response_model=list[MemberOut])
def list_members(access: BoardAccess = Depends(get_board_access)):
    board = access.board
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
    return [owner, *members]


@router.post("/{board_id}/members", response_model=MemberOut, status_code=status.HTTP_201_CREATED)
def add_member(
    payload: MemberCreate,
    access: BoardAccess = Depends(get_board_access),
    db: Session = Depends(get_db),
):
    require_role(access.role, OWNER)
    board = access.board
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")
    if user.id == board.owner_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este usuário já é o dono do quadro",
        )
    existing = db.scalar(
        select(BoardMember).where(BoardMember.board_id == board.id, BoardMember.user_id == user.id)
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este usuário já é membro do quadro",
        )
    member = BoardMember(board_id=board.id, user_id=user.id, role=payload.role)
    db.add(member)
    db.commit()
    notify_members_changed(board.id)
    notify_board_changed(board.id)
    return MemberOut(
        user_id=user.id,
        name=user.name,
        email=user.email,
        role=payload.role,
        created_at=member.created_at,
    )


@router.patch("/{board_id}/members/{user_id}", response_model=MemberOut)
def update_member_role(
    user_id: int,
    payload: MemberRoleUpdate,
    access: BoardAccess = Depends(get_board_access),
    db: Session = Depends(get_db),
):
    require_role(access.role, OWNER)
    board = access.board
    if user_id == board.owner_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível alterar o papel do dono",
        )
    member = db.scalar(
        select(BoardMember).where(BoardMember.board_id == board.id, BoardMember.user_id == user_id)
    )
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membro não encontrado")
    member.role = payload.role
    db.commit()
    notify_members_changed(board.id)
    notify_board_changed(board.id)
    return MemberOut(
        user_id=member.user_id,
        name=member.user.name,
        email=member.user.email,
        role=member.role,
        created_at=member.created_at,
    )


@router.delete("/{board_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    user_id: int,
    access: BoardAccess = Depends(get_board_access),
    db: Session = Depends(get_db),
):
    board = access.board
    if user_id == board.owner_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível remover o dono do quadro",
        )
    if access.role != OWNER and access.user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para remover este membro",
        )
    member = db.scalar(
        select(BoardMember).where(BoardMember.board_id == board.id, BoardMember.user_id == user_id)
    )
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membro não encontrado")
    db.delete(member)
    db.commit()
    notify_members_changed(board.id)
    notify_board_changed(board.id)


def _board_role(board: Board, user: User) -> str:
    if board.owner_id == user.id:
        return OWNER
    for member in board.members:
        if member.user_id == user.id:
            return member.role
    return VIEWER


def _get_board_detail(db: Session, board_id: int, role: str) -> BoardDetail:
    board = db.scalar(
        select(Board)
        .where(Board.id == board_id)
        .options(
            selectinload(Board.columns).selectinload(Column.cards),
            selectinload(Board.members),
        )
    )
    if board is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quadro não encontrado")
    return board_detail(board, role)


def _renumber_columns(db: Session, board_id: int) -> None:
    columns = db.scalars(
        select(Column).where(Column.board_id == board_id).order_by(Column.position)
    ).all()
    for index, column in enumerate(columns):
        column.position = index
    db.commit()
