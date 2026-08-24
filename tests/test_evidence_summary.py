from datetime import datetime, timezone

from planner.evidence import evidence_activity_adjustment
from planner.questions import QuestionOutcome


def test_question_outcome_retains_confidence_and_time():
    outcome = QuestionOutcome("q1", "topic", False, 42.0, 0.9, "kc")
    assert outcome.response_time_seconds == 42.0
    assert outcome.confidence == 0.9


def test_evidence_adjustment_increases_question_need_when_accuracy_is_weak():
    from planner.evidence import EvidenceSummary
    weak = evidence_activity_adjustment(EvidenceSummary(attempts=20, recent_attempts=10, recent_accuracy=0.30, confidence=0.85, evidence_strength=0.8))
    strong = evidence_activity_adjustment(EvidenceSummary(attempts=20, recent_attempts=10, recent_accuracy=0.90, confidence=0.85, evidence_strength=0.8))
    assert weak["questions"] > strong["questions"]
    assert weak["confidence_gap"] > 0
