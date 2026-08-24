from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from typing import Iterable

from .state import CurriculumNode


@dataclass(frozen=True)
class CurriculumRecord:
    source: str
    external_id: str | None
    name: str
    node_type: str
    parent_external_id: str | None = None


@dataclass(frozen=True)
class IngestIssue:
    severity: str
    code: str
    message: str
    record_index: int | None = None


@dataclass(frozen=True)
class CurriculumSnapshot:
    source: str
    version: str
    nodes: tuple[CurriculumNode, ...]
    issues: tuple[IngestIssue, ...]
    fingerprint: str


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")


def stable_node_id(source: str, external_id: str | None, name: str, parent_id: str | None = None) -> str:
    if external_id:
        token = f"{source}|external|{external_id.strip()}"
    else:
        token = f"{source}|name|{_slug(name)}|parent|{parent_id or ''}"
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]
    return f"cur-{_slug(source)}-{digest}"


def _fingerprint(nodes: Iterable[CurriculumNode]) -> str:
    payload = "\n".join(
        f"{n.id}|{n.name}|{n.node_type}|{n.parent_id or ''}|{n.source}"
        for n in sorted(nodes, key=lambda x: x.id)
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def ingest_records(source: str, version: str, records: list[CurriculumRecord]) -> CurriculumSnapshot:
    issues: list[IngestIssue] = []
    nodes: list[CurriculumNode] = []
    ext_to_id: dict[str, str] = {}
    seen_keys: set[tuple[str, str, str | None]] = set()

    for index, record in enumerate(records):
        name = record.name.strip()
        node_type = record.node_type.strip().lower()
        if not name:
            issues.append(IngestIssue("error", "empty_name", "curriculum record has an empty name", index))
            continue
        if not node_type:
            issues.append(IngestIssue("error", "empty_type", f"curriculum record '{name}' has no node type", index))
            continue
        parent_id = None
        if record.parent_external_id:
            parent_id = ext_to_id.get(record.parent_external_id)
            if parent_id is None:
                issues.append(IngestIssue("error", "unknown_parent", f"parent '{record.parent_external_id}' is not defined before child '{name}'", index))
                continue
        key = (name.casefold(), node_type, parent_id)
        if key in seen_keys:
            issues.append(IngestIssue("warning", "duplicate", f"duplicate curriculum record '{name}' merged", index))
            continue
        node_id = stable_node_id(source, record.external_id, name, parent_id)
        if record.external_id:
            if record.external_id in ext_to_id:
                issues.append(IngestIssue("warning", "duplicate_external_id", f"external id '{record.external_id}' repeated", index))
                continue
            ext_to_id[record.external_id] = node_id
        seen_keys.add(key)
        nodes.append(CurriculumNode(node_id, name, node_type, parent_id, source))

    return CurriculumSnapshot(source, version, tuple(nodes), tuple(issues), _fingerprint(nodes))


def validate_snapshot(snapshot: CurriculumSnapshot) -> tuple[IngestIssue, ...]:
    issues = list(snapshot.issues)
    ids = {node.id for node in snapshot.nodes}
    for node in snapshot.nodes:
        if node.parent_id and node.parent_id not in ids:
            issues.append(IngestIssue("error", "orphan", f"node '{node.name}' references missing parent"))
    graph: dict[str, str | None] = {node.id: node.parent_id for node in snapshot.nodes}
    for node_id in graph:
        seen: set[str] = set()
        current = node_id
        while current is not None:
            if current in seen:
                issues.append(IngestIssue("error", "cycle", f"curriculum cycle detected at '{node_id}'"))
                break
            seen.add(current)
            current = graph.get(current)
    return tuple(issues)
