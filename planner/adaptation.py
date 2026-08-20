from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta

from .models import Topic


def update_topic_from_session(topic: Topic, actual_minutes: int, score: float, completed_on: date) -> Topic:
    """Update mastery and review interval from a completed session.

    This is deliberately conservative: performance changes mastery now; complexity
    remains mostly historical until enough observations exist for recalibration.
    """
    score = max(0.0, min(1.0, score))
    mastery = max(topic.mastery, min(1.0, topic.mastery + 0.25 * (score - topic.mastery + 0.25)))
    if score >= 0.9:
        interval_days = 14
    elif score >= 0.75:
        interval_days = 7
    elif score >= 0.6:
        interval_days = 3
    else:
        interval_days = 1
    return replace(topic, mastery=mastery, last_studied=completed_on,
                   next_review_due=completed_on + timedelta(days=interval_days))


def recalibrated_complexity(topic: Topic, historical_minutes: list[int], target_hours: float | None = None) -> float:
    """Estimate complexity from observed time-to-mastery, bounded around the prior estimate."""
    if not historical_minutes:
        return topic.complexity
    observed_hours = sum(historical_minutes) / len(historical_minutes) / 60
    target = target_hours or max(topic.estimated_hours, 0.5)
    ratio = observed_hours / target
    return max(0.0, min(1.0, 0.7 * topic.complexity + 0.3 * (ratio / (1 + ratio))))
