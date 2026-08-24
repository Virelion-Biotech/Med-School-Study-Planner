from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CurriculumMapping:
    knowledge_component_id: str
    curriculum_node_id: str
    source: str
    confidence: float = 1.0
    relation: str = "covers"


def deduplicate_mappings(mappings: list[CurriculumMapping]) -> tuple[CurriculumMapping, ...]:
    seen: set[tuple[str, str, str]] = set()
    result: list[CurriculumMapping] = []
    for mapping in mappings:
        confidence = max(0.0, min(1.0, float(mapping.confidence)))
        item = CurriculumMapping(mapping.knowledge_component_id, mapping.curriculum_node_id, mapping.source.strip(), confidence, mapping.relation.strip() or "covers")
        key = (item.knowledge_component_id, item.curriculum_node_id, item.relation)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return tuple(result)


def mappings_for_kc(mappings: list[CurriculumMapping], knowledge_component_id: str) -> tuple[CurriculumMapping, ...]:
    return tuple(m for m in deduplicate_mappings(mappings) if m.knowledge_component_id == knowledge_component_id)


def mappings_for_node(mappings: list[CurriculumMapping], curriculum_node_id: str) -> tuple[CurriculumMapping, ...]:
    return tuple(m for m in deduplicate_mappings(mappings) if m.curriculum_node_id == curriculum_node_id)
