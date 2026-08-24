from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .adaptive_db import AdaptiveDB
from .mastery import BKTParameters, update_bkt
from .models import Topic, clamp


@dataclass(frozen=True)
class QuestionOutcome:
    question_id: str
    topic_id: str
    correct: bool
    response_time_seconds: float | None = None
    confidence: float | None = None
    knowledge_component_id: str | None = None


def record_question(
    db: AdaptiveDB,
    outcome: QuestionOutcome,
    topic: Topic,
    attempted_at: datetime,
    params: BKTParameters = BKTParameters(),
) -> dict[str, object]:
    attempt_id = db.record_question_attempt(
        outcome.question_id,
        outcome.topic_id,
        attempted_at,
        outcome.correct,
        outcome.knowledge_component_id,
        outcome.response_time_seconds,
        outcome.confidence,
    )
    state = None
    if outcome.knowledge_component_id:
        kc = next((x for x in db.load_knowledge_components(topic.id) if x.id == outcome.knowledge_component_id), None)
        state = db.get_knowledge_state(outcome.knowledge_component_id, kc.initial_mastery if kc else 0.50)
        state = update_bkt(state, outcome.correct, attempted_at, params)
        db.save_knowledge_state(state)
    db.record_event("question_attempt", {"attempt_id": attempt_id, "correct": outcome.correct}, topic.id)
    return {
        "attempt_id": attempt_id,
        "topic_id": outcome.topic_id,
        "correct": outcome.correct,
        "mastery_probability": state.mastery_probability if state else clamp(topic.mastery),
        "uncertainty": state.uncertainty if state else topic.mastery_uncertainty,
    }
