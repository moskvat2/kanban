from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security_deps import get_current_user
from app.db.database import get_db
from app.models import Card, Column, User
from app.schemas.board import BoardDetail
from app.routers.boards import _get_board_detail
from app.schemas.board import CardCreate, CardMove, CardOut, CardUpdate

router = APIRouter()


@router.post("/columns/{column_id}/cards", response_model=CardOut, status_code=status.HTTP_201_CREATED)
def create_card(
    column_id: int,
    payload: CardCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    column = _get_owned_column(db, user, column_id)
    max_position = max((c.position for c in column.cards), default=-1)
    card = Card(
        column_id=column.id,
        title=payload.title,
        description=payload.description,
        position=max_position + 1,
    )
    db.add(card)
    db.commit()
    db.refresh(card)
    return card


@router.patch("/cards/{card_id}", response_model=CardOut)
def update_card(
    card_id: int,
    payload: CardUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    card = _get_owned_card(db, user, card_id)
    if payload.title is not None:
        card.title = payload.title
    if payload.description is not None:
        card.description = payload.description
    db.commit()
    db.refresh(card)
    return card


@router.delete("/cards/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_card(
    card_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    card = _get_owned_card(db, user, card_id)
    column_id = card.column_id
    db.delete(card)
    db.commit()
    _renumber_cards(db, column_id)


@router.post("/cards/{card_id}/move", response_model=BoardDetail)
def move_card(
    card_id: int,
    payload: CardMove,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    card = _get_owned_card(db, user, card_id)
    target_column = _get_owned_column(db, user, payload.column_id)

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

    return _get_board_detail(db, target_column.board_id)


def _get_owned_card(db: Session, user: User, card_id: int) -> Card:
    card = db.get(Card, card_id)
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cartão não encontrado")
    if card.column.board.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para acessar este recurso",
        )
    return card


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
