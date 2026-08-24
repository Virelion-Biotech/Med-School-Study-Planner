from __future__ import annotations

from dataclasses import dataclass

from .models import Topic, clamp


@dataclass(frozen=True)
class KCConflict:
    knowledge_component_id: str
    topic_ids: tuple[str, ...]
    mastery_min: float
    mastery_max: float
    spread: float
    severity: str
    message: str


def detect_kc_conflicts(kc_id: str, topics: list[Topic], threshold: float = 0.25) -> KCConflict | None:
    if len(topics) < 2:
        return None
    values = [clamp(t.mastery) for t in topics]
    low, high = min(values), max(values)
    spread = high - low
    if spread < threshold:
        return None
    severity = "high" if spread >= 0.50 else "moderate"
    return KCConflict(
        kc_id,
        tuple(sorted(t.id for t in topics)),
        low,
        high,
        spread,
        severity,
        f"Mapped curriculum representations disagree on mastery by {spread:.0%}; use recent evidence before treating the KC as mastered.",
    )
