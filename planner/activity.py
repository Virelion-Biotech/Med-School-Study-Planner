from __future__ import annotations

from dataclasses import dataclass

from .models import ActivityType


@dataclass(frozen=True)
class ActivityProfile:
    activity: ActivityType
    learning_gain: float
    retention_gain: float
    practice_gain: float


ACTIVITY_PROFILES: dict[ActivityType, ActivityProfile] = {
    ActivityType.LEARN: ActivityProfile(ActivityType.LEARN, 1.00, 0.20, 0.05),
    ActivityType.REVIEW: ActivityProfile(ActivityType.REVIEW, 0.35, 1.00, 0.10),
    ActivityType.QUESTIONS: ActivityProfile(ActivityType.QUESTIONS, 0.55, 0.65, 1.00),
    ActivityType.RECALL: ActivityProfile(ActivityType.RECALL, 0.65, 0.90, 0.75),
    ActivityType.MIXED: ActivityProfile(ActivityType.MIXED, 0.75, 0.75, 0.75),
}


def activity_profile(activity: ActivityType) -> ActivityProfile:
    return ACTIVITY_PROFILES[activity]


def choose_default_activity(is_due: bool, mastery: float, performance: float | None = None) -> ActivityType:
    if is_due:
        return ActivityType.REVIEW
    if mastery < 0.40:
        return ActivityType.LEARN
    if performance is not None and performance < 0.65:
        return ActivityType.QUESTIONS
    return ActivityType.MIXED
