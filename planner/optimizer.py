from __future__ import annotations

from datetime import date, timedelta
import math

from .models import Exam, PriorityWeights, SessionType, StudySession, Subject, Topic, UserProfile, best_exam_for_topic, topic_priority
from .weekly import WeeklyPlan, generate_balanced_week

try:
    from ortools.sat.python import cp_model
except ImportError:  # pragma: no cover
    cp_model = None


def _coverage_requirements(topics: list[Topic], exams: list[Exam], start: date, days: int) -> dict[str, tuple[date, int, str]]:
    req: dict[str, tuple[date, int, str]] = {}
    horizon_end = start + timedelta(days=days - 1)
    for topic in topics:
        candidates = [e for e in exams if e.date >= start and e.date <= horizon_end and (topic.id in e.topic_ids or topic.subject_id in e.subject_ids)]
        if not candidates:
            continue
        exam = min(candidates, key=lambda e: (e.date, -e.weight))
        explicit = topic.id in exam.topic_ids
        gap = max(0.1, 1.0 - topic.mastery)
        estimated_blocks = max(1, round(topic.estimated_hours * 60 / 15 * gap * (0.35 if explicit else 0.20)))
        minimum_blocks = min(8 if explicit else 4, estimated_blocks)
        req[topic.id] = (exam.date, minimum_blocks, exam.id)
    return req


def _coverage_gaps(topics: list[Topic], exams: list[Exam], sessions: list[StudySession], start: date, days: int) -> dict[str, int]:
    coverage = _coverage_requirements(topics, exams, start, days)
    if not coverage:
        return {}
    blocks: dict[str, int] = {tid: 0 for tid in coverage}
    for session in sessions:
        if session.topic_id not in blocks or session.date > coverage[session.topic_id][0]:
            continue
        blocks[session.topic_id] += session.planned_minutes // 15
    return {f"{exam_id}:{topic_id}": max(0, required - blocks.get(topic_id, 0)) * 15
            for topic_id, (_, required, exam_id) in coverage.items()
            if max(0, required - blocks.get(topic_id, 0))}


def optimize_week(
    subjects: list[Subject], topics: list[Topic], exams: list[Exam], profile: UserProfile,
    start: date, days: int = 7, weights: PriorityWeights = PriorityWeights(),
    blocked_minutes_by_day: dict[str, int] | None = None,
    preallocated_subject_minutes: dict[str, int] | None = None,
) -> WeeklyPlan:
    """Tier-2 CP-SAT optimizer with daily caps, subject floors, exam coverage and locked capacity."""
    blocked_minutes_by_day = blocked_minutes_by_day or {}
    preallocated_subject_minutes = preallocated_subject_minutes or {}
    if cp_model is None:
        fallback = generate_balanced_week(subjects, topics, exams, profile, start, days, weights, blocked_minutes_by_day, preallocated_subject_minutes)
        return WeeklyPlan(fallback.sessions, fallback.subject_minutes, fallback.unfulfilled_floor, _coverage_gaps(topics, exams, fallback.sessions, start, days))

    active = [s for s in subjects if any(t.subject_id == s.id for t in topics)]
    if not active or days < 1:
        return WeeklyPlan([], {}, {})

    quantum = 15
    max_blocks = profile.daily_available_minutes // quantum
    day_capacity_blocks = {
        d: max(0, max_blocks - math.ceil(max(0, blocked_minutes_by_day.get((start + timedelta(days=d)).isoformat(), 0)) / quantum))
        if (start + timedelta(days=d)).weekday() not in profile.rest_weekdays else 0
        for d in range(days)
    }
    total_capacity = sum(day_capacity_blocks.values())
    model = cp_model.CpModel()
    topic_map = {t.id: t for t in topics}
    subject_map = {s.id: s for s in active}
    vars_: dict[tuple[str, int], cp_model.IntVar] = {}

    for topic in topics:
        if topic.subject_id not in subject_map:
            continue
        for d in range(days):
            day = start + timedelta(days=d)
            capacity = day_capacity_blocks[d]
            if capacity <= 0:
                continue
            exam = best_exam_for_topic(topic, exams, day)
            if exam and day > exam.date:
                continue
            target_blocks = max(1, round(topic.estimated_hours * 60 / quantum * max(0.25, 1 - topic.mastery)))
            vars_[(topic.id, d)] = model.NewIntVar(0, min(capacity, target_blocks), f"q_{topic.id}_{d}")

    for d in range(days):
        model.Add(sum(v for (tid, dd), v in vars_.items() if dd == d) <= day_capacity_blocks[d])

    requested_floor = profile.minimum_subject_minutes_week // quantum
    floor_blocks = {s.id: max(0, math.ceil((profile.minimum_subject_minutes_week - preallocated_subject_minutes.get(s.id, 0)) / quantum)) for s in active}
    feasible_floor_total = total_capacity // max(1, len(active))
    for subject in active:
        floor = min(floor_blocks[subject.id], feasible_floor_total)
        floor_blocks[subject.id] = floor
        subject_vars = [v for (tid, _), v in vars_.items() if topic_map[tid].subject_id == subject.id]
        if subject_vars and floor:
            model.Add(sum(subject_vars) >= floor)

    coverage = _coverage_requirements(topics, exams, start, days)
    for topic_id, (deadline, required, _) in coverage.items():
        relevant = [v for (tid, d), v in vars_.items() if tid == topic_id and start + timedelta(days=d) <= deadline]
        if relevant:
            max_possible = sum(v.Proto().domain[1] for v in relevant)
            model.Add(sum(relevant) >= min(required, max_possible))

    objective_terms = []
    for (topic_id, d), var in vars_.items():
        topic = topic_map[topic_id]
        day = start + timedelta(days=d)
        score = topic_priority(topic, subject_map[topic.subject_id], day, best_exam_for_topic(topic, exams, day), weights)
        if topic_id in coverage:
            score += 0.35
        objective_terms.append(int(round(score * 1000)) * var)
    model.Maximize(sum(objective_terms))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 3.0
    solver.parameters.num_search_workers = 4
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        fallback = generate_balanced_week(subjects, topics, exams, profile, start, days, weights, blocked_minutes_by_day, preallocated_subject_minutes)
        return WeeklyPlan(fallback.sessions, fallback.subject_minutes, fallback.unfulfilled_floor, _coverage_gaps(topics, exams, fallback.sessions, start, days))

    sessions: list[StudySession] = []
    minutes_by_subject = {s.id: 0 for s in active}
    covered_blocks = {topic_id: 0 for topic_id in coverage}
    for (topic_id, d), var in vars_.items():
        blocks = solver.Value(var)
        if blocks <= 0:
            continue
        day = start + timedelta(days=d)
        topic = topic_map[topic_id]
        minutes = blocks * quantum
        sessions.append(StudySession(day, topic_id, minutes, session_type=SessionType.REVIEW if topic.next_review_due and topic.next_review_due <= day else SessionType.NEW))
        minutes_by_subject[topic.subject_id] += minutes
        if topic_id in covered_blocks:
            covered_blocks[topic_id] += blocks

    missing = {sid: max(0, floor_blocks[sid] * quantum - minutes_by_subject[sid]) for sid in floor_blocks}
    exam_gaps = {f"{exam_id}:{topic_id}": max(0, required - covered_blocks.get(topic_id, 0)) * quantum
                 for topic_id, (_, required, exam_id) in coverage.items()
                 if max(0, required - covered_blocks.get(topic_id, 0))}
    return WeeklyPlan(sorted(sessions, key=lambda s: (s.date, s.topic_id)), minutes_by_subject, missing, exam_gaps)
