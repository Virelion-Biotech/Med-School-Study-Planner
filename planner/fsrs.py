from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone

from fsrs import Card, Rating, Scheduler

from .state import StudentFSRSState


class FSRSAdapter:
    """Thin application boundary around Py-FSRS.

    The rest of the planner stores a small, serializable state object and never
    depends directly on the third-party scheduler API.
    """

    def __init__(self, desired_retention: float = 0.90, enable_fuzzing: bool = False) -> None:
        self.scheduler = Scheduler(desired_retention=desired_retention, enable_fuzzing=enable_fuzzing)

    @staticmethod
    def _utc(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def new_state(self, topic_id: str) -> StudentFSRSState:
        card = Card()
        return self._state_from_card(topic_id, card)

    def review(
        self,
        state: StudentFSRSState,
        rating: int,
        reviewed_at: datetime | None = None,
        review_duration_ms: int | None = None,
    ) -> StudentFSRSState:
        if rating not in (1, 2, 3, 4):
            raise ValueError("FSRS rating must be 1..4")
        card = Card.from_json(state.card_json) if state.card_json else Card()
        reviewed_at = self._utc(reviewed_at) or datetime.now(timezone.utc)
        updated, _ = self.scheduler.review_card(
            card=card,
            rating=Rating(rating),
            review_datetime=reviewed_at,
            review_duration=review_duration_ms,
        )
        return self._state_from_card(state.topic_id, updated)

    def retrievability(self, state: StudentFSRSState, at: datetime | None = None) -> float:
        card = Card.from_json(state.card_json) if state.card_json else Card()
        return self.scheduler.get_card_retrievability(card, self._utc(at))

    @staticmethod
    def _state_from_card(topic_id: str, card: Card) -> StudentFSRSState:
        return StudentFSRSState(
            topic_id=topic_id,
            card_json=card.to_json(),
            stability=card.stability,
            difficulty=card.difficulty,
            retrievability=None,
            due=card.due,
            last_review=card.last_review,
            repetitions=card.reps,
            state=int(card.state),
        )
