from datetime import date

from planner.activity import ActivityType
from planner.models import Subject, Topic
from planner.utility import action_utility


def test_activity_fit_changes_utility_objective():
    topic = Topic("t", "s", "Topic", mastery=0.25, memory_retrievability=0.95)
    subject = Subject("s", "Subject", exam_weight=0.8)
    learn = action_utility(topic, subject, date(2026, 8, 24), None, 60, activity=ActivityType.LEARN)
    review = action_utility(topic, subject, date(2026, 8, 24), None, 60, activity=ActivityType.REVIEW)
    assert learn.activity_fit > review.activity_fit
    assert learn.per_minute > review.per_minute


def test_due_topic_favors_review_activity():
    topic = Topic("t", "s", "Topic", mastery=0.85, next_review_due=date(2026, 8, 24), memory_retrievability=0.35)
    subject = Subject("s", "Subject", exam_weight=0.5)
    review = action_utility(topic, subject, date(2026, 8, 24), None, 30, activity=ActivityType.REVIEW)
    learn = action_utility(topic, subject, date(2026, 8, 24), None, 30, activity=ActivityType.LEARN)
    assert review.activity_fit > learn.activity_fit
    assert review.per_minute > learn.per_minute


def test_reasons_include_activity_choice():
    topic = Topic("t", "s", "Topic", mastery=0.2)
    subject = Subject("s", "Subject")
    result = action_utility(topic, subject, date(2026, 8, 24), None, 30, activity=ActivityType.LEARN)
    assert any("activity fit: learn" in reason for reason in result.reasons)
