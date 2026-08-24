from __future__ import annotations

from dataclasses import dataclass

from .cross_curriculum import CurriculumMapping
from .kc_state import KCStateSummary


@dataclass(frozen=True)
class KCExplanation:
    knowledge_component_id: str
    mastery: float
    uncertainty: float
    evidence_strength: float
    mapped_sources: tuple[str, ...]
    reasons: tuple[str, ...]


def explain_kc(summary: KCStateSummary, mappings: list[CurriculumMapping]) -> KCExplanation:
    selected = [m for m in mappings if m.knowledge_component_id == summary.knowledge_component_id]
    sources = tuple(sorted({m.source for m in selected}))
    reasons: list[str] = []
    if summary.observations:
        reasons.append(f"{summary.observations} observations inform this knowledge estimate")
    else:
        reasons.append("No direct observations yet; cold-start mastery prior is being used")
    if summary.mastery < 0.50:
        reasons.append("Estimated mastery is below 50%, so learning work is favored")
    elif summary.mastery > 0.80:
        reasons.append("Estimated mastery is high; retention and retrieval evidence matter more")
    if summary.uncertainty > 0.35:
        reasons.append("Uncertainty is still high, so the planner avoids overconfident conclusions")
    if len(sources) > 1:
        reasons.append("Evidence is shared across multiple curriculum representations")
    return KCExplanation(summary.knowledge_component_id, summary.mastery, summary.uncertainty, summary.evidence_strength, sources, tuple(reasons))
