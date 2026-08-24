from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import random

from .adaptive_cpsat import optimize_adaptive_week
from .models import Exam, Subject, Topic, UserProfile
from .scheduler import generate_week


@dataclass(frozen=True)
class SimulationResult:
    name: str
    planned_minutes: int
    topic_coverage: float
    weighted_utility: float
    fairness_gap_minutes: int


def _coverage(sessions, topic_ids: set[str]) -> float:
    if not topic_ids:
        return 1.0
    covered = {s.topic_id for s in sessions if s.planned_minutes > 0}
    return len(covered & topic_ids) / len(topic_ids)


def _fairness_gap(sessions, subjects: list[Subject], topics: list[Topic], floor: int) -> int:
    topic_to_subject = {t.id: t.subject_id for t in topics}
    minutes = {s.id: 0 for s in subjects}
    for session in sessions:
        subject_id = topic_to_subject.get(session.topic_id)
        if subject_id in minutes:
            minutes[subject_id] += session.planned_minutes
    return max(0, floor - min(minutes.values(), default=floor))


def compare_planners(
    subjects: list[Subject],
    topics: list[Topic],
    exams: list[Exam],
    profile: UserProfile,
    start: date,
    days: int = 7,
) -> list[SimulationResult]:
    """Compare the legacy greedy baseline against the V2 constrained planner."""
    legacy = generate_week(subjects, topics, exams, profile, start, days)
    adaptive = optimize_adaptive_week(subjects, topics, exams, profile, start, days)
    topic_ids = {t.id for t in topics}
    return [
        SimulationResult(
            "legacy_greedy",
            sum(s.planned_minutes for s in legacy),
            _coverage(legacy, topic_ids),
            0.0,
            _fairness_gap(legacy, subjects, topics, profile.minimum_subject_minutes_week),
        ),
        SimulationResult(
            "adaptive_cpsat",
            sum(s.planned_minutes for s in adaptive.sessions),
            _coverage(adaptive.sessions, topic_ids),
            sum(1.0 for s in adaptive.sessions if s.session_type.value in {"review", "new"}),
            max(adaptive.unfulfilled_subject_floor.values(), default=0),
        ),
    ]


def synthetic_student(seed: int = 7) -> tuple[list[Subject], list[Topic], list[Exam], UserProfile]:
    """Deterministic fixture for regression benchmarking, not a clinical or educational claim."""
    rng = random.Random(seed)
    subjects = [Subject("cardio", "Cardiovascular", 1.0), Subject("renal", "Renal", 0.9), Subject("neuro", "Neurology", 0.8)]
    topics: list[Topic] = []
    for subject in subjects:
        for index in range(8):
            topics.append(
                Topic(
                    f"{subject.id}-{index}",
                    subject.id,
                    f"{subject.name} topic {index + 1}",
                    estimated_hours=rng.uniform(0.5, 2.5),
                    mastery=rng.uniform(0.15, 0.8),
                    self_difficulty=rng.uniform(2, 5),
                    volume=rng.random(),
                    cognitive_load=rng.random(),
                )
            )
    exams = [Exam("block", date(2026, 9, 7), tuple(s.id for s in subjects), weight=1.0)]
    profile = UserProfile(daily_available_minutes=180, minimum_subject_minutes_week=60, review_fraction=0.25, max_session_minutes=60)
    return subjects, topics, exams, profile
