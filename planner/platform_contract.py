from __future__ import annotations

"""Stable, dependency-free contracts shared by the planner platform.

This module intentionally contains no FastAPI, database, or UI code.  It is the
boundary between the adaptive engine and clients that need to synchronize,
inspect readiness, and present planner decisions.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


class SyncAction(str, Enum):
    APPLY = "apply"
    REFRESH = "refresh"
    RECONCILE = "reconcile"
    REJECT = "reject"


@dataclass(frozen=True)
class WorkspaceSnapshot:
    user_id: str
    revision: int
    plan_fingerprint: str | None = None


@dataclass(frozen=True)
class SyncDecision:
    action: SyncAction
    expected_revision: int
    current_revision: int
    reason: str

    @property
    def stale(self) -> bool:
        return self.expected_revision != self.current_revision


def decide_sync(expected_revision: int | None, current_revision: int) -> SyncDecision:
    """Return a conservative synchronization decision.

    Missing revision is treated as a refresh requirement for mutating clients;
    matching revisions can safely apply; stale revisions require reconciliation
    rather than an unconditional overwrite.
    """
    if current_revision < 0:
        raise ValueError("current_revision must be non-negative")
    if expected_revision is None:
        return SyncDecision(
            SyncAction.REFRESH,
            -1,
            current_revision,
            "missing_revision",
        )
    if expected_revision < 0:
        raise ValueError("expected_revision must be non-negative")
    if expected_revision == current_revision:
        return SyncDecision(
            SyncAction.APPLY,
            expected_revision,
            current_revision,
            "revision_matches",
        )
    return SyncDecision(
        SyncAction.RECONCILE,
        expected_revision,
        current_revision,
        "revision_stale",
    )


@dataclass(frozen=True)
class ReadinessIssue:
    code: str
    message: str
    severity: str = "error"
    details: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PlatformReadiness:
    ready: bool
    issues: tuple[ReadinessIssue, ...] = ()

    @classmethod
    def from_issues(cls, issues: list[ReadinessIssue]) -> "PlatformReadiness":
        return cls(
            ready=not any(issue.severity == "error" for issue in issues),
            issues=tuple(issues),
        )


@dataclass(frozen=True)
class PlannerLifecycle:
    """Compact state machine for the end-to-end student loop."""

    stages: tuple[str, ...] = (
        "curriculum",
        "student_state",
        "plan",
        "session",
        "evidence",
        "replan",
    )

    def validate(self, completed: list[str]) -> tuple[str, ...]:
        unknown = sorted(set(completed) - set(self.stages))
        if unknown:
            raise ValueError(f"unknown lifecycle stages: {unknown}")
        positions = [self.stages.index(stage) for stage in completed]
        if positions != sorted(positions):
            raise ValueError("lifecycle stages must progress monotonically")
        return tuple(stage for stage in self.stages if stage in completed)
