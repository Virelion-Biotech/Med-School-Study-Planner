from __future__ import annotations

from datetime import date

from planner.models import ActivityType, SessionType, StudySession
from planner.plan_versioning import plan_fingerprint


def _session(topic: str, minutes: int) -> StudySession:
    return StudySession(
        date=date(2026, 8, 25),
        topic_id=topic,
        planned_minutes=minutes,
        session_type=SessionType.STUDY,
        activity=ActivityType.LEARN,
    )


def test_plan_fingerprint_is_order_independent():
    a = [_session("b", 30), _session("a", 45)]
    b = list(reversed(a))
    assert plan_fingerprint(a) == plan_fingerprint(b)


def test_plan_fingerprint_changes_when_plan_changes():
    assert plan_fingerprint([_session("a", 45)]) != plan_fingerprint([_session("a", 60)])
