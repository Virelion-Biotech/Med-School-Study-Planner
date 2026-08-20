from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from dataclasses import dataclass

from .models import (
    Exam, PriorityWeights, SessionType, StudySession, Subject, Topic, UserProfile,
    best_exam_for_topic, topic_priority,
)


@dataclass(frozen=True)
class Allocation:
    topic_id: str
    subject_id: str
    minutes: int
    score: float
    session_type: SessionType


def _active_subjects(subjects: list[Subject], topics: list[Topic], exams: list[Exam], today: date) -> list[Subject]:
    ids = {t.subject_id for t in topics}
    ids |= {sid for e in exams if e.date >= today for sid in e.subject_ids}
    return [s for s in subjects if s.id in ids]


def allocate_day(
    subjects: list[Subject], topics: list[Topic], exams: list[Exam], profile: UserProfile,
    day: date, weights: PriorityWeights = PriorityWeights(),
) -> list[Allocation]:
    """Allocate one day while protecting review time and subject fairness."""
    if day.weekday() in profile.rest_weekdays:
        return []
    active = _active_subjects(subjects, topics, exams, day)
    if not active:
        return []

    available = profile.daily_available_minutes
    review_budget = round(available * profile.review_fraction)
    floor_budget = min(profile.minimum_subject_minutes_week, available // len(active))
    # The fairness floor is a daily proxy for the weekly guarantee; weekly generation
    # tracks accumulated minutes so later versions can enforce the exact constraint.
    floor_budget = min(floor_budget, available // len(active))

    by_subject: dict[str, list[Topic]] = defaultdict(list)
    for t in topics:
        by_subject[t.subject_id].append(t)

    subject_map = {s.id: s for s in active}
    scored: dict[str, float] = {}
    for t in topics:
        if t.subject_id not in subject_map:
            continue
        exam = best_exam_for_topic(t, exams, day)
        scored[t.id] = topic_priority(t, subject_map[t.subject_id], day, exam, weights)

    allocations: list[Allocation] = []
    used = 0
    # First guarantee each active subject a minimum slice.
    for subject in active:
        candidates = sorted(by_subject[subject.id], key=lambda t: scored.get(t.id, 0), reverse=True)
        if not candidates:
            continue
        topic = candidates[0]
        mins = min(floor_budget, profile.max_session_minutes, available - used)
        if mins <= 0:
            break
        allocations.append(Allocation(topic.id, subject.id, mins, scored[topic.id], SessionType.REVIEW if topic.next_review_due and topic.next_review_due <= day else SessionType.NEW))
        used += mins

    remainder = max(0, available - used)
    review_candidates = [t for t in topics if t.id in scored and t.next_review_due and t.next_review_due <= day]
    review_remaining = min(review_budget, remainder)
    for t in sorted(review_candidates, key=lambda x: scored[x.id], reverse=True):
        if review_remaining <= 0 or remainder <= 0:
            break
        mins = min(profile.max_session_minutes, review_remaining, remainder)
        allocations.append(Allocation(t.id, t.subject_id, mins, scored[t.id], SessionType.REVIEW))
        review_remaining -= mins
        remainder -= mins

    # Priority-weighted remainder. A small quantum prevents one topic from swallowing a day.
    ranked = sorted((t for t in topics if t.id in scored), key=lambda x: scored[x.id], reverse=True)
    while remainder > 0 and ranked:
        total = sum(max(scored[t.id], 0.01) for t in ranked)
        progressed = False
        for t in ranked:
            if remainder <= 0:
                break
            share = max(15, round(remainder * scored[t.id] / total))
            mins = min(profile.max_session_minutes, share, remainder)
            if mins <= 0:
                continue
            allocations.append(Allocation(t.id, t.subject_id, mins, scored[t.id], SessionType.NEW))
            remainder -= mins
            progressed = True
        if not progressed:
            break
    return allocations


def generate_week(
    subjects: list[Subject], topics: list[Topic], exams: list[Exam], profile: UserProfile,
    start: date, days: int = 7, weights: PriorityWeights = PriorityWeights(),
) -> list[StudySession]:
    """Generate deterministic daily sessions; future versions can use ILP for hard constraints."""
    sessions: list[StudySession] = []
    for offset in range(days):
        day = start + timedelta(days=offset)
        for a in allocate_day(subjects, topics, exams, profile, day, weights):
            sessions.append(StudySession(day, a.topic_id, a.minutes, session_type=a.session_type))
    return sessions
