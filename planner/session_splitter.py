from __future__ import annotations

from .activity import ActivityType
from .models import StudySession


def split_session(session: StudySession) -> list[StudySession]:
    """Turn an allocated block into realistic activity chunks without changing total minutes."""
    minutes = session.planned_minutes
    activity = session.activity
    if minutes <= 30:
        return [session]

    if activity is ActivityType.LEARN:
        parts = _fit((45, 15), minutes)
    elif activity is ActivityType.REVIEW:
        parts = _fit((30, 15), minutes)
    elif activity is ActivityType.QUESTIONS:
        parts = _fit((40, 20), minutes)
    elif activity is ActivityType.RECALL:
        parts = _fit((25, 20), minutes)
    else:  # mixed
        parts = _fit((30, 15), minutes)

    activities = {
        ActivityType.LEARN: (ActivityType.LEARN, ActivityType.RECALL),
        ActivityType.REVIEW: (ActivityType.REVIEW, ActivityType.RECALL),
        ActivityType.QUESTIONS: (ActivityType.QUESTIONS, ActivityType.RECALL),
        ActivityType.RECALL: (ActivityType.RECALL,),
        ActivityType.MIXED: (ActivityType.MIXED, ActivityType.RECALL),
    }[activity]
    result: list[StudySession] = []
    for index, part in enumerate(parts):
        child_activity = activities[min(index, len(activities) - 1)]
        result.append(
            StudySession(
                session.date,
                session.topic_id,
                part,
                actual_minutes=None,
                session_type=session.session_type,
                performance_score=None,
                activity=child_activity,
            )
        )
    return result


def split_sessions(sessions: list[StudySession]) -> list[StudySession]:
    return [part for session in sessions for part in split_session(session)]


def _fit(pattern: tuple[int, ...], total: int) -> list[int]:
    if total <= 0:
        return []
    if total <= pattern[0]:
        return [total]
    first = pattern[0]
    remainder = total - first
    if remainder <= 0:
        return [total]
    second = min(pattern[1], remainder)
    leftover = remainder - second
    parts = [first, second]
    if leftover:
        parts.append(leftover)
    return [p for p in parts if p > 0]
