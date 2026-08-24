from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime, timezone

from .adaptive_db import AdaptiveDB
from .fsrs import FSRSAdapter
from .mastery import update_bkt
from .models import Topic, clamp
from .state import StudentKnowledgeState
from .workload import WorkloadEstimate, initial_workload, update_workload


class AdaptiveSessionLearner:
    """Single backend-owned learning loop for completed study sessions."""

    def __init__(self, db) -> None:
        self.db = db
        self.adaptive_db = AdaptiveDB(db)
        self.fsrs = FSRSAdapter(enable_fuzzing=False)

    def observe(self, topic: Topic, actual_minutes: int, performance_score: float, observed_at: date | datetime | None = None) -> dict:
        when = observed_at or datetime.now(timezone.utc)
        if isinstance(when, date) and not isinstance(when, datetime):
            when = datetime.combine(when, datetime.min.time(), tzinfo=timezone.utc)
        score = clamp(performance_score)

        components = self.adaptive_db.load_knowledge_components(topic.id)
        knowledge: list[StudentKnowledgeState] = []
        for kc in components:
            state = self.adaptive_db.get_knowledge_state(kc.id, kc.initial_mastery)
            state = update_bkt(state, score >= 0.70, when)
            self.adaptive_db.save_knowledge_state(state)
            knowledge.append(state)

        current_row = self.adaptive_db.get_workload(topic.id)
        estimate = WorkloadEstimate(**current_row) if current_row else initial_workload(topic)
        workload = update_workload(estimate, [actual_minutes])
        self.adaptive_db.save_workload(workload)

        rating = 1 if score < 0.60 else 2 if score < 0.75 else 3 if score < 0.90 else 4
        current_card = self.adaptive_db.get_fsrs_state(topic.id) or self.fsrs.new_state(topic.id)
        fsrs_state = self.fsrs.review(current_card, rating, when, max(0, actual_minutes) * 60_000)
        fsrs_state.retrievability = self.fsrs.retrievability(fsrs_state, when)
        self.adaptive_db.save_fsrs_state(fsrs_state)

        if knowledge:
            topic.mastery = sum(s.mastery_probability for s in knowledge) / len(knowledge)
            topic.mastery_uncertainty = sum(s.uncertainty for s in knowledge) / len(knowledge)
        topic.memory_retrievability = fsrs_state.retrievability
        topic.next_review_due = fsrs_state.due.date() if fsrs_state.due else topic.next_review_due
        topic.workload_confidence = workload.confidence
        self.db.update_topic(topic)
        self.adaptive_db.record_event(
            "session_observation",
            {"actual_minutes": actual_minutes, "performance_score": score, "fsrs_rating": rating},
            topic.id,
        )
        return {
            "topic": asdict(topic),
            "workload": asdict(workload),
            "fsrs": asdict(fsrs_state),
            "knowledge": [asdict(s) for s in knowledge],
        }
