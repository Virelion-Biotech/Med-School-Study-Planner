from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import math

from .activity import ActivityType, activity_profile
from .models import Exam, Subject, Topic, clamp


@dataclass(frozen=True)
class UtilityWeights:
    exam_urgency: float = 1.0
    mastery_gap: float = 1.0
    retention_gap: float = 0.9
    blueprint: float = 0.7
    workload: float = 0.5
    block_relevance: float = 0.35
    activity_fit: float = 0.55
    evidence_fit: float = 0.30


@dataclass(frozen=True)
class EvidenceSignal:
    recent_accuracy: float = 0.5
    confidence_gap: float = 0.0
    evidence_strength: float = 0.0


@dataclass(frozen=True)
class UtilityBreakdown:
    total: float
    per_minute: float
    exam_urgency: float
    mastery_gap: float
    retention_gap: float
    blueprint: float
    workload: float
    block_relevance: float
    activity_fit: float
    evidence_fit: float
    activity: ActivityType
    reasons: tuple[str, ...]


def smooth_exam_urgency(today: date, exam_date: date | None, midpoint_days: float = 10.0, steepness: float = 0.30) -> float:
    if exam_date is None:
        return 0.0
    days = (exam_date - today).days
    if days < 0:
        return 0.0
    return 1.0 / (1.0 + math.exp(steepness * (days - midpoint_days)))


def expected_retrievability(stability_days: float | None, elapsed_days: float | None) -> float:
    if not stability_days or stability_days <= 0:
        return 0.0
    return math.exp(-max(0.0, elapsed_days or 0.0) / stability_days)


def _activity_fit(activity: ActivityType, mastery_gap: float, retention_gap: float, blueprint: float) -> float:
    profile = activity_profile(activity)
    practice_need = clamp(1.0 - abs(0.55 - (1.0 - mastery_gap)) / 0.55)
    raw = (
        profile.learning_gain * mastery_gap
        + profile.retention_gain * retention_gap
        + profile.practice_gain * practice_need * (0.5 + 0.5 * blueprint)
    ) / 3.0
    return clamp(raw)


def _evidence_fit(activity: ActivityType, evidence: EvidenceSignal) -> float:
    accuracy_gap = clamp(1.0 - evidence.recent_accuracy)
    confidence_gap = clamp(max(0.0, evidence.confidence_gap))
    if activity is ActivityType.QUESTIONS:
        target = 0.70 * accuracy_gap + 0.30 * confidence_gap
    elif activity is ActivityType.LEARN:
        target = 0.70 * accuracy_gap
    elif activity is ActivityType.RECALL:
        target = 0.45 * accuracy_gap
    elif activity is ActivityType.REVIEW:
        target = 0.35 * (1.0 - accuracy_gap)
    else:
        target = 0.30
    return clamp(target * (0.25 + 0.75 * evidence.evidence_strength))


def action_utility(
    topic: Topic,
    subject: Subject,
    today: date,
    exam: Exam | None,
    expected_minutes: float,
    mastery_probability: float | None = None,
    retrievability: float | None = None,
    current_block: str | None = None,
    topic_block: str | None = None,
    activity: ActivityType = ActivityType.MIXED,
    evidence: EvidenceSignal | None = None,
    weights: UtilityWeights = UtilityWeights(),
) -> UtilityBreakdown:
    evidence = evidence or EvidenceSignal()
    mastery = clamp(topic.mastery if mastery_probability is None else mastery_probability)
    retention = clamp(1.0 if retrievability is None else retrievability)
    urgency = smooth_exam_urgency(today, exam.date if exam else None)
    blueprint = clamp(subject.exam_weight if subject.exam_weight <= 1 else subject.exam_weight / 16.0)
    workload = clamp(expected_minutes / 240.0)
    block = 1.0 if current_block and topic_block and topic_block == current_block else 0.0
    mastery_gap = 1.0 - mastery
    retention_gap = 1.0 - retention
    activity_fit = _activity_fit(activity, mastery_gap, retention_gap, blueprint)
    evidence_fit = _evidence_fit(activity, evidence)
    total = (
        weights.exam_urgency * urgency
        + weights.mastery_gap * mastery_gap
        + weights.retention_gap * retention_gap
        + weights.blueprint * blueprint
        + weights.workload * workload
        + weights.block_relevance * block
        + weights.activity_fit * activity_fit
        + weights.evidence_fit * evidence_fit
    )
    per_minute = total / max(expected_minutes, 1.0)
    reasons: list[str] = []
    if urgency >= 0.60:
        reasons.append("exam is approaching")
    if mastery <= 0.50:
        reasons.append(f"estimated mastery is {round(mastery * 100)}%")
    if retention <= 0.60:
        reasons.append(f"predicted retention is {round(retention * 100)}%")
    if evidence.evidence_strength > 0:
        reasons.append(f"recent question accuracy is {round(evidence.recent_accuracy * 100)}%")
        if evidence.confidence_gap >= 0.20:
            reasons.append("confidence is higher than observed performance")
    if blueprint >= 0.60:
        reasons.append("high exam blueprint weight")
    if block:
        reasons.append("matches the current block")
    reasons.append(f"activity fit: {activity.value}")
    return UtilityBreakdown(total, per_minute, urgency, mastery_gap, retention_gap, blueprint, workload, block, activity_fit, evidence_fit, activity, tuple(reasons))
