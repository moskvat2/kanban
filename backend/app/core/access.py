from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.security_deps import get_current_user
from app.db.database import get_db
from app.models import Board, BoardMember, Card, Column, User

OWNER = "owner"
EDITOR = "editor"
VIEWER = "viewer"

WRITE_ROLES = (OWNER, EDITOR)


@dataclass
class BoardAccess:
    board: Board
    role: str
    user: User


@dataclass
class ColumnAccess:
    column: Column
    role: str
    user: User


@dataclass
class CardAccess:
    card: Card
    role: str
    user: User


def board_role(db: Session, board: Board, user: User) -> str | None:
    """Retorna o papel do usuário em um quadro (None = sem acesso)."""
    if board.owner_id == user.id:
        return OWNER
    member = db.scalar(
        select(BoardMember).where(
            BoardMember.board_id == board.id,
            BoardMember.user_id == user.id,
        )
    )
    return member.role if member else None


def require_role(role: str | None, *allowed: str) -> None:
    if role is None or role not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para esta ação",
        )


def get_board_access(
    board_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> BoardAccess:
    board = db.scalar(
        select(Board)
        .options(
            joinedload(Board.owner),
            selectinload(Board.columns).selectinload(Column.cards),
            selectinload(Board.members).selectinload(BoardMember.user),
        )
        .where(Board.id == board_id)
    )
    if board is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quadro não encontrado")
    role = board_role(db, board, user)
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para acessar este recurso",
        )
    return BoardAccess(board=board, role=role, user=user)


def get_column_access(
    column_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ColumnAccess:
    column = db.scalar(
        select(Column).options(joinedload(Column.board)).where(Column.id == column_id)
    )
    if column is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coluna não encontrada")
    role = board_role(db, column.board, user)
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para acessar este recurso",
        )
    return ColumnAccess(column=column, role=role, user=user)


def get_card_access(
    card_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CardAccess:
    card = db.scalar(
        select(Card)
        .options(joinedload(Card.column).joinedload(Column.board))
        .where(Card.id == card_id)
    )
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cartão não encontrado")
    role = board_role(db, card.column.board, user)
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para acessar este recurso",
        )
    return CardAccess(card=card, role=role, user=user)
