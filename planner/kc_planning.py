from __future__ import annotations

from datetime import datetime, timezone

from .adaptive_cpsat import AdaptivePlan, optimize_adaptive_week
from .adaptive_db import AdaptiveDB
from .kc_scheduler import project_kc_state_onto_topics
from .models import Exam, Subject, Topic, UserProfile
from .utility import UtilityWeights


def optimize_with_kc_state(
    adaptive_db: AdaptiveDB,
    subjects: list[Subject],
    topics: list[Topic],
    exams: list[Exam],
    profile: UserProfile,
    start,
    days: int = 7,
    workloads: dict[str, float] | None = None,
    blocked_minutes_by_day: dict[str, int] | None = None,
    preallocated_subject_minutes: dict[str, int] | None = None,
    preallocated_topic_minutes: dict[str, int] | None = None,
    current_block: str | None = None,
    utility_weights: UtilityWeights = UtilityWeights(),
    now: datetime | None = None,
) -> AdaptivePlan:
    """Optimize using canonical KC state while retaining Topic execution units."""
    projected_topics = project_kc_state_onto_topics(
        adaptive_db,
        topics,
        now or datetime.now(timezone.utc),
    )
    return optimize_adaptive_week(
        subjects,
        projected_topics,
        exams,
        profile,
        start,
        days,
        workloads,
        blocked_minutes_by_day,
        preallocated_subject_minutes,
        preallocated_topic_minutes,
        current_block,
        utility_weights,
    )
