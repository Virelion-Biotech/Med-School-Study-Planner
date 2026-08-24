from __future__ import annotations

from dataclasses import dataclass

from .calibration import CalibrationReport, calibration_passes
from .statistics import PairedEffect


@dataclass(frozen=True)
class QualityGateResult:
    name: str
    passed: bool
    reason: str


def calibration_gate(name: str, report: CalibrationReport, max_ece: float = 0.10, max_brier: float = 0.20) -> QualityGateResult:
    passed = calibration_passes(report, max_ece=max_ece, max_brier=max_brier)
    return QualityGateResult(
        name,
        passed,
        f"ECE={report.expected_calibration_error:.4f}, Brier={report.brier_score:.4f}, n={report.samples}",
    )


def noninferiority_gate(name: str, effect: PairedEffect, minimum_mean_difference: float = -0.05) -> QualityGateResult:
    passed = effect.mean_difference >= minimum_mean_difference
    return QualityGateResult(
        name,
        passed,
        f"mean_difference={effect.mean_difference:.4f}, CI95=[{effect.ci95_low:.4f}, {effect.ci95_high:.4f}]",
    )
