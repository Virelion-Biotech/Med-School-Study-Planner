from datetime import date

from planner.cross_curriculum import CurriculumMapping
from planner.kc_conflicts import detect_kc_conflicts
from planner.kc_explanations import explain_kc
from planner.kc_state import KCSignal
from planner.models import Subject, Topic, UserProfile, Exam


def test_kc_explanation_mentions_shared_sources_and_uncertainty():
    summary = KCSignal("kc1", 0.42, 0.60, 3, ("topic1",), ("school", "usmle"))
    explanation = explain_kc(summary, [CurriculumMapping("kc1", "school-hf", "school"), CurriculumMapping("kc1", "usmle-hf", "usmle")])
    assert "school" in explanation.mapped_sources
    assert "usmle" in explanation.mapped_sources
    assert any("Uncertainty" in reason for reason in explanation.reasons)
    assert any("multiple curriculum" in reason for reason in explanation.reasons)


def test_conflict_detector_is_quiet_for_single_topic():
    topic = Topic("t1", "s1", "Heart failure", mastery=0.40)
    assert detect_kc_conflicts("kc1", [topic]) is None


def test_conflict_detector_flags_divergent_representations():
    first = Topic("t1", "s1", "School HF", mastery=0.20)
    second = Topic("t2", "s2", "USMLE HF", mastery=0.85)
    conflict = detect_kc_conflicts("kc1", [first, second], threshold=0.25)
    assert conflict is not None
    assert conflict.severity == "high"
    assert conflict.spread == 0.65
