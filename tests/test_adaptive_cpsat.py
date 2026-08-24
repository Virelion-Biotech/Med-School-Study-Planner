from datetime import date, timedelta

from planner.adaptive_cpsat import optimize_adaptive_week
from planner.models import Exam, Subject, Topic, UserProfile


def test_adaptive_optimizer_respects_capacity_and_rest_day():
    start = date(2026, 8, 24)
    subjects = [Subject("a", "A"), Subject("b", "B")]
    topics = [Topic("ta", "a", "A topic", estimated_hours=2), Topic("tb", "b", "B topic", estimated_hours=2)]
    profile = UserProfile(daily_available_minutes=90, minimum_subject_minutes_week=30, rest_weekdays=(1,), max_session_minutes=60)
    plan = optimize_adaptive_week(subjects, topics, [], profile, start, days=3)
    assert plan.sessions
    for d in {s.date for s in plan.sessions}:
        assert d.weekday() != 1
        assert sum(s.planned_minutes for s in plan.sessions if s.date == d) <= 90


def test_adaptive_optimizer_accounts_for_preallocated_time_before_exam():
    start = date(2026, 8, 24)
    exam = Exam("e", start + timedelta(days=2), topic_ids=("t",))
    subjects = [Subject("s", "Subject")]
    topics = [Topic("t", "s", "Topic", estimated_hours=1)]
    profile = UserProfile(daily_available_minutes=60, minimum_subject_minutes_week=0)
    plan = optimize_adaptive_week(subjects, topics, [exam], profile, start, days=3, preallocated_topic_minutes={"t": 60})
    assert not any(key.startswith("e:t") for key in plan.unfulfilled_exam_coverage)
