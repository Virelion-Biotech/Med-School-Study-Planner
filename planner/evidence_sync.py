from __future__ import annotations

from datetime import datetime

from .adaptive_db import AdaptiveDB
from .evidence import summarize_question_evidence
from .models import Topic, clamp


def sync_topic_question_evidence(db: AdaptiveDB, topic: Topic, now: datetime) -> Topic:
    evidence = summarize_question_evidence(db, topic.id, now)
    topic.question_attempts = evidence.attempts
    topic.recent_question_accuracy = evidence.recent_accuracy
    topic.question_confidence_gap = clamp(evidence.confidence - evidence.recent_accuracy)
    topic.question_evidence_strength = evidence.evidence_strength
    db.db.update_topic(topic)
    return topic
