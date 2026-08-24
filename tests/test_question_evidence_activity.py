from planner.activity import choose_default_activity
from planner.models import ActivityType


def test_cold_start_keeps_prior_behavior():
    assert choose_default_activity(False, 0.8) is ActivityType.MIXED
    assert choose_default_activity(True, 0.8) is ActivityType.REVIEW


def test_weak_empirical_performance_prefers_questions():
    assert choose_default_activity(False, 0.8, 0.35, confidence_gap=0.0, evidence_strength=0.8) is ActivityType.QUESTIONS


def test_overconfidence_prefers_questions():
    assert choose_default_activity(False, 0.8, 0.65, confidence_gap=0.25, evidence_strength=0.8) is ActivityType.QUESTIONS


def test_due_topic_with_strong_performance_prefers_review():
    assert choose_default_activity(True, 0.8, 0.90, confidence_gap=0.0, evidence_strength=0.8) is ActivityType.REVIEW
