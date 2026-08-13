from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.access import (
    EDITOR,
    OWNER,
    CardAccess,
    ColumnAccess,
    board_role,
    get_card_access,
    get_column_access,
    require_role,
)
from app.core.ws import notify_board_changed
from app.db.database import get_db
from app.models import Card, Column
from app.routers.boards import _get_board_detail
from app.schemas.board import BoardDetail, CardCreate, CardMove, CardOut, CardUpdate

router = APIRouter()


@router.post("/columns/{column_id}/cards", response_model=BoardDetail, status_code=status.HTTP_201_CREATED)
def create_card(
    column_id: int,
    payload: CardCreate,
    db: Session = Depends(get_db),
    access: ColumnAccess = Depends(get_column_access),
):
    require_role(access.role, OWNER, EDITOR)
    column = access.column
    max_position = max((c.position for c in column.cards), default=-1)
    card = Card(
        column_id=column.id,
        title=payload.title,
        description=payload.description,
        position=max_position + 1,
    )
    db.add(card)
    db.commit()
    notify_board_changed(column.board_id)
    return _get_board_detail(db, column.board_id, access.role)


@router.patch("/cards/{card_id}", response_model=CardOut)
def update_card(
    card_id: int,
    payload: CardUpdate,
    db: Session = Depends(get_db),
    access: CardAccess = Depends(get_card_access),
):
    require_role(access.role, OWNER, EDITOR)
    card = access.card
    if payload.title is not None:
        card.title = payload.title
    if payload.description is not None:
        card.description = payload.description
    db.commit()
    db.refresh(card)
    notify_board_changed(card.column.board_id)
    return card


@router.delete("/cards/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_card(
    card_id: int,
    db: Session = Depends(get_db),
    access: CardAccess = Depends(get_card_access),
):
    require_role(access.role, OWNER, EDITOR)
    column_id = access.card.column_id
    board_id = access.card.column.board_id
    db.delete(access.card)
    db.commit()
    _renumber_cards(db, column_id)
    notify_board_changed(board_id)


@router.post("/cards/{card_id}/move", response_model=BoardDetail)
def move_card(
    card_id: int,
    payload: CardMove,
    db: Session = Depends(get_db),
    access: CardAccess = Depends(get_card_access),
):
    require_role(access.role, OWNER, EDITOR)
    card = access.card

    target_column = db.scalar(
        select(Column).options(joinedload(Column.board)).where(Column.id == payload.column_id)
    )
    if target_column is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coluna não encontrada")
    target_role = board_role(db, target_column.board, access.user)
    require_role(target_role, OWNER, EDITOR)

    source_column_id = card.column_id
    card.column_id = target_column.id
    card.position = payload.position

    db.flush()
    if source_column_id == target_column.id:
        _renumber_cards(db, target_column.id, moved_card=card, insert_index=payload.position)
    else:
        _renumber_cards(db, source_column_id)
        _renumber_cards(db, target_column.id, moved_card=card, insert_index=payload.position)
    db.commit()

    notify_board_changed(target_column.board_id)
    return _get_board_detail(db, target_column.board_id, target_role)


def _renumber_cards(
    db: Session, column_id: int, moved_card: Card | None = None, insert_index: int | None = None
) -> None:
    cards = db.scalars(
        select(Card).where(Card.column_id == column_id).order_by(Card.position, Card.id)
    ).all()
    if moved_card is not None:
        cards = [card for card in cards if card.id != moved_card.id]
        cards.insert(insert_index or 0, moved_card)
    for index, card in enumerate(cards):
        card.position = index
    db.flush()
