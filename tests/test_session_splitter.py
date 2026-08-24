from datetime import date

from planner.models import ActivityType, SessionType, StudySession
from planner.session_splitter import split_session, split_sessions


def test_splitter_preserves_minutes():
    source = StudySession(date(2026, 8, 24), "topic", 90, session_type=SessionType.NEW, activity=ActivityType.LEARN)
    parts = split_session(source)
    assert sum(p.planned_minutes for p in parts) == source.planned_minutes
    assert all(p.topic_id == source.topic_id for p in parts)
    assert all(p.date == source.date for p in parts)


def test_splitter_turns_learning_into_learning_plus_recall():
    source = StudySession(date(2026, 8, 24), "topic", 60, session_type=SessionType.NEW, activity=ActivityType.LEARN)
    parts = split_session(source)
    assert [p.activity for p in parts] == [ActivityType.LEARN, ActivityType.RECALL]
    assert [p.planned_minutes for p in parts] == [45, 15]


def test_split_sessions_preserves_total_week_minutes():
    source = [
        StudySession(date(2026, 8, 24), "a", 45, activity=ActivityType.REVIEW),
        StudySession(date(2026, 8, 25), "b", 60, activity=ActivityType.QUESTIONS),
    ]
    result = split_sessions(source)
    assert sum(x.planned_minutes for x in result) == sum(x.planned_minutes for x in source)
