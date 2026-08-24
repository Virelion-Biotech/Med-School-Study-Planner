from planner.irt import IRTItem, evidence_sufficient, probability_correct
from planner.readiness import readiness_from_signals


def test_readiness_is_componentized_and_interpretable():
    r = readiness_from_signals(0.8, 0.7, 0.6, 0.5, 1.0)
    assert 0.5 < r.score < 0.8
    assert r.label in {"Moderate", "Good"}


def test_irt_probability_is_bounded_and_difficulty_sensitive():
    easy = probability_correct(0.0, IRTItem("easy", difficulty=-1, discrimination=1))
    hard = probability_correct(0.0, IRTItem("hard", difficulty=1, discrimination=1))
    assert 0 < hard < easy < 1


def test_irt_requires_substantial_evidence():
    assert not evidence_sufficient(999, 100)
    assert not evidence_sufficient(1000, 99)
    assert evidence_sufficient(1000, 100)
