from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CardCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)


class CardUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)


class CardMove(BaseModel):
    column_id: int
    position: int


class CardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    column_id: int
    title: str
    description: str | None
    position: int
    created_at: datetime


class ColumnCreate(BaseModel):
    title: str = Field(min_length=1, max_length=150)


class ColumnUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=150)


class ColumnReorderItem(BaseModel):
    id: int
    position: int


class ColumnOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    board_id: int
    title: str
    position: int
    created_at: datetime
    cards: list[CardOut] = []


class BoardCreate(BaseModel):
    title: str = Field(min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=5000)


class BoardUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=5000)


class BoardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    owner_id: int
    created_at: datetime


class BoardSummary(BoardOut):
    progress: float
    cards_count: int
    done_cards: int
    columns_count: int


class BoardDetail(BoardOut):
    columns: list[ColumnOut] = []
