from datetime import date

from planner.adaptation import update_topic_from_session
from planner.models import Exam, Subject, Topic, UserProfile
from planner.storage import StudyDB
from planner.weekly import generate_balanced_week


def curriculum():
    subjects = [Subject("anatomy", "Anatomy"), Subject("physio", "Physiology")]
    topics = [
        Topic("bones", "anatomy", "Bones", mastery=0.1, estimated_hours=2),
        Topic("heart", "physio", "Cardiac Physiology", mastery=0.2, estimated_hours=3),
    ]
    return subjects, topics


def test_weekly_floor_is_explicit_and_rest_day_is_empty():
    subjects, topics = curriculum()
    profile = UserProfile(daily_available_minutes=120, minimum_subject_minutes_week=60, rest_weekdays=(6,))
    plan = generate_balanced_week(subjects, topics, [], profile, date(2026, 8, 17), 7)
    assert plan.unfulfilled_floor == {"anatomy": 0, "physio": 0}
    assert all(s.date.weekday() != 6 for s in plan.sessions)
    assert plan.subject_minutes["anatomy"] >= 60
    assert plan.subject_minutes["physio"] >= 60


def test_completion_updates_mastery_and_review_due():
    _, topics = curriculum()
    updated = update_topic_from_session(topics[0], 45, 0.95, date(2026, 8, 20))
    assert updated.mastery > topics[0].mastery
    assert updated.next_review_due == date(2026, 9, 3)


def test_sqlite_round_trip(tmp_path):
    subjects, topics = curriculum()
    db = StudyDB(tmp_path / "planner.sqlite")
    db.save_curriculum(subjects, topics, [])
    assert db.get_topic("heart").name == "Cardiac Physiology"
    db.update_topic(Topic("heart", "physio", "Cardiac Physiology", mastery=0.7))
    assert db.get_topic("heart").mastery == 0.7
