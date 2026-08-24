from planner.irt import IRTItem, IRTResponse
from planner.irt_analysis import estimate_theta


def _responses(correct: bool, attempts: int = 1000):
    out = []
    for i in range(attempts):
        q = f"q-{i % 100}"
        out.append((IRTResponse(q, correct, "student"), IRTItem(q, difficulty=0.0, discrimination=1.0)))
    return out


def test_irt_refuses_small_sample():
    estimate = estimate_theta(_responses(True, 50))
    assert estimate.reliable is False
    assert estimate.standard_error is None


def test_irt_high_performance_produces_positive_theta():
    estimate = estimate_theta(_responses(True))
    assert estimate.reliable is True
    assert estimate.theta > 0
    assert estimate.standard_error is not None
