"""Serializable audit records for why a study action was selected."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any
import json


@dataclass(frozen=True)
class DecisionAudit:
    topic_id: str
    activity: str
    utility_per_minute: float
    reasons: tuple[str, ...] = ()
    signals: dict[str, float] = field(default_factory=dict)
    constraints: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))


def build_audit(*, topic_id: str, activity: str, utility_per_minute: float,
                reasons: list[str] | tuple[str, ...] = (),
                signals: dict[str, float] | None = None,
                constraints: list[str] | tuple[str, ...] = ()) -> DecisionAudit:
    if utility_per_minute != utility_per_minute:
        raise ValueError("utility_per_minute must not be NaN")
    return DecisionAudit(
        topic_id=topic_id,
        activity=activity,
        utility_per_minute=float(utility_per_minute),
        reasons=tuple(reasons),
        signals={k: float(v) for k, v in (signals or {}).items()},
        constraints=tuple(constraints),
    )
