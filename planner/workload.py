from __future__ import annotations

from statistics import median

from .models import Topic
from .state import WorkloadEstimate


def initial_workload(topic: Topic) -> WorkloadEstimate:
    """Convert the existing hour estimate into an explicit prior with uncertainty."""
    predicted = max(5.0, topic.estimated_hours * 60.0)
    return WorkloadEstimate(
        topic_id=topic.id,
        predicted_minutes=predicted,
        lower_bound_minutes=predicted * 0.60,
        upper_bound_minutes=predicted * 1.75,
        confidence=0.25,
        sample_count=0,
        source="topic_prior",
    )


def update_workload(estimate: WorkloadEstimate, actual_minutes: list[int]) -> WorkloadEstimate:
    """Robustly learn from observed session durations without overreacting to one outlier."""
    clean = [float(v) for v in actual_minutes if v > 0]
    if not clean:
        return estimate
    observed = median(clean[-9:])
    n = estimate.sample_count + len(clean)
    # Increase the learned contribution gradually; priors remain useful for cold-start.
    alpha = min(0.85, 0.25 + 0.10 * len(clean))
    predicted = (1.0 - alpha) * estimate.predicted_minutes + alpha * observed
    confidence = min(0.95, max(estimate.confidence, 0.25 + 0.05 * n))
    spread = max(0.25, 0.90 / (confidence + 0.15))
    return WorkloadEstimate(
        topic_id=estimate.topic_id,
        predicted_minutes=predicted,
        lower_bound_minutes=max(5.0, predicted * max(0.50, 1.0 - spread / 2)),
        upper_bound_minutes=predicted * (1.0 + spread),
        confidence=confidence,
        sample_count=n,
        source="student_history",
    )
