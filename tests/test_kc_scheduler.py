from planner.kc_state import KCSignal, aggregate_topic_kc_signals, merge_topic_evidence
from planner.models import Topic
from planner.state import StudentKnowledgeState


def test_kc_signal_weights_observations():
    states = [
        StudentKnowledgeState("kc", mastery_probability=0.2, uncertainty=0.6, observations=1),
        StudentKnowledgeState("kc", mastery_probability=0.8, uncertainty=0.2, observations=9),
    ]
    signal = aggregate_topic_kc_signals(states, ("topic-a",), ("school", "usmle"))
    assert signal.mastery > 0.7
    assert signal.observations == 10
    assert signal.mapped_sources == ("school", "usmle")


def test_evidence_merges_by_attempt_count():
    attempts, accuracy, gap = merge_topic_evidence([(10, 0.3, 0.2), (30, 0.9, 0.0)])
    assert attempts == 40
    assert round(accuracy, 3) == 0.75
    assert round(gap, 3) == 0.05


def test_unmapped_topic_remains_unchanged():
    topic = Topic("t", "s", "Topic", mastery=0.42)
    assert topic.mastery == 0.42
