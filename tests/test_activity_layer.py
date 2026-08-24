from datetime import date

from planner.activity import choose_default_activity
from planner.models import ActivityType, Subject, StudySession, Topic, UserProfile
from planner.adaptive_cpsat import optimize_adaptive_week
from planner.storage import CURRENT_USER, StudyDB


def test_activity_selection_prefers_review_for_due_topics():
    assert choose_default_activity(True, 0.85) is ActivityType.REVIEW
    assert choose_default_activity(False, 0.20) is ActivityType.LEARN
    assert choose_default_activity(False, 0.80, 0.50) is ActivityType.QUESTIONS


def test_adaptive_plan_labels_low_mastery_sessions_as_learning():
    subjects = [Subject("s", "Subject")]
    topics = [Topic("t", "s", "Topic", estimated_hours=1, mastery=0.20)]
    profile = UserProfile(daily_available_minutes=60, minimum_subject_minutes_week=0, max_session_minutes=60)
    plan = optimize_adaptive_week(subjects, topics, [], profile, date(2026, 8, 24), days=1)
    assert plan.sessions
    assert plan.sessions[0].activity is ActivityType.LEARN


def test_session_activity_round_trips(tmp_path):
    db = StudyDB(tmp_path / "planner.db")
    token = CURRENT_USER.set("activity-round-trip")
    try:
        db.upsert_subject(Subject("s", "Subject"))
        ids = db.save_sessions([StudySession(date(2026, 8, 24), "t", 30, activity=ActivityType.REVIEW)])
        assert ids
        row = db.snapshot()["sessions"][0]
        assert row["activity_type"] == "review"
    finally:
        CURRENT_USER.reset(token)
