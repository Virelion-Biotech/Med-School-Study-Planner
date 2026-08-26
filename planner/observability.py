"""Structured, dependency-free observability primitives for the planner.

The planner is intentionally deterministic at its core.  This module adds
structured events around that core without coupling it to a logging vendor.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping
import json
import time


@dataclass(frozen=True)
class PlannerEvent:
    name: str
    timestamp: str
    duration_ms: float | None = None
    workspace_revision: int | None = None
    plan_fingerprint: str | None = None
    attributes: Mapping[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))


def event(name: str, *, revision: int | None = None,
          fingerprint: str | None = None, **attributes: Any) -> PlannerEvent:
    return PlannerEvent(
        name=name,
        timestamp=datetime.now(timezone.utc).isoformat(),
        workspace_revision=revision,
        plan_fingerprint=fingerprint,
        attributes=attributes,
    )


class Timer:
    """Small context manager for deterministic duration instrumentation."""
    def __enter__(self) -> "Timer":
        self.started = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.duration_ms = (time.perf_counter() - self.started) * 1000.0


def complete(evt: PlannerEvent, duration_ms: float) -> PlannerEvent:
    return PlannerEvent(
        name=evt.name,
        timestamp=evt.timestamp,
        duration_ms=round(max(0.0, duration_ms), 3),
        workspace_revision=evt.workspace_revision,
        plan_fingerprint=evt.plan_fingerprint,
        attributes=evt.attributes,
    )
