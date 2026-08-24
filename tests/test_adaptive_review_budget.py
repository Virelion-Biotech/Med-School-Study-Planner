from datetime import date

from planner.adaptive_cpsat import optimize_adaptive_week
from planner.models import Subject, Topic, UserProfile


def test_review_budget_does_not_force_large_review_share_when_nothing_is_due():
    start = date(2026, 8, 24)
    subjects = [Subject("s", "Subject")]
    topics = [Topic("t1", "s", "T1", estimated_hours=1), Topic("t2", "s", "T2", estimated_hours=1)]
    profile = UserProfile(daily_available_minutes=120, minimum_subject_minutes_week=0, review_fraction=0.50)
    plan = optimize_adaptive_week(subjects, topics, [], profile, start, days=1)
    assert plan.sessions
    assert all(s.session_type.value == "new" for s in plan.sessions)


def test_review_budget_rises_when_due_topics_dominate():
    start = date(2026, 8, 24)
    subjects = [Subject("s", "Subject")]
    topics = [Topic("t1", "s", "T1", estimated_hours=1, mastery=0.8, next_review_due=start)]
    profile = UserProfile(daily_available_minutes=120, minimum_subject_minutes_week=0, review_fraction=0.50)
    plan = optimize_adaptive_week(subjects, topics, [], profile, start, days=1)
    assert plan.sessions
    assert all(s.session_type.value == "review" for s in plan.sessions)
