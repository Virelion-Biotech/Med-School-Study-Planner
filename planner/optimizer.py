from __future__ import annotations

import os
from datetime import date

from .adaptive_cpsat import optimize_adaptive_week
from .models import Exam, PriorityWeights, Subject, Topic, UserProfile
from .utility import UtilityWeights
from .weekly import WeeklyPlan, generate_balanced_week


def _utility_weights(weights: PriorityWeights) -> UtilityWeights:
    """Translate legacy weights into the V2 utility engine without changing the API."""
    return UtilityWeights(
        exam_urgency=max(0.1, weights.urgency / 0.30),
        mastery_gap=max(0.1, weights.mastery_gap / 0.25),
        retention_gap=max(0.1, weights.review_due / 0.10),
        blueprint=max(0.1, weights.exam_weight / 0.15),
        workload=max(0.1, weights.complexity / 0.20),
        block_relevance=0.35,
    )


def optimize_week(
    subjects: list[Subject],
    topics: list[Topic],
    exams: list[Exam],
    profile: UserProfile,
    start: date,
    days: int = 7,
    weights: PriorityWeights = PriorityWeights(),
    blocked_minutes_by_day: dict[str, int] | None = None,
    preallocated_subject_minutes: dict[str, int] | None = None,
    preallocated_topic_minutes: dict[str, int] | None = None,
) -> WeeklyPlan:
    """Stable planner contract with a safe deterministic default.

    Native CP-SAT is opt-in because a native solver crash must never take down
    the student-facing setup/replan API. Enable it only after runtime validation
    with PLANNER_ENABLE_CPSAT=1.
    """
    use_cpsat = os.getenv("PLANNER_ENABLE_CPSAT", "0").strip().lower() in {"1", "true", "yes", "on"}
    if not use_cpsat:
        return generate_balanced_week(
            subjects,
            topics,
            exams,
            profile,
            start,
            days,
            weights,
            blocked_minutes_by_day=blocked_minutes_by_day,
            preallocated_subject_minutes=preallocated_subject_minutes,
        )

    plan = optimize_adaptive_week(
        subjects,
        topics,
        exams,
        profile,
        start,
        days,
        workloads={t.id: max(15.0, t.estimated_hours * 60.0) for t in topics},
        blocked_minutes_by_day=blocked_minutes_by_day,
        preallocated_subject_minutes=preallocated_subject_minutes,
        preallocated_topic_minutes=preallocated_topic_minutes,
        utility_weights=_utility_weights(weights),
    )
    return WeeklyPlan(
        sessions=plan.sessions,
        subject_minutes=plan.subject_minutes,
        unfulfilled_floor=plan.unfulfilled_subject_floor,
        unfulfilled_exam_coverage=plan.unfulfilled_exam_coverage,
    )
