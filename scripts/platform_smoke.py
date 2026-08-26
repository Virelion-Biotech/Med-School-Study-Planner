#!/usr/bin/env python3
"""Fast, dependency-light smoke test for the planner platform contracts."""
from __future__ import annotations

from planner.health import planner_health
from planner.platform_contract import SyncAction, decide_sync
from planner.reconciliation import SessionRevision, reconcile_sessions


def main() -> int:
    health = planner_health(
        capacity_minutes=180,
        quantum_minutes=15,
        max_session_minutes=90,
    )
    assert health.ready, health.checks

    assert decide_sync(4, 4).action is SyncAction.APPLY
    assert decide_sync(3, 4).action is SyncAction.RECONCILE
    assert decide_sync(None, 4).action is SyncAction.REFRESH

    base = [
        SessionRevision(1, ("2026-08-26", 60, "new")),
        SessionRevision(2, ("2026-08-27", 45, "review")),
    ]
    server = [
        SessionRevision(1, ("2026-08-26", 75, "new")),
        SessionRevision(2, ("2026-08-27", 45, "review")),
    ]
    client = [
        SessionRevision(1, ("2026-08-26", 60, "new")),
        SessionRevision(2, ("2026-08-27", 30, "review")),
    ]
    result = reconcile_sessions(base, server, client)
    assert result.status == "merged"
    assert len(result.merged) == 2

    print("planner platform smoke: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
