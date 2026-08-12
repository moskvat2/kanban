from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.security_deps import get_board_for_user, get_current_user
from app.db.database import get_db
from app.models import Board, Card, Column, User
from app.schemas.board import (
    BoardCreate,
    BoardDetail,
    BoardOut,
    BoardSummary,
    BoardUpdate,
    ColumnCreate,
    ColumnReorderItem,
    ColumnUpdate,
)

router = APIRouter()


@router.get("", response_model=list[BoardSummary])
def list_boards(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    boards = db.scalars(
        select(Board)
        .where(Board.owner_id == user.id)
        .options(selectinload(Board.columns).selectinload(Column.cards))
        .order_by(Board.created_at.desc())
    ).all()
    return [_board_summary(board) for board in boards]


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
    return _board_summary(board)


@router.get("/{board_id}", response_model=BoardDetail)
def get_board(
    board: Board = Depends(get_board_for_user),
    db: Session = Depends(get_db),
):
    return db.scalar(
        select(Board)
        .where(Board.id == board.id)
        .options(selectinload(Board.columns).selectinload(Column.cards))
    )


@router.patch("/{board_id}", response_model=BoardOut)
def update_board(
    payload: BoardUpdate,
    board: Board = Depends(get_board_for_user),
    db: Session = Depends(get_db),
):
    if payload.title is not None:
        board.title = payload.title
    if payload.description is not None:
        board.description = payload.description
    db.commit()
    db.refresh(board)
    return board


@router.delete("/{board_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_board(
    board: Board = Depends(get_board_for_user),
    db: Session = Depends(get_db),
):
    db.delete(board)
    db.commit()


@router.post("/{board_id}/columns", response_model=BoardDetail, status_code=status.HTTP_201_CREATED)
def create_column(
    payload: ColumnCreate,
    board: Board = Depends(get_board_for_user),
    db: Session = Depends(get_db),
):
    max_position = max((c.position for c in board.columns), default=-1)
    db.add(Column(board_id=board.id, title=payload.title, position=max_position + 1))
    db.commit()
    return db.scalar(
        select(Board)
        .where(Board.id == board.id)
        .options(selectinload(Board.columns).selectinload(Column.cards))
    )


@router.patch("/columns/{column_id}", response_model=BoardDetail)
def update_column(
    column_id: int,
    payload: ColumnUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    column = _get_owned_column(db, user, column_id)
    if payload.title is not None:
        column.title = payload.title
    db.commit()
    return _get_board_detail(db, column.board_id)


@router.delete("/columns/{column_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_column(
    column_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    column = _get_owned_column(db, user, column_id)
    board_id = column.board_id
    db.delete(column)
    db.commit()
    _renumber_columns(db, board_id)


@router.patch("/{board_id}/columns/reorder", response_model=BoardDetail)
def reorder_columns(
    items: list[ColumnReorderItem],
    board: Board = Depends(get_board_for_user),
    db: Session = Depends(get_db),
):
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
    return _get_board_detail(db, board.id)


def _get_owned_column(db: Session, user: User, column_id: int) -> Column:
    column = db.get(Column, column_id)
    if column is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coluna não encontrada")
    if column.board.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para acessar este recurso",
        )
    return column


def _get_board_detail(db: Session, board_id: int) -> Board:
    board = db.scalar(
        select(Board)
        .where(Board.id == board_id)
        .options(selectinload(Board.columns).selectinload(Column.cards))
    )
    if board is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quadro não encontrado")
    return board


def _renumber_columns(db: Session, board_id: int) -> None:
    columns = db.scalars(
        select(Column).where(Column.board_id == board_id).order_by(Column.position)
    ).all()
    for index, column in enumerate(columns):
        column.position = index
    db.commit()


def _board_card_counts(columns: list[Column]) -> tuple[int, int]:
    total_cards = sum(len(c.cards) for c in columns)
    last_position = max((c.position for c in columns), default=-1)
    done_cards = (
        sum(len(c.cards) for c in columns if c.position == last_position)
        if last_position >= 0
        else 0
    )
    return total_cards, done_cards


def _board_progress(columns: list[Column]) -> float:
    total_cards, done_cards = _board_card_counts(columns)
    if total_cards == 0:
        return 0.0
    return done_cards / total_cards


def _board_summary(board: Board) -> BoardSummary:
    columns = board.columns
    total_cards, done_cards = _board_card_counts(columns)
    return BoardSummary(
        id=board.id,
        title=board.title,
        description=board.description,
        owner_id=board.owner_id,
        created_at=board.created_at,
        columns_count=len(columns),
        cards_count=total_cards,
        done_cards=done_cards,
        progress=round(_board_progress(columns), 4),
    )
