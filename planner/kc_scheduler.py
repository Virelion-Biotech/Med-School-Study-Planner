from __future__ import annotations

from dataclasses import replace

from .adaptive_db import AdaptiveDB
from .kc_context import build_kc_context, topic_kc_ids
from .models import Topic


def project_kc_state_onto_topics(db: AdaptiveDB, topics: list[Topic], now) -> list[Topic]:
    """Project canonical KC state/evidence onto executable Topic objects.

    Topic remains the scheduling/execution unit. When a topic has mapped KCs,
    the scheduler sees the canonical KC mastery/evidence rather than a stale
    topic-local copy.
    """
    projected: list[Topic] = []
    for topic in topics:
        kc_ids = topic_kc_ids(topic)
        if not kc_ids:
            projected.append(topic)
            continue
        contexts = [build_kc_context(db, kc_id, now) for kc_id in kc_ids]
        mastery = sum(c.signal.mastery for c in contexts) / len(contexts)
        uncertainty = sum(c.signal.uncertainty for c in contexts) / len(contexts)
        attempts = sum(c.evidence.attempts for c in contexts)
        accuracy = sum(c.evidence.recent_accuracy for c in contexts) / len(contexts)
        gaps = sum(c.evidence.confidence - c.evidence.recent_accuracy for c in contexts) / len(contexts)
        strength = min(1.0, sum(c.evidence.evidence_strength for c in contexts) / len(contexts))
        projected.append(replace(
            topic,
            mastery=mastery,
            mastery_uncertainty=uncertainty,
            question_attempts=attempts,
            recent_question_accuracy=accuracy,
            question_confidence_gap=max(0.0, gaps),
            question_evidence_strength=strength,
        ))
    return projected
