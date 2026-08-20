from datetime import date

from planner.adaptation import recalibrated_complexity, update_topic_from_session
from planner.analytics import summarize
from planner.memory import MemoryState, forgetting_curve, next_memory_state
from planner.models import Topic
from planner.storage import StudyDB


def test_memory_progresses_and_resets_after_poor_recall():
    state, interval = next_memory_state(MemoryState(), 0.9)
    assert interval >= 1
    assert state.repetitions == 1
    later, interval2 = next_memory_state(state, 0.95)
    assert later.repetitions == 2
    assert interval2 >= interval
    reset, reset_interval = next_memory_state(later, 0.3)
    assert reset.repetitions == 0
    assert reset_interval == 1


def test_forgetting_curve_bounded():
    assert 0 <= forgetting_curve(7, 0) <= 1
    assert forgetting_curve(7, 7) < forgetting_curve(7, 1)


def test_completion_updates_mastery_and_review():
    topic = Topic("t", "s", "Topic", mastery=0.2)
    updated, state = update_topic_from_session(topic, 45, 0.9, date(2026, 8, 20), MemoryState())
    assert updated.mastery > topic.mastery
    assert updated.next_review_due > date(2026, 8, 20)
    assert state.repetitions == 1


def test_complexity_uses_history():
    topic = Topic("t", "s", "Topic", complexity=0.3, estimated_hours=1)
    adjusted = recalibrated_complexity(topic, [120, 150, 180])
    assert adjusted > 0.3
    assert 0 <= adjusted <= 1


def test_sqlite_round_trip_for_memory_and_management(tmp_path):
    db = StudyDB(tmp_path / "planner.db")
    from planner.models import Subject
    db.upsert_subject(Subject("s", "Subject"))
    db.upsert_topic(Topic("t", "s", "Topic"))
    state = MemoryState(repetitions=3, interval_days=10, ease_factor=2.4, stability_days=12, last_rating=0.9)
    db.save_memory_state("t", state)
    assert db.get_memory_state("t") == state
    db.delete_topic("t")
    assert db.get_topic("t") is None


def test_analytics_handles_empty_and_completed_sessions():
    summary = summarize({"topics": [], "sessions": []})
    assert summary.completion_rate == 0
    assert summary.mean_performance is None
    summary2 = summarize({
        "topics": [{"id": "t", "mastery": 0.8, "next_review_due": "2026-08-19"}],
        "sessions": [{"id": 1, "planned_minutes": 60, "actual_minutes": 75, "completed": 1, "performance_score": 0.9, "topic_id": "t"}],
    }, date(2026, 8, 20))
    assert summary2.completion_rate == 1
    assert summary2.planning_error_minutes == 15
    assert summary2.reviews_due == 1
