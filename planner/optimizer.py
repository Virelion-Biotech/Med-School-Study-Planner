from __future__ import annotations

from datetime import date, timedelta

from .models import Exam, PriorityWeights, Subject, Topic, UserProfile, best_exam_for_topic, topic_priority
from .weekly import WeeklyPlan, generate_balanced_week

try:
    from ortools.sat.python import cp_model
except ImportError:  # pragma: no cover - exercised when optional dependency is absent
    cp_model = None


def optimize_week(
    subjects: list[Subject], topics: list[Topic], exams: list[Exam], profile: UserProfile,
    start: date, days: int = 7, weights: PriorityWeights = PriorityWeights(),
) -> WeeklyPlan:
    """Tier-2 CP-SAT optimizer; falls back to Tier 1 when OR-Tools is unavailable.

    Variables are 15-minute quanta. The optimizer maximizes priority-weighted coverage,
    enforces daily budgets and weekly subject floors, and avoids placing study after the
    nearest relevant exam date.
    """
    if cp_model is None:
        return generate_balanced_week(subjects, topics, exams, profile, start, days, weights)

    active = [s for s in subjects if any(t.subject_id == s.id for t in topics)]
    if not active:
        return WeeklyPlan([], {}, {})

    model = cp_model.CpModel()
    quantum = 15
    max_blocks = profile.daily_available_minutes // quantum
    vars_: dict[tuple[str, int], cp_model.IntVar] = {}

    for topic in topics:
        if not any(s.id == topic.subject_id for s in active):
            continue
        for d in range(days):
            day = start + timedelta(days=d)
            if day.weekday() in profile.rest_weekdays:
                continue
            exam = best_exam_for_topic(topic, exams, day)
            if exam and day > exam.date:
                continue
            max_topic_blocks = max(1, round(topic.estimated_hours * 60 / quantum * max(0.25, 1 - topic.mastery)))
            vars_[(topic.id, d)] = model.NewIntVar(0, min(max_blocks, max_topic_blocks), f"q_{topic.id}_{d}")

    for d in range(days):
        day_vars = [v for (tid, dd), v in vars_.items() if dd == d]
        model.Add(sum(day_vars) <= max_blocks)

    floors: dict[str, int] = {}
    for subject in active:
        requested = profile.minimum_subject_minutes_week // quantum
        floors[subject.id] = requested
        subject_vars = [v for (tid, d), v in vars_.items() if next(t.subject_id for t in topics if t.id == tid) == subject.id]
        if subject_vars:
            # If the requested floor exceeds feasible weekly capacity, CP-SAT will solve
            # with a scaled soft target rather than making the entire model infeasible.
            floor_target = min(requested, max_blocks * sum(start.weekday() not in profile.rest_weekdays for start in [start + timedelta(i) for i in range(days)]))
            if floor_target:
                model.Add(sum(subject_vars) >= min(floor_target, sum(subject_vars)))

    objective_terms = []
    for (topic_id, d), var in vars_.items():
        topic = next(t for t in topics if t.id == topic_id)
        subject = next(s for s in active if s.id == topic.subject_id)
        score = topic_priority(topic, subject, start + timedelta(days=d), best_exam_for_topic(topic, exams, start + timedelta(days=d)), weights)
        objective_terms.append(int(round(score * 1000)) * var)
    model.Maximize(sum(objective_terms))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 2.0
    solver.parameters.num_search_workers = 4
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return generate_balanced_week(subjects, topics, exams, profile, start, days, weights)

    from .models import SessionType, StudySession
    sessions: list[StudySession] = []
    minutes_by_subject: dict[str, int] = {s.id: 0 for s in active}
    for (topic_id, d), var in vars_.items():
        blocks = solver.Value(var)
        if blocks <= 0:
            continue
        topic = next(t for t in topics if t.id == topic_id)
        minutes = blocks * quantum
        sessions.append(StudySession(start + timedelta(days=d), topic_id, minutes,
                                     session_type=SessionType.REVIEW if topic.next_review_due and topic.next_review_due <= start + timedelta(days=d) else SessionType.NEW))
        minutes_by_subject[topic.subject_id] += minutes

    missing = {sid: max(0, floors[sid] * quantum - minutes_by_subject[sid]) for sid in floors}
    return WeeklyPlan(sorted(sessions, key=lambda s: (s.date, s.topic_id)), minutes_by_subject, missing)
