from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta

from .memory import MemoryState, next_memory_state
from .models import Topic, clamp


def update_topic_from_session(topic: Topic, actual_minutes: int, score: float, completed_on: date, memory: MemoryState | None = None) -> tuple[Topic, MemoryState]:
    """Update mastery and retention state from completed performance."""
    score = clamp(score)
    prior = topic.mastery
    learning_gain = 0.10 + 0.25 * score * (1.0 - prior)
    mastery = clamp(prior + learning_gain)
    state, interval_days = next_memory_state(memory or MemoryState(), score)
    updated = replace(
        topic,
        mastery=mastery,
        last_studied=completed_on,
        next_review_due=completed_on + timedelta(days=interval_days),
    )
    return updated, state


def recalibrated_complexity(topic: Topic, historical_minutes: list[int], target_hours: float | None = None) -> float:
    """Blend initial complexity with observed time burden while resisting outliers."""
    if not historical_minutes:
        return topic.complexity
    cleaned = sorted(max(1, int(v)) for v in historical_minutes)
    median_minutes = cleaned[len(cleaned) // 2]
    target = target_hours or max(topic.estimated_hours, 0.5)
    ratio = (median_minutes / 60.0) / target
    observation_weight = min(0.65, 0.15 + 0.10 * len(cleaned))
    observed_score = ratio / (1.0 + ratio)
    return clamp((1.0 - observation_weight) * topic.complexity + observation_weight * observed_score)
