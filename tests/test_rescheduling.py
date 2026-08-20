from datetime import date

import pytest

from planner.models import StudySession, SessionType, Subject, Topic, UserProfile
from planner.storage import StudyDB


def test_reschedule_persists_and_preserves_locked_session(tmp_path):
    db = StudyDB(tmp_path / "planner.db")
    db.save_profile(UserProfile())
    db.save_curriculum(
        [Subject("s", "Subject")],
        [Topic("t", "s", "Topic")],
        [],
    )
    ids = db.save_sessions([
        StudySession(date(2026, 8, 20), "t", 45, session_type=SessionType.NEW),
        StudySession(date(2026, 8, 21), "t", 45, session_type=SessionType.NEW),
    ])
    db.reschedule_session(ids[0], date(2026, 8, 24))
    db.delete_uncompleted_sessions_in_range(date(2026, 8, 20), date(2026, 8, 27), {ids[0]})
    rows = db.snapshot()["sessions"]
    assert len(rows) == 1
    assert rows[0]["id"] == ids[0]
    assert rows[0]["session_date"] == "2026-08-24"


def test_completed_session_cannot_be_rescheduled(tmp_path):
    db = StudyDB(tmp_path / "planner.db")
    db.save_curriculum([Subject("s", "Subject")], [Topic("t", "s", "Topic")], [])
    session_id = db.save_sessions([StudySession(date(2026, 8, 20), "t", 45)])[0]
    db.complete_session(session_id, 40, 0.8)
    with pytest.raises(ValueError, match="completed"):
        db.reschedule_session(session_id, date(2026, 8, 21))
