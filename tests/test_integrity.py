from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from planner.models import Exam, SessionType, StudySession, Subject, Topic, UserProfile
from planner.storage import StudyDB
from planner.weekly import generate_balanced_week


def test_locked_sessions_reduce_daily_capacity():
    start = date(2026, 8, 20)
    profile = UserProfile(daily_available_minutes=120, max_session_minutes=60, minimum_subject_minutes_week=0)
    subjects = [Subject('s', 'Subject')]
    topics = [Topic('t', 's', 'Topic', estimated_hours=4)]
    plan = generate_balanced_week(subjects, topics, [], profile, start, 1, blocked_minutes_by_day={start.isoformat(): 60})
    assert sum(s.planned_minutes for s in plan.sessions) <= 60


def test_persisted_plan_replacement_is_idempotent(tmp_path):
    from planner import api

    api.db = StudyDB(tmp_path / 'planner.db')
    client = TestClient(api.app)
    payload = {
        'subjects': [{'id': 's', 'name': 'Subject'}],
        'topics': [{'id': 't', 'subject_id': 's', 'name': 'Topic', 'estimated_hours': 1}],
        'exams': [],
        'profile': {'daily_available_minutes': 60, 'minimum_subject_minutes_week': 0, 'review_fraction': 0.25, 'max_session_minutes': 60, 'rest_weekdays': []},
        'start_date': '2026-08-20', 'days': 1, 'optimizer': False, 'persist': True,
    }
    first = client.post('/plan', json=payload)
    second = client.post('/plan', json=payload)
    assert first.status_code == 200 and second.status_code == 200
    assert len(api.db.snapshot()['sessions']) == len(second.json()['sessions'])


def test_double_completion_is_rejected(tmp_path):
    db = StudyDB(tmp_path / 'planner.db')
    db.save_curriculum([Subject('s', 'Subject')], [Topic('t', 's', 'Topic')], [])
    session_id = db.save_sessions([StudySession(date(2026, 8, 20), 't', 30, session_type=SessionType.NEW)])[0]
    db.complete_session(session_id, 30, 0.8)
    with pytest.raises(ValueError, match='already completed'):
        db.complete_session(session_id, 20, 0.9)


def test_reschedule_rejects_exam_deadline_and_overloaded_day(tmp_path):
    from planner import api

    api.db = StudyDB(tmp_path / 'planner.db')
    client = TestClient(api.app)
    client.post('/subjects', json={'id': 's', 'name': 'Subject'})
    client.post('/topics', json={'id': 't', 'subject_id': 's', 'name': 'Topic'})
    exam_day = date(2026, 8, 22)
    client.post('/exams', json={'id': 'e', 'date': str(exam_day), 'subject_ids': ['s']})
    api.db.save_profile(UserProfile(daily_available_minutes=60, max_session_minutes=60))
    ids = api.db.save_sessions([
        StudySession(date(2026, 8, 20), 't', 60),
        StudySession(date(2026, 8, 21), 't', 60),
    ])
    after_exam = client.post(f'/sessions/{ids[0]}/reschedule', json={'new_date': str(exam_day + timedelta(days=1))})
    assert after_exam.status_code == 409
    overloaded = client.post(f'/sessions/{ids[0]}/reschedule', json={'new_date': '2026-08-21'})
    assert overloaded.status_code == 409
