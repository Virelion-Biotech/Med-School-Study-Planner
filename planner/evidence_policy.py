from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .activity import ActivityType, choose_default_activity
from .adaptive_db import AdaptiveDB
from .evidence import evidence_activity_adjustment, summarize_question_evidence
from .models import Topic


@dataclass(frozen=True)
class EvidenceDrivenActivity:
    activity: ActivityType
    evidence_strength: float
    recent_accuracy: float
    confidence_gap: float
    reason: str


def choose_evidence_driven_activity(db: AdaptiveDB, topic: Topic, day: datetime) -> EvidenceDrivenActivity:
    evidence = summarize_question_evidence(db, topic.id, day)
    if evidence.attempts == 0 or evidence.recent_attempts == 0:
        activity = choose_default_activity(bool(topic.next_review_due and topic.next_review_due <= day.date()), topic.mastery)
        return EvidenceDrivenActivity(activity, evidence.evidence_strength, evidence.recent_accuracy, 0.0, "cold-start topic prior")

    multipliers = evidence_activity_adjustment(evidence)
    due = bool(topic.next_review_due and topic.next_review_due <= day.date())
    if due and evidence.recent_accuracy >= 0.80:
        activity = ActivityType.REVIEW
        reason = "review is due and recent question performance is strong"
    elif evidence.recent_accuracy < 0.45:
        activity = ActivityType.QUESTIONS if evidence.attempts >= 3 else ActivityType.LEARN
        reason = "recent question accuracy is weak"
    elif multipliers["confidence_gap"] >= 0.20:
        activity = ActivityType.QUESTIONS
        reason = "self-confidence is materially above observed performance"
    elif evidence.recent_accuracy < 0.70:
        activity = ActivityType.RECALL
        reason = "recent performance is below the consolidation threshold"
    else:
        activity = choose_default_activity(due, topic.mastery)
        reason = "recent performance supports the default activity"
    return EvidenceDrivenActivity(activity, evidence.evidence_strength, evidence.recent_accuracy, multipliers["confidence_gap"], reason)
