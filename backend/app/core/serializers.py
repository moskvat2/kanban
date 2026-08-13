from app.core.access import OWNER
from app.models import Board, Column
from app.schemas.board import BoardDetail, BoardSummary


def board_card_counts(columns: list[Column]) -> tuple[int, int]:
    total_cards = sum(len(c.cards) for c in columns)
    last_position = max((c.position for c in columns), default=-1)
    done_cards = (
        sum(len(c.cards) for c in columns if c.position == last_position)
        if last_position >= 0
        else 0
    )
    return total_cards, done_cards


def board_progress(columns: list[Column]) -> float:
    total_cards, done_cards = board_card_counts(columns)
    if total_cards == 0:
        return 0.0
    return done_cards / total_cards


def board_summary(board: Board, role: str) -> BoardSummary:
    columns = board.columns
    total_cards, done_cards = board_card_counts(columns)
    return BoardSummary(
        id=board.id,
        title=board.title,
        description=board.description,
        owner_id=board.owner_id,
        created_at=board.created_at,
        columns_count=len(columns),
        cards_count=total_cards,
        done_cards=done_cards,
        progress=round(board_progress(columns), 4),
        role=role,
        is_owner=role == OWNER,
        members_count=1 + len(board.members),
    )


def board_detail(board: Board, role: str) -> BoardDetail:
    detail = BoardDetail.model_validate(board)
    detail.role = role
    detail.is_owner = role == OWNER
    detail.members_count = 1 + len(board.members)
    return detail
