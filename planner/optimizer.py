from __future__ import annotations

from datetime import date, timedelta

from .models import Exam, PriorityWeights, SessionType, StudySession, Subject, Topic, UserProfile, best_exam_for_topic, topic_priority
from .weekly import WeeklyPlan, generate_balanced_week

try:
    from ortools.sat.python import cp_model
except ImportError:  # pragma: no cover
    cp_model = None


def optimize_week(
    subjects: list[Subject], topics: list[Topic], exams: list[Exam], profile: UserProfile,
    start: date, days: int = 7, weights: PriorityWeights = PriorityWeights(),
) -> WeeklyPlan:
    """Tier-2 CP-SAT optimizer with a safe Tier-1 fallback when OR-Tools is absent."""
    if cp_model is None:
        return generate_balanced_week(subjects, topics, exams, profile, start, days, weights)

    active = [s for s in subjects if any(t.subject_id == s.id for t in topics)]
    if not active or days < 1:
        return WeeklyPlan([], {}, {})
    quantum = 15
    max_blocks = profile.daily_available_minutes // quantum
    available_days = sum((start + timedelta(i)).weekday() not in profile.rest_weekdays for i in range(days))
    total_capacity = max_blocks * available_days
    model = cp_model.CpModel()
    topic_map = {t.id: t for t in topics}
    subject_map = {s.id: s for s in active}
    vars_: dict[tuple[str, int], cp_model.IntVar] = {}

    for topic in topics:
        if topic.subject_id not in subject_map:
            continue
        for d in range(days):
            day = start + timedelta(days=d)
            if day.weekday() in profile.rest_weekdays:
                continue
            exam = best_exam_for_topic(topic, exams, day)
            if exam and day > exam.date:
                continue
            target_blocks = max(1, round(topic.estimated_hours * 60 / quantum * max(0.25, 1 - topic.mastery)))
            vars_[(topic.id, d)] = model.NewIntVar(0, min(max_blocks, target_blocks), f"q_{topic.id}_{d}")

    for d in range(days):
        model.Add(sum(v for (tid, dd), v in vars_.items() if dd == d) <= max_blocks)

    requested_floor = profile.minimum_subject_minutes_week // quantum
    feasible_floor = min(requested_floor, total_capacity // max(1, len(active)))
    floor_blocks = {s.id: feasible_floor for s in active}
    for subject in active:
        subject_vars = [v for (tid, _), v in vars_.items() if topic_map[tid].subject_id == subject.id]
        if subject_vars and feasible_floor:
            model.Add(sum(subject_vars) >= feasible_floor)

    objective_terms = []
    for (topic_id, d), var in vars_.items():
        topic = topic_map[topic_id]
        day = start + timedelta(days=d)
        score = topic_priority(topic, subject_map[topic.subject_id], day, best_exam_for_topic(topic, exams, day), weights)
        objective_terms.append(int(round(score * 1000)) * var)
    model.Maximize(sum(objective_terms))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 2.0
    solver.parameters.num_search_workers = 4
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return generate_balanced_week(subjects, topics, exams, profile, start, days, weights)

    sessions: list[StudySession] = []
    minutes_by_subject = {s.id: 0 for s in active}
    for (topic_id, d), var in vars_.items():
        blocks = solver.Value(var)
        if blocks <= 0:
            continue
        day = start + timedelta(days=d)
        topic = topic_map[topic_id]
        minutes = blocks * quantum
        sessions.append(StudySession(
            day, topic_id, minutes,
            session_type=SessionType.REVIEW if topic.next_review_due and topic.next_review_due <= day else SessionType.NEW,
        ))
        minutes_by_subject[topic.subject_id] += minutes
    missing = {sid: max(0, floor_blocks[sid] * quantum - minutes_by_subject[sid]) for sid in floor_blocks}
    return WeeklyPlan(sorted(sessions, key=lambda s: (s.date, s.topic_id)), minutes_by_subject, missing)
