from planner.ablation import default_ablation_variants
from planner.statistics import paired_effect


def test_paired_effect_has_zero_delta_for_identical_samples():
    result = paired_effect([1.0, 2.0, 3.0], [1.0, 2.0, 3.0])
    assert result.mean_difference == 0.0
    assert result.cohens_dz == 0.0
    assert result.ci95_low == 0.0
    assert result.ci95_high == 0.0


def test_paired_effect_positive_candidate_improvement():
    result = paired_effect([1.0, 2.0, 3.0], [2.0, 3.0, 5.0])
    assert result.mean_difference > 0
    assert result.samples == 3


def test_ablation_variants_cover_full_and_components():
    names = {v.name for v in default_ablation_variants()}
    assert {"full_adaptive", "no_evidence", "no_reviews", "no_fairness", "legacy"} <= names
