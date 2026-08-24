from __future__ import annotations

from dataclasses import dataclass
from statistics import mean

from .simulation import SimulationMetrics


@dataclass(frozen=True)
class PopulationComparison:
    planners: tuple[str, ...]
    samples: int
    mean_mastery: dict[str, float]
    mean_retention: dict[str, float]
    mean_completion_rate: dict[str, float]
    mean_topic_coverage: dict[str, float]
    mean_deadline_coverage: dict[str, float]
    mean_overdue_reviews: dict[str, float]
    mean_fairness_gap_minutes: dict[str, float]


def _group(metrics: list[SimulationMetrics], field: str) -> dict[str, float]:
    groups: dict[str, list[float]] = {}
    for metric in metrics:
        groups.setdefault(metric.planner, []).append(float(getattr(metric, field)))
    return {planner: mean(values) for planner, values in groups.items()}


def summarize_population(metrics: list[SimulationMetrics]) -> PopulationComparison:
    planners = tuple(sorted({m.planner for m in metrics}))
    seeds = len({m.student_seed for m in metrics})
    return PopulationComparison(
        planners=planners,
        samples=seeds,
        mean_mastery=_group(metrics, "mean_mastery"),
        mean_retention=_group(metrics, "mean_retention"),
        mean_completion_rate=_group(metrics, "completion_rate"),
        mean_topic_coverage=_group(metrics, "topic_coverage"),
        mean_deadline_coverage=_group(metrics, "deadline_coverage"),
        mean_overdue_reviews=_group(metrics, "overdue_reviews"),
        mean_fairness_gap_minutes=_group(metrics, "fairness_gap_minutes"),


def deltas(summary: PopulationComparison, reference: str, candidate: str) -> dict[str, float]:
    if reference not in summary.planners or candidate not in summary.planners:
        raise ValueError("reference and candidate planners must be present")
    return {
        "mastery": summary.mean_mastery[candidate] - summary.mean_mastery[reference],
        "retention": summary.mean_retention[candidate] - summary.mean_retention[reference],
        "completion_rate": summary.mean_completion_rate[candidate] - summary.mean_completion_rate[reference],
        "topic_coverage": summary.mean_topic_coverage[candidate] - summary.mean_topic_coverage[reference],
        "deadline_coverage": summary.mean_deadline_coverage[candidate] - summary.mean_deadline_coverage[reference],
        "overdue_reviews": summary.mean_overdue_reviews[reference] - summary.mean_overdue_reviews[candidate],
        "fairness_gap_minutes": summary.mean_fairness_gap_minutes[reference] - summary.mean_fairness_gap_minutes[candidate],
    }
