from datetime import date, timedelta

from planner.models import Exam, PriorityWeights, Subject, Topic, UserProfile, urgency_score
from planner.optimizer import optimize_week


def test_passed_exam_has_no_urgency():
    assert urgency_score(date(2026, 8, 20), date(2026, 8, 19)) == 0
    assert urgency_score(date(2026, 8, 20), date(2026, 8, 20)) == 1


def test_locked_subject_time_counts_toward_fairness():
    start = date(2026, 8, 20)
    subjects = [Subject('a', 'A'), Subject('b', 'B')]
    topics = [Topic('ta', 'a', 'A topic'), Topic('tb', 'b', 'B topic')]
    profile = UserProfile(daily_available_minutes=120, minimum_subject_minutes_week=60)
    plan = optimize_week(subjects, topics, [], profile, start, 1, PriorityWeights(), {start.isoformat(): 60}, {'a': 60}, {'ta': 60})
    assert plan.subject_minutes.get('a', 0) == 0 or plan.unfulfilled_floor.get('a', 0) == 0


def test_exam_coverage_counts_preallocated_topic_time():
    start = date(2026, 8, 20)
    exam = Exam('e', start + timedelta(days=2), topic_ids=('t',), weight=2)
    subjects = [Subject('s', 'S')]
    topics = [Topic('t', 's', 'Topic', estimated_hours=1)]
    profile = UserProfile(daily_available_minutes=60, minimum_subject_minutes_week=0)
    plan = optimize_week(subjects, topics, [exam], profile, start, 3, preallocated_topic_minutes={'t': 60})
    assert all('e:t' not in key for key in plan.unfulfilled_exam_coverage)
