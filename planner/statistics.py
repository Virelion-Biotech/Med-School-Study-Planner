from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class PairedEffect:
    samples: int
    mean_difference: float
    standard_deviation: float
    standard_error: float
    cohens_dz: float
    ci95_low: float
    ci95_high: float


def paired_effect(reference: list[float], candidate: list[float]) -> PairedEffect:
    if len(reference) != len(candidate):
        raise ValueError("paired samples must have equal length")
    n = len(reference)
    if n < 2:
        raise ValueError("at least two paired observations are required")
    differences = [b - a for a, b in zip(reference, candidate)]
    mean_difference = sum(differences) / n
    variance = sum((d - mean_difference) ** 2 for d in differences) / (n - 1)
    sd = math.sqrt(max(variance, 0.0))
    se = sd / math.sqrt(n)
    dz = mean_difference / sd if sd > 0 else 0.0
    # Normal approximation keeps this dependency-free and is adequate for the
    # simulator's large paired populations; it is explicitly not a claim of
    # exact small-sample inference.
    margin = 1.96 * se
    return PairedEffect(n, mean_difference, sd, se, dz, mean_difference - margin, mean_difference + margin)


def paired_from_metrics(metrics, field: str, reference: str, candidate: str) -> PairedEffect:
    reference_by_seed = {m.student_seed: float(getattr(m, field)) for m in metrics if m.planner == reference}
    candidate_by_seed = {m.student_seed: float(getattr(m, field)) for m in metrics if m.planner == candidate}
    seeds = sorted(set(reference_by_seed) & set(candidate_by_seed))
    return paired_effect([reference_by_seed[s] for s in seeds], [candidate_by_seed[s] for s in seeds])
