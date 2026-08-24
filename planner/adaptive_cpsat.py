from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
import math

from .activity import choose_default_activity
from .models import ActivityType, Exam, SessionType, StudySession, Subject, Topic, UserProfile, best_exam_for_topic
from .utility import UtilityWeights, action_utility

try:
    from ortools.sat.python import cp_model
except ImportError:  # pragma: no cover
    cp_model = None


@dataclass(frozen=True)
class AdaptivePlan:
    sessions: list[StudySession]
    subject_minutes: dict[str, int]
    unfulfilled_subject_floor: dict[str, int]
    unfulfilled_exam_coverage: dict[str, int]
    explanations: dict[str, tuple[str, ...]]
    status: str


def _session_activity(topic: Topic, day: date) -> ActivityType:
    is_due = bool(topic.next_review_due and topic.next_review_due <= day)
    return choose_default_activity(is_due, topic.mastery)


def optimize_adaptive_week(
    subjects: list[Subject],
    topics: list[Topic],
    exams: list[Exam],
    profile: UserProfile,
    start: date,
    days: int = 7,
    workloads: dict[str, float] | None = None,
    blocked_minutes_by_day: dict[str, int] | None = None,
    preallocated_subject_minutes: dict[str, int] | None = None,
    preallocated_topic_minutes: dict[str, int] | None = None,
    current_block: str | None = None,
    utility_weights: UtilityWeights = UtilityWeights(),
) -> AdaptivePlan:
    """Allocate 15-minute quanta using expected learning gain/min with hard constraints."""
    workloads = workloads or {}
    blocked_minutes_by_day = blocked_minutes_by_day or {}
    preallocated_subject_minutes = preallocated_subject_minutes or {}
    preallocated_topic_minutes = preallocated_topic_minutes or {}
    active = [s for s in subjects if any(t.subject_id == s.id for t in topics)]
    if not active or days < 1:
        return AdaptivePlan([], {}, {}, {}, {}, "empty")
    if cp_model is None:
        return _greedy_fallback(subjects, topics, exams, profile, start, days, workloads, blocked_minutes_by_day, current_block, utility_weights, preallocated_topic_minutes)

    quantum = 15
    max_blocks = max(0, profile.daily_available_minutes // quantum)
    max_session_blocks = max(1, profile.max_session_minutes // quantum)
    capacities: dict[int, int] = {}
    for d in range(days):
        day = start + timedelta(days=d)
        blocked = max(0, blocked_minutes_by_day.get(day.isoformat(), 0))
        capacities[d] = 0 if day.weekday() in profile.rest_weekdays else max(0, max_blocks - math.ceil(blocked / quantum))

    model = cp_model.CpModel()
    subject_map = {s.id: s for s in active}
    topic_map = {t.id: t for t in topics}
    vars_: dict[tuple[str, int], cp_model.IntVar] = {}
    topic_targets: dict[str, int] = {}
    explanations: dict[str, tuple[str, ...]] = {}
    objective = []

    for topic in topics:
        if topic.subject_id not in subject_map:
            continue
        expected = max(15.0, workloads.get(topic.id, topic.estimated_hours * 60.0))
        target = max(1, math.ceil(expected / quantum))
        pre_blocks = max(0, preallocated_topic_minutes.get(topic.id, 0) // quantum)
        remaining_target = max(0, target - pre_blocks)
        topic_targets[topic.id] = remaining_target
        for d in range(days):
            if capacities[d] <= 0 or remaining_target <= 0:
                continue
            day = start + timedelta(days=d)
            exam = best_exam_for_topic(topic, exams, day)
            if exam is not None and day > exam.date:
                continue
            upper = min(capacities[d], max_session_blocks, remaining_target)
            var = model.NewIntVar(0, upper, f"adaptive_{topic.id}_{d}")
            vars_[(topic.id, d)] = var
            breakdown = action_utility(
                topic,
                subject_map[topic.subject_id],
                day,
                exam,
                expected,
                mastery_probability=topic.mastery,
                retrievability=topic.memory_retrievability,
                current_block=current_block,
                topic_block=topic.block_id,
                weights=utility_weights,
            )
            explanations.setdefault(topic.id, breakdown.reasons)
            objective.append(int(round(breakdown.per_minute * 1_000_000)) * var)

    for d in range(days):
        model.Add(sum(v for (_, dd), v in vars_.items() if dd == d) <= capacities[d])

    for topic_id, remaining_target in topic_targets.items():
        topic_vars = [v for (tid, _), v in vars_.items() if tid == topic_id]
        if topic_vars:
            model.Add(sum(topic_vars) <= remaining_target)

    total_capacity = sum(capacities.values())
    floor_target = max(0, profile.minimum_subject_minutes_week // quantum)
    fair_cap = total_capacity // max(1, len(active))
    floor_target = min(floor_target, fair_cap)
    for subject in active:
        subject_vars = [v for (tid, _), v in vars_.items() if topic_map[tid].subject_id == subject.id]
        pre_blocks = preallocated_subject_minutes.get(subject.id, 0) // quantum
        required = max(0, floor_target - pre_blocks)
        if subject_vars and required:
            model.Add(sum(subject_vars) >= min(required, sum(v.Proto().domain[-1] for v in subject_vars)))

    coverage: dict[str, tuple[date, int, str]] = {}
    horizon_end = start + timedelta(days=days - 1)
    for topic in topics:
        candidates = [e for e in exams if start <= e.date <= horizon_end and (topic.id in e.topic_ids or topic.subject_id in e.subject_ids)]
        if not candidates:
            continue
        exam = min(candidates, key=lambda e: (e.date, -e.weight))
        explicit = topic.id in exam.topic_ids
        base = 4 if explicit else 2
        demand = max(1, round(topic.estimated_hours * (1.0 - topic.mastery) * base))
        coverage[topic.id] = (exam.date, demand, exam.id)
        remaining = max(0, demand - preallocated_topic_minutes.get(topic.id, 0) // quantum)
        relevant = [v for (tid, d), v in vars_.items() if tid == topic.id and start + timedelta(days=d) <= exam.date]
        if relevant and remaining:
            possible = sum(v.Proto().domain[-1] for v in relevant)
            model.Add(sum(relevant) >= min(remaining, possible))

    due_topics = [t for t in topics if t.next_review_due and t.next_review_due <= start]
    review_budget = min(sum(capacities.values()), max(0, math.ceil(total_capacity * profile.review_fraction)))
    review_vars = [v for (tid, _), v in vars_.items() if topic_map[tid] in due_topics]
    if review_vars and review_budget:
        model.Add(sum(review_vars) >= min(review_budget // quantum, sum(v.Proto().domain[-1] for v in review_vars)))

    model.Maximize(sum(objective))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 5.0
    solver.parameters.num_search_workers = 4
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return _greedy_fallback(subjects, topics, exams, profile, start, days, workloads, blocked_minutes_by_day, current_block, utility_weights, preallocated_topic_minutes)

    sessions: list[StudySession] = []
    subject_minutes = {s.id: 0 for s in active}
    covered = {tid: preallocated_topic_minutes.get(tid, 0) // quantum for tid in coverage}
    for (topic_id, d), var in vars_.items():
        blocks = solver.Value(var)
        if blocks <= 0:
            continue
        minutes = blocks * quantum
        topic = topic_map[topic_id]
        day = start + timedelta(days=d)
        session_type = SessionType.REVIEW if topic.next_review_due and topic.next_review_due <= day else SessionType.NEW
        activity = _session_activity(topic, day)
        sessions.append(StudySession(day, topic_id, minutes, session_type=session_type, activity=activity))
        subject_minutes[topic.subject_id] += minutes
        if topic_id in covered:
            covered[topic_id] += blocks

    unfulfilled_floor = {
        s.id: max(0, floor_target * quantum - preallocated_subject_minutes.get(s.id, 0) - subject_minutes[s.id])
        for s in active
    }
    unfulfilled_exam = {
        f"{exam_id}:{topic_id}": max(0, demand - covered.get(topic_id, 0)) * quantum
        for topic_id, (_, demand, exam_id) in coverage.items()
        if max(0, demand - covered.get(topic_id, 0))
    }
    return AdaptivePlan(sorted(sessions, key=lambda s: (s.date, s.topic_id)), subject_minutes, unfulfilled_floor, unfulfilled_exam, explanations, "optimal" if status == cp_model.OPTIMAL else "feasible")


def _greedy_fallback(
    subjects: list[Subject], topics: list[Topic], exams: list[Exam], profile: UserProfile, start: date,
    days: int, workloads: dict[str, float], blocked: dict[str, int], current_block: str | None, weights: UtilityWeights,
    preallocated_topic_minutes: dict[str, int] | None = None,
) -> AdaptivePlan:
    from .adaptive_optimizer import rank_actions

    preallocated_topic_minutes = preallocated_topic_minutes or {}
    quantum = 15
    sessions: list[StudySession] = []
    subject_minutes = {s.id: 0 for s in subjects}
    explanations: dict[str, tuple[str, ...]] = {}
    remaining_by_topic = {
        t.id: max(0, math.ceil(max(15.0, workloads.get(t.id, t.estimated_hours * 60.0)) / quantum) - max(0, preallocated_topic_minutes.get(t.id, 0) // quantum))
        for t in topics
    }
    for offset in range(days):
        day = start + timedelta(days=offset)
        if day.weekday() in profile.rest_weekdays:
            continue
        remaining = max(0, profile.daily_available_minutes - blocked.get(day.isoformat(), 0))
        ranked = rank_actions(subjects, topics, exams, day, workloads, current_block, weights)
        for action in ranked:
            if remaining < quantum or remaining_by_topic.get(action.topic_id, 0) <= 0:
                continue
            available_topic_minutes = remaining_by_topic[action.topic_id] * quantum
            minutes = min(remaining, profile.max_session_minutes, max(quantum, action.expected_minutes), available_topic_minutes)
            minutes -= minutes % quantum
            if minutes <= 0:
                continue
            topic = next((t for t in topics if t.id == action.topic_id), None)
            activity = _session_activity(topic, day) if topic else ActivityType.MIXED
            sessions.append(StudySession(day, action.topic_id, minutes, session_type=action.session_type, activity=activity))
            subject_minutes[action.subject_id] = subject_minutes.get(action.subject_id, 0) + minutes
            explanations[action.topic_id] = action.score.reasons
            remaining_by_topic[action.topic_id] -= minutes // quantum
            remaining -= minutes
    return AdaptivePlan(sessions, subject_minutes, {}, {}, explanations, "greedy")
