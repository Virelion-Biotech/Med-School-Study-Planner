from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Iterable


class SessionType(str, Enum):
    NEW = "new"
    REVIEW = "review"
    PRACTICE = "practice"


@dataclass(frozen=True)
class Subject:
    id: str
    name: str
    exam_weight: float = 1.0
    category: str = "general"


@dataclass
class Topic:
    id: str
    subject_id: str
    name: str
    complexity: float = 0.5
    estimated_hours: float = 1.0
    mastery: float = 0.0
    last_studied: date | None = None
    next_review_due: date | None = None
    self_difficulty: float = 3.0
    volume: float = 0.5
    cognitive_load: float = 0.5


@dataclass(frozen=True)
class Exam:
    id: str
    date: date
    subject_ids: tuple[str, ...]
    topic_ids: tuple[str, ...] = ()
    weight: float = 1.0


@dataclass
class StudySession:
    date: date
    topic_id: str
    planned_minutes: int
    actual_minutes: int | None = None
    session_type: SessionType = SessionType.NEW
    performance_score: float | None = None


@dataclass(frozen=True)
class UserProfile:
    daily_available_minutes: int = 240
    minimum_subject_minutes_week: int = 60
    review_fraction: float = 0.25
    max_session_minutes: int = 60
    rest_weekdays: tuple[int, ...] = ()
    energy_pattern: tuple[str, ...] = ("high", "medium", "medium", "low")


@dataclass(frozen=True)
class PriorityWeights:
    urgency: float = 0.30
    complexity: float = 0.20
    mastery_gap: float = 0.25
    exam_weight: float = 0.15
    review_due: float = 0.10


def clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def complexity_score(topic: Topic) -> float:
    """Initial complexity estimate; historical learning data can replace inputs later."""
    difficulty = clamp((topic.self_difficulty - 1) / 4)
    return clamp(0.30 * topic.volume + 0.30 * topic.cognitive_load + 0.40 * difficulty)


def urgency_score(today: date, exam_date: date | None) -> float:
    if exam_date is None:
        return 0.0
    days = (exam_date - today).days
    if days <= 0:
        return 1.0
    # Smooth urgency curve: meaningful early, aggressive inside two weeks.
    return clamp(1.0 / (1.0 + days / 14.0))


def review_due_score(today: date, due: date | None) -> float:
    if due is None:
        return 0.0
    days = (today - due).days
    if days >= 0:
        return 1.0
    return clamp(1.0 / (1.0 + abs(days) / 7.0))


def topic_priority(topic: Topic, subject: Subject, today: date, exam: Exam | None,
                   weights: PriorityWeights = PriorityWeights()) -> float:
    exam_date = exam.date if exam else None
    tested = 1.0 if not exam or topic.subject_id in exam.subject_ids or topic.id in exam.topic_ids else 0.15
    return (
        weights.urgency * urgency_score(today, exam_date)
        + weights.complexity * complexity_score(topic)
        + weights.mastery_gap * (1.0 - clamp(topic.mastery))
        + weights.exam_weight * clamp(subject.exam_weight) * tested
        + weights.review_due * review_due_score(today, topic.next_review_due)
    )


def best_exam_for_topic(topic: Topic, exams: Iterable[Exam], today: date) -> Exam | None:
    candidates = [e for e in exams if topic.subject_id in e.subject_ids or topic.id in e.topic_ids]
    future = [e for e in candidates if e.date >= today]
    return min(future, key=lambda e: e.date) if future else None
