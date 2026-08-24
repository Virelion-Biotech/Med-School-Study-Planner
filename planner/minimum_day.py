from __future__ import annotations

from dataclasses import replace
from datetime import date

from .adaptive_cpsat import AdaptivePlan, optimize_adaptive_week
from .models import Exam, Subject, Topic, UserProfile
from .utility import UtilityWeights


def optimize_minimum_day(
    subjects: list[Subject],
    topics: list[Topic],
    exams: list[Exam],
    profile: UserProfile,
    day: date,
    minutes: int = 45,
    utility_weights: UtilityWeights = UtilityWeights(),
) -> AdaptivePlan:
    """Generate a conservative one-day plan without mutating the student's profile."""
    capacity = max(15, min(int(minutes), profile.daily_available_minutes))
    temporary = replace(profile, daily_available_minutes=capacity, max_session_minutes=min(profile.max_session_minutes, capacity))
    return optimize_adaptive_week(
        subjects,
        topics,
        exams,
        temporary,
        day,
        days=1,
        workloads=None,
        utility_weights=utility_weights,
    )
