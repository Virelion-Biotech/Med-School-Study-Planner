from __future__ import annotations

from dataclasses import dataclass
import math
import random


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
    margin = 1.96 * se
    return PairedEffect(n, mean_difference, sd, se, dz, mean_difference - margin, mean_difference + margin)


def paired_bootstrap_ci(
    reference: list[float],
    candidate: list[float],
    *,
    resamples: int = 4000,
    seed: int = 17,
) -> tuple[float, float]:
    if len(reference) != len(candidate):
        raise ValueError("paired samples must have equal length")
    if len(reference) < 2:
        raise ValueError("at least two paired observations are required")
    if resamples < 100:
        raise ValueError("resamples must be at least 100")
    rng = random.Random(seed)
    differences = [b - a for a, b in zip(reference, candidate)]
    n = len(differences)
    samples: list[float] = []
    for _ in range(resamples):
        sample = [differences[rng.randrange(n)] for _ in range(n)]
        samples.append(sum(sample) / n)
    samples.sort()
    lo = samples[int(0.025 * (len(samples) - 1))]
    hi = samples[int(0.975 * (len(samples) - 1))]
    return lo, hi


def paired_from_metrics(metrics, field: str, reference: str, candidate: str) -> PairedEffect:
    reference_by_seed = {m.student_seed: float(getattr(m, field)) for m in metrics if m.planner == reference}
    candidate_by_seed = {m.student_seed: float(getattr(m, field)) for m in metrics if m.planner == candidate}
    seeds = sorted(set(reference_by_seed) & set(candidate_by_seed))
    return paired_effect([reference_by_seed[s] for s in seeds], [candidate_by_seed[s] for s in seeds])
