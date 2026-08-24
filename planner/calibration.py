from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class CalibrationBin:
    lower: float
    upper: float
    count: int
    mean_prediction: float
    observed_rate: float
    absolute_gap: float


@dataclass(frozen=True)
class CalibrationReport:
    samples: int
    bins: tuple[CalibrationBin, ...]
    brier_score: float
    log_loss: float
    expected_calibration_error: float
    max_calibration_error: float


def _safe_probability(value: float) -> float:
    return min(1.0 - 1e-12, max(1e-12, float(value)))


def calibrate_binary_predictions(
    predictions: list[float],
    outcomes: list[bool],
    bins: int = 10,
) -> CalibrationReport:
    if len(predictions) != len(outcomes):
        raise ValueError("predictions and outcomes must have equal length")
    if not predictions:
        return CalibrationReport(0, (), 0.0, 0.0, 0.0, 0.0)
    bins = max(2, min(100, bins))
    points = [(_safe_probability(p), bool(y)) for p, y in zip(predictions, outcomes)]
    buckets: list[list[tuple[float, bool]]] = [[] for _ in range(bins)]
    for p, y in points:
        idx = min(bins - 1, int(p * bins))
        buckets[idx].append((p, y))
    report_bins: list[CalibrationBin] = []
    ece = 0.0
    mce = 0.0
    n = len(points)
    for i, bucket in enumerate(buckets):
        if not bucket:
            continue
        mean_prediction = sum(p for p, _ in bucket) / len(bucket)
        observed = sum(1.0 for _, y in bucket if y) / len(bucket)
        gap = abs(mean_prediction - observed)
        lower = i / bins
        upper = (i + 1) / bins
        report_bins.append(CalibrationBin(lower, upper, len(bucket), mean_prediction, observed, gap))
        ece += (len(bucket) / n) * gap
        mce = max(mce, gap)
    brier = sum((p - float(y)) ** 2 for p, y in points) / n
    log_loss = -sum(float(y) * math.log(p) + (1.0 - float(y)) * math.log(1.0 - p) for p, y in points) / n
    return CalibrationReport(n, tuple(report_bins), brier, log_loss, ece, mce)


def calibration_passes(report: CalibrationReport, max_ece: float = 0.10, max_brier: float = 0.20) -> bool:
    return report.samples > 0 and report.expected_calibration_error <= max_ece and report.brier_score <= max_brier
