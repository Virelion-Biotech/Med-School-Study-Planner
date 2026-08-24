from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
import math
import random

from .adaptive_cpsat import optimize_adaptive_week
from .models import ActivityType, Exam, Subject, Topic, UserProfile, clamp
from .scheduler import generate_week


@dataclass(frozen=True)
class SyntheticStudent:
    seed: int
    study_speed: float = 1.0
    adherence: float = 0.82
    learning_rate: float = 0.18
    forgetting_rate: float = 0.035
    question_skill: float = 0.70
    confidence_bias: float = 0.0
    available_minutes: int = 180


@dataclass(frozen=True)
class SimulationMetrics:
    planner: str
    student_seed: int
    planned_minutes: int
    completed_minutes: int
    completion_rate: float
    mean_mastery: float
    mean_retention: float
    topic_coverage: float
    overdue_reviews: int
    deadline_coverage: float
    fairness_gap_minutes: int


@dataclass(frozen=True)
class SimulationRun:
    metrics: SimulationMetrics
    final_topics: tuple[Topic, ...]


def make_student(seed: int) -> SyntheticStudent:
    rng = random.Random(seed)
    return SyntheticStudent(
        seed=seed,
        study_speed=max(0.65, min(1.45, rng.gauss(1.0, 0.15))),
        adherence=max(0.45, min(0.98, rng.gauss(0.82, 0.10))),
        learning_rate=max(0.08, min(0.35, rng.gauss(0.18, 0.035))),
        forgetting_rate=max(0.015, min(0.08, rng.gauss(0.035, 0.008))),
        question_skill=max(0.45, min(0.95, rng.gauss(0.70, 0.08))),
        confidence_bias=max(-0.15, min(0.15, rng.gauss(0.0, 0.05))),
        available_minutes=int(max(90, min(300, rng.gauss(180, 30)))),
    )


def _retention(topic: Topic, elapsed_days: int, student: SyntheticStudent) -> float:
    if elapsed_days <= 0:
        return clamp(topic.memory_retrievability if topic.memory_retrievability is not None else topic.mastery)
    stability = max(3.0, (topic.mastery * 25.0) + (topic.complexity * 8.0))
    return clamp(math.exp(-elapsed_days / (stability / max(student.forgetting_rate / 0.035, 0.25))))


def _apply_session(topic: Topic, activity: ActivityType, minutes: int, completed: bool, elapsed_days: int, student: SyntheticStudent) -> Topic:
    if not completed:
        return topic
    effective = minutes * student.study_speed / 60.0
    mastery = topic.mastery
    if activity is ActivityType.LEARN:
        gain = student.learning_rate * effective * (1.0 - mastery)
    elif activity is ActivityType.QUESTIONS:
        performance = clamp(student.question_skill * 0.65 + mastery * 0.35)
        gain = student.learning_rate * 0.75 * effective * performance * (1.0 - mastery)
    elif activity is ActivityType.RECALL:
        gain = student.learning_rate * 0.60 * effective * (1.0 - mastery)
    elif activity is ActivityType.REVIEW:
        gain = student.learning_rate * 0.45 * effective * (0.5 + mastery)
    else:
        gain = student.learning_rate * 0.65 * effective * (1.0 - 0.6 * mastery)
    new_mastery = clamp(mastery + gain)
    retention = clamp(math.exp(-max(0, elapsed_days) / max(3.0, 8.0 + 20.0 * new_mastery)))
    topic.mastery = new_mastery
    topic.memory_retrievability = retention
    return topic


def _decay_topics(topics: list[Topic], student: SyntheticStudent, days: int) -> None:
    if days <= 0:
        return
    for topic in topics:
        topic.mastery = clamp(topic.mastery * math.exp(-student.forgetting_rate * days))
        topic.memory_retrievability = clamp(math.exp(-student.forgetting_rate * days) * max(topic.mastery, 0.05))


def simulate_planner(
    planner: str,
    subjects: list[Subject],
    topics: list[Topic],
    exams: list[Exam],
    profile: UserProfile,
    student: SyntheticStudent,
    start: date,
    days: int = 28,
) -> SimulationRun:
    rng = random.Random(student.seed + hash(planner) % 10000)
    topic_state = [Topic(**vars(t)) for t in topics]
    topic_last_studied: dict[str, date | None] = {t.id: None for t in topic_state}
    initial_topic_ids = {t.id for t in topic_state}
    planned = completed = 0
    deadline_plan_minutes = 0
    deadline_completed_minutes = 0
    subject_minutes: dict[str, int] = {s.id: 0 for s in subjects}

    for offset in range(days):
        day = start + timedelta(days=offset)
        _decay_topics(topic_state, student, 1 if offset else 0)
        if planner == "legacy_greedy":
            sessions = generate_week(subjects, topic_state, exams, profile, day, 1)
        else:
            sessions = optimize_adaptive_week(subjects, topic_state, exams, profile, day, 1).sessions
        for session in sessions:
            planned += session.planned_minutes
            topic = next((t for t in topic_state if t.id == session.topic_id), None)
            if topic is None:
                continue
            exam = next((e for e in exams if topic.id in e.topic_ids or topic.subject_id in e.subject_ids), None)
            if exam and day <= exam.date:
                deadline_plan_minutes += session.planned_minutes
            adherence = clamp(student.adherence + rng.gauss(0, 0.05))
            actual_complete = rng.random() < adherence
            actual_minutes = int(session.planned_minutes * student.study_speed) if actual_complete else 0
            completed += actual_minutes
            subject_minutes[topic.subject_id] = subject_minutes.get(topic.subject_id, 0) + actual_minutes
            if exam and day <= exam.date:
                deadline_completed_minutes += actual_minutes
            elapsed = (day - topic_last_studied[topic.id]).days if topic_last_studied[topic.id] else 0
            _apply_session(topic, session.activity, max(0, actual_minutes), actual_complete, elapsed, student)
            if actual_complete:
                topic_last_studied[topic.id] = day
                topic.next_review_due = day + timedelta(days=max(1, int(2 + topic.mastery * 12)))

    coverage = len({t.id for t in topic_state if t.mastery >= 0.50} & initial_topic_ids) / max(1, len(initial_topic_ids))
    overdue = sum(1 for t in topic_state if t.next_review_due and t.next_review_due < start + timedelta(days=days))
    mean_mastery = sum(t.mastery for t in topic_state) / max(1, len(topic_state))
    mean_retention = sum((t.memory_retrievability or t.mastery) for t in topic_state) / max(1, len(topic_state))
    fairness_gap = max(0, profile.minimum_subject_minutes_week - min(subject_minutes.values(), default=profile.minimum_subject_minutes_week))
    deadline_coverage = deadline_completed_minutes / max(1, deadline_plan_minutes)
    metrics = SimulationMetrics(
        planner,
        student.seed,
        planned,
        completed,
        completed / max(1, planned),
        mean_mastery,
        mean_retention,
        coverage,
        overdue,
        deadline_coverage,
        fairness_gap,
    )
    return SimulationRun(metrics, tuple(topic_state))


def compare_student_population(
    subjects: list[Subject],
    topics: list[Topic],
    exams: list[Exam],
    profile: UserProfile,
    start: date,
    seeds: range = range(1, 21),
    days: int = 28,
) -> list[SimulationMetrics]:
    results: list[SimulationMetrics] = []
    for seed in seeds:
        student = make_student(seed)
        for planner in ("legacy_greedy", "adaptive_cpsat"):
            results.append(simulate_planner(planner, subjects, topics, exams, profile, student, start, days).metrics)
    return results
