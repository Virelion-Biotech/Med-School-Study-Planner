from planner.calibration import calibrate_binary_predictions, calibration_passes
from planner.model_validation import validate_models


def test_perfect_probabilities_are_calibrated():
    report = calibrate_binary_predictions([0.0, 1.0, 0.0, 1.0], [False, True, False, True])
    assert report.brier_score == 0.0
    assert report.expected_calibration_error == 0.0
    assert calibration_passes(report)


def test_poorly_calibrated_probabilities_are_flagged():
    report = calibrate_binary_predictions([0.99] * 20, [False] * 20)
    assert report.expected_calibration_error > 0.9
    assert not calibration_passes(report)


def test_synthetic_model_validation_is_deterministic():
    first = validate_models(seed=9, observations=500)
    second = validate_models(seed=9, observations=500)
    assert first == second
    assert first.bkt.samples == 500
    assert first.fsrs.samples == 500
