from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from .activity import choose_default_activity
from .models import ActivityType, Exam, SessionType, StudySession, Subject, Topic, UserProfile, best_exam_for_topic
from .utility import UtilityBreakdown, UtilityWeights, action_utility


@dataclass(frozen=True)
class RankedAction:
    topic_id: str
    subject_id: str
    expected_minutes: int
    score: UtilityBreakdown
    session_type: SessionType
    activity: ActivityType


def rank_actions(
    subjects: list[Subject],
    topics: list[Topic],
    exams: list[Exam],
    day: date,
    workloads: dict[str, float] | None = None,
    current_block: str | None = None,
    utility_weights: UtilityWeights = UtilityWeights(),
) -> list[RankedAction]:
    """Rank study actions by activity-aware expected gain per minute."""
    workloads = workloads or {}
    subject_map = {subject.id: subject for subject in subjects}
    ranked: list[RankedAction] = []
    for topic in topics:
        subject = subject_map.get(topic.subject_id)
        if subject is None:
            continue
        exam = best_exam_for_topic(topic, exams, day)
        minutes = max(15, int(round(workloads.get(topic.id, topic.estimated_hours * 60))))
        performance = topic.recent_question_accuracy if topic.question_attempts else None
        activity = choose_default_activity(
            bool(topic.next_review_due and topic.next_review_due <= day),
            topic.mastery,
            performance=performance,
            confidence_gap=topic.question_confidence_gap,
            evidence_strength=topic.question_evidence_strength,
        )
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
            activity=activity,
            weights=utility_weights,
        )
        session_type = SessionType.REVIEW if topic.next_review_due and topic.next_review_due <= day else SessionType.NEW
        ranked.append(RankedAction(topic.id, subject.id, minutes, breakdown, session_type, activity))
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
    """Greedy V2 allocation using the same activity-aware utility objective."""
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
                    activity=action.activity,
                )
            )
            remaining -= minutes
    return sessions
