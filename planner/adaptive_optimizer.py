from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
import math

from .models import Exam, SessionType, StudySession, Subject, Topic, UserProfile, best_exam_for_topic
from .utility import UtilityBreakdown, UtilityWeights, action_utility


@dataclass(frozen=True)
class RankedAction:
    topic_id: str
    subject_id: str
    expected_minutes: int
    score: UtilityBreakdown
    session_type: SessionType


def rank_actions(
    subjects: list[Subject],
    topics: list[Topic],
    exams: list[Exam],
    day: date,
    workloads: dict[str, float] | None = None,
    current_block: str | None = None,
    utility_weights: UtilityWeights = UtilityWeights(),
) -> list[RankedAction]:
    """Rank study actions by expected gain per minute without changing the legacy scheduler."""
    workloads = workloads or {}
    subject_map = {subject.id: subject for subject in subjects}
    ranked: list[RankedAction] = []
    for topic in topics:
        subject = subject_map.get(topic.subject_id)
        if subject is None:
            continue
        exam = best_exam_for_topic(topic, exams, day)
        minutes = max(15, int(round(workloads.get(topic.id, topic.estimated_hours * 60))))
        breakdown = action_utility(
            topic,
            subject,
            day,
            exam,
            minutes,
            mastery_probability=topic.mastery,
            retrievability=topic.memory_retrievability,
            current_block=current_block,
            topic_block=topic.block_id,
            weights=utility_weights,
        )
        session_type = SessionType.REVIEW if topic.next_review_due and topic.next_review_due <= day else SessionType.NEW
        ranked.append(RankedAction(topic.id, subject.id, minutes, breakdown, session_type))
    return sorted(ranked, key=lambda item: (-item.score.per_minute, item.topic_id))


def generate_adaptive_week(
    subjects: list[Subject],
    topics: list[Topic],
    exams: list[Exam],
    profile: UserProfile,
    start: date,
    days: int = 7,
    current_block: str | None = None,
    workloads: dict[str, float] | None = None,
    utility_weights: UtilityWeights = UtilityWeights(),
) -> list[StudySession]:
    """Greedy V2 allocation used as a deterministic baseline before full CP-SAT integration.

    It allocates in 15-minute quanta while protecting the existing rest-day/session limits.
    The production CP-SAT integration can consume the same RankedAction objects later.
    """
    sessions: list[StudySession] = []
    quantum = 15
    for offset in range(days):
        day = start + timedelta(days=offset)
        if day.weekday() in profile.rest_weekdays:
            continue
        remaining = profile.daily_available_minutes
        ranked = rank_actions(subjects, topics, exams, day, workloads, current_block, utility_weights)
        for action in ranked:
            if remaining < quantum:
                break
            topic_minutes = max(quantum, min(profile.max_session_minutes, action.expected_minutes))
            minutes = min(topic_minutes, remaining)
            minutes -= minutes % quantum
            if minutes <= 0:
                continue
            sessions.append(
                StudySession(
                    day,
                    action.topic_id,
                    minutes,
                    session_type=action.session_type,
                )
            )
            remaining -= minutes
    return sessions
