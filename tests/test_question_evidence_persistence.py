from datetime import date

from planner.adaptive_cpsat import optimize_adaptive_week
from planner.activity import choose_default_activity
from planner.models import ActivityType, Subject, Topic, UserProfile
from planner.storage import CURRENT_USER, StudyDB


def test_question_evidence_round_trips(tmp_path):
    db = StudyDB(tmp_path / "planner.db")
    token = CURRENT_USER.set("evidence-round-trip")
    try:
        db.upsert_subject(Subject("s", "Subject"))
        topic = Topic(
            "t", "s", "Topic", mastery=0.80,
            question_attempts=25,
            recent_question_accuracy=0.35,
            question_confidence_gap=0.40,
            question_evidence_strength=0.95,
        )
        db.upsert_topic(topic)
        restored = db.get_topic("t")
        assert restored is not None
        assert restored.question_attempts == 25
        assert restored.recent_question_accuracy == 0.35
        assert restored.question_confidence_gap == 0.40
        assert restored.question_evidence_strength == 0.95
    finally:
        CURRENT_USER.reset(token)


def test_weak_question_evidence_changes_planned_activity():
    topic = Topic(
        "t", "s", "Topic", mastery=0.80,
        question_attempts=20,
        recent_question_accuracy=0.30,
        question_confidence_gap=0.50,
        question_evidence_strength=0.80,
    )
    assert choose_default_activity(
        False, topic.mastery, topic.recent_question_accuracy,
        topic.question_confidence_gap, topic.question_evidence_strength,
    ) is ActivityType.QUESTIONS

    plan = optimize_adaptive_week(
        [Subject("s", "Subject")], [topic], [],
        UserProfile(daily_available_minutes=60, minimum_subject_minutes_week=0, max_session_minutes=60),
        date(2026, 8, 24), days=1,
    )
    assert plan.sessions
    assert all(session.activity is ActivityType.QUESTIONS for session in plan.sessions)
