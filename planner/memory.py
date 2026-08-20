from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
import math


@dataclass(frozen=True)
class MemoryState:
    repetitions: int = 0
    interval_days: int = 0
    ease_factor: float = 2.5
    stability_days: float = 0.0
    last_rating: float | None = None


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def next_memory_state(state: MemoryState, rating: float) -> tuple[MemoryState, int]:
    """SM-2-inspired retention scheduler with bounded stability.

    Rating is a continuous 0..1 recall score. This is intentionally transparent,
    deterministic, and replaceable by a fuller FSRS implementation later.
    """
    r = _clamp(rating)
    ef = state.ease_factor
    if r < 0.6:
        repetitions = 0
        interval = 1
        ef = _clamp(ef - 0.20, 1.3, 3.0)
        stability = max(1.0, state.stability_days * 0.45)
    else:
        repetitions = state.repetitions + 1
        if repetitions == 1:
            interval = 1
        elif repetitions == 2:
            interval = 6
        else:
            interval = max(1, round(max(1, state.interval_days) * ef * (0.70 + 0.30 * r)))
        ef = _clamp(ef + (0.10 - (1.0 - r) * 0.25), 1.3, 3.0)
        stability = max(1.0, (state.stability_days or interval) * (1.15 + 0.55 * r))
        interval = max(interval, round(stability))
    new_state = MemoryState(repetitions, interval, ef, stability, r)
    return new_state, interval


def next_review_date(completed_on: date, state: MemoryState, rating: float) -> date:
    _, interval = next_memory_state(state, rating)
    return completed_on + timedelta(days=interval)


def forgetting_curve(stability_days: float, elapsed_days: float) -> float:
    """Simple exponential retrievability estimate in [0,1]."""
    if stability_days <= 0:
        return 0.0
    return math.exp(-max(0.0, elapsed_days) / stability_days)
