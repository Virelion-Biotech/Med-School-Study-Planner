from __future__ import annotations

from collections import defaultdict

from .state import CurriculumNode, KnowledgeComponent


class CurriculumGraph:
    """Small in-memory graph for reusable school/USMLE/personal mappings."""

    def __init__(self, nodes: list[CurriculumNode] | None = None) -> None:
        self._nodes = {node.id: node for node in nodes or []}
        self._children: dict[str, set[str]] = defaultdict(set)
        for node in self._nodes.values():
            if node.parent_id:
                self._children[node.parent_id].add(node.id)

    def add(self, node: CurriculumNode) -> None:
        if node.id in self._nodes:
            raise ValueError(f"curriculum node already exists: {node.id}")
        self._nodes[node.id] = node
        if node.parent_id:
            self._children[node.parent_id].add(node.id)

    def children(self, node_id: str) -> tuple[CurriculumNode, ...]:
        return tuple(self._nodes[child] for child in sorted(self._children.get(node_id, ())))

    def ancestors(self, node_id: str) -> tuple[CurriculumNode, ...]:
        result: list[CurriculumNode] = []
        current = self._nodes.get(node_id)
        while current and current.parent_id:
            parent = self._nodes.get(current.parent_id)
            if parent is None:
                break
            result.append(parent)
            current = parent
        return tuple(result)

    def roots(self, source: str | None = None) -> tuple[CurriculumNode, ...]:
        roots = [n for n in self._nodes.values() if n.parent_id is None and (source is None or n.source == source)]
        return tuple(sorted(roots, key=lambda n: n.id))


def map_knowledge_components(
    components: list[KnowledgeComponent], curriculum_ids: dict[str, list[str]]
) -> dict[str, tuple[str, ...]]:
    """Return KC -> curriculum nodes without forcing a single curriculum hierarchy."""
    return {kc.id: tuple(curriculum_ids.get(kc.id, ())) for kc in components}
