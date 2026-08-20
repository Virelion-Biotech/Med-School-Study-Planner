from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta

from .models import Exam, PriorityWeights, SessionType, StudySession, Subject, Topic, UserProfile, best_exam_for_topic, topic_priority
from .scheduler import _active_subjects


@dataclass(frozen=True)
class WeeklyPlan:
    sessions: list[StudySession]
    subject_minutes: dict[str, int]
    unfulfilled_floor: dict[str, int]
    unfulfilled_exam_coverage: dict[str, int] = field(default_factory=dict)


def _review_fraction(profile: UserProfile, day: date, exams: list[Exam]) -> float:
    future = [e.date for e in exams if e.date >= day]
    if not future:
        return profile.review_fraction
    days = (min(future) - day).days
    boost = 0.0 if days > 28 else 0.10 if days > 14 else 0.20 if days > 7 else 0.30
    return min(0.80, profile.review_fraction + boost)


def generate_balanced_week(
    subjects: list[Subject], topics: list[Topic], exams: list[Exam], profile: UserProfile,
    start: date, days: int = 7, weights: PriorityWeights = PriorityWeights(),
) -> WeeklyPlan:
    if days < 1:
        return WeeklyPlan([], {}, {})
    active = _active_subjects(subjects, topics, exams, start)
    if not active:
        return WeeklyPlan([], {}, {})

    available_days = sum((start + timedelta(i)).weekday() not in profile.rest_weekdays for i in range(days))
    capacity = available_days * profile.daily_available_minutes
    requested_floor = profile.minimum_subject_minutes_week
    total_floor = requested_floor * len(active)
    floor_scale = min(1.0, capacity / total_floor) if total_floor else 1.0
    floor_target = {s.id: round(requested_floor * floor_scale) for s in active}
    floor_debt = dict(floor_target)
    subject_minutes = defaultdict(int)
    sessions: list[StudySession] = []
    by_subject: dict[str, list[Topic]] = defaultdict(list)
    subject_map = {s.id: s for s in active}
    for topic in topics:
        if topic.subject_id in subject_map:
            by_subject[topic.subject_id].append(topic)

    for offset in range(days):
        day = start + timedelta(days=offset)
        if day.weekday() in profile.rest_weekdays:
            continue
        remaining_days = sum((start + timedelta(j)).weekday() not in profile.rest_weekdays for j in range(offset, days))
        available = profile.daily_available_minutes
        scores = {t.id: topic_priority(t, subject_map[t.subject_id], day, best_exam_for_topic(t, exams, day), weights)
                  for t in topics if t.subject_id in subject_map}

        for subject in sorted(active, key=lambda s: floor_debt[s.id], reverse=True):
            if available <= 0 or floor_debt[subject.id] <= 0 or not by_subject[subject.id]:
                continue
            topic = max(by_subject[subject.id], key=lambda t: scores[t.id])
            debt_cap = max(15, (floor_debt[subject.id] + remaining_days - 1) // remaining_days)
            mins = min(profile.max_session_minutes, debt_cap, available)
            if mins <= 0:
                continue
            session_type = SessionType.REVIEW if topic.next_review_due and topic.next_review_due <= day else SessionType.NEW
            sessions.append(StudySession(day, topic.id, mins, session_type=session_type))
            floor_debt[subject.id] -= mins
            subject_minutes[subject.id] += mins
            available -= mins

        review_budget = min(available, round(profile.daily_available_minutes * _review_fraction(profile, day, exams)))
        due = sorted([t for t in topics if t.subject_id in subject_map and t.next_review_due and t.next_review_due <= day],
                     key=lambda t: scores[t.id], reverse=True)
        for topic in due:
            if review_budget <= 0 or available <= 0:
                break
            mins = min(profile.max_session_minutes, review_budget, available)
            sessions.append(StudySession(day, topic.id, mins, session_type=SessionType.REVIEW))
            subject_minutes[topic.subject_id] += mins
            review_budget -= mins
            available -= mins

        ranked = sorted((t for t in topics if t.subject_id in subject_map), key=lambda t: scores[t.id], reverse=True)
        while available > 0 and ranked:
            total = sum(max(scores[t.id], 0.01) for t in ranked)
            progressed = False
            for topic in ranked:
                if available <= 0:
                    break
                share = max(15, round(available * scores[topic.id] / total))
                mins = min(profile.max_session_minutes, share, available)
                if mins <= 0:
                    continue
                sessions.append(StudySession(day, topic.id, mins, session_type=SessionType.NEW))
                subject_minutes[topic.subject_id] += mins
                available -= mins
                progressed = True
            if not progressed:
                break

    return WeeklyPlan(sessions, dict(subject_minutes), {k: max(0, v) for k, v in floor_debt.items()})
