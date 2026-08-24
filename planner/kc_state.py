from __future__ import annotations

from dataclasses import dataclass
from statistics import mean

from .models import clamp
from .state import StudentKnowledgeState


@dataclass(frozen=True)
class KCSignal:
    knowledge_component_id: str
    mastery: float
    uncertainty: float
    observations: int
    mapped_topic_ids: tuple[str, ...] = ()
    mapped_sources: tuple[str, ...] = ()


def aggregate_topic_kc_signals(
    states: list[StudentKnowledgeState],
    topic_ids: tuple[str, ...] = (),
    sources: tuple[str, ...] = (),
) -> KCSignal:
    if not states:
        return KCSignal("", 0.50, 1.0, 0, topic_ids, sources)
    weights = [max(1, s.observations + 1) for s in states]
    total = sum(weights)
    mastery = sum(s.mastery_probability * w for s, w in zip(states, weights)) / total
    uncertainty = sum(s.uncertainty * w for s, w in zip(states, weights)) / total
    observations = sum(s.observations for s in states)
    return KCSignal(
        states[0].knowledge_component_id,
        clamp(mastery),
        clamp(uncertainty),
        observations,
        topic_ids,
        tuple(sorted(set(sources))),
    )


def merge_topic_evidence(values: list[tuple[int, float, float]]) -> tuple[int, float, float]:
    """Merge (attempts, accuracy, confidence_gap) using attempts as weights."""
    if not values:
        return 0, 0.5, 0.0
    total = sum(max(0, n) for n, _, _ in values)
    if total == 0:
        return 0, 0.5, 0.0
    accuracy = sum(max(0, n) * a for n, a, _ in values) / total
    gap = sum(max(0, n) * g for n, _, g in values) / total
    return total, clamp(accuracy), clamp(gap)
