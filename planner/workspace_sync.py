from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from typing import Any

from .plan_versioning import plan_fingerprint
from .storage import StudyDB
from .workspace_revision import WorkspaceConflict, WorkspaceRevisionStore


MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
MUTATING_PATHS = (
    "/profile",
    "/subjects",
    "/topics",
    "/exams",
    "/plan",
    "/replan",
    "/setup/",
    "/sessions/",
    "/calibrate",
)


def is_mutating_planner_path(method: str, path: str) -> bool:
    if method.upper() not in MUTATING_METHODS:
        return False
    return path in {"/profile", "/subjects", "/topics", "/exams", "/plan", "/replan", "/calibrate"} or any(path.startswith(prefix) for prefix in ("/setup/", "/sessions/"))


def current_plan_fingerprint(snapshot: dict[str, Any]) -> str:
    rows = [
        {
            "date": row.get("session_date"),
            "topic_id": row.get("topic_id"),
            "planned_minutes": int(row.get("planned_minutes", 0)),
            "completed": bool(row.get("completed", False)),
            "activity": row.get("activity"),
            "session_type": row.get("session_type"),
        }
        for row in snapshot.get("sessions", [])
    ]
    rows.sort(key=lambda row: tuple(str(row.get(k, "")) for k in ("date", "topic_id", "planned_minutes", "session_type", "activity", "completed")))
    return hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def workspace_state(db: StudyDB, revisions: WorkspaceRevisionStore) -> dict[str, Any]:
    snapshot = db.snapshot()
    current = revisions.current()
    return {
        "revision": current.revision,
        "updated_at": current.updated_at,
        "plan_fingerprint": current_plan_fingerprint(snapshot),
        "session_count": len(snapshot.get("sessions", [])),
        "uncompleted_session_count": sum(1 for row in snapshot.get("sessions", []) if not row.get("completed")),
    }


def parse_revision(value: str | None) -> int | None:
    if value is None or not value.strip():
        return None
    try:
        revision = int(value)
    except ValueError as exc:
        raise ValueError("X-Planner-Revision must be an integer") from exc
    if revision < 0:
        raise ValueError("X-Planner-Revision must be non-negative")
    return revision


def claim_mutation(revisions: WorkspaceRevisionStore, header_value: str | None) -> int:
    """Claim the next workspace version for a mutating request.

    Missing revisions are accepted for backwards compatibility. New clients
    should always send X-Planner-Revision from /workspace/state. Once supplied,
    the value acts as an optimistic compare-and-swap token.
    """
    expected = parse_revision(header_value)
    return revisions.claim(expected).revision


def revision_headers(revision: int) -> dict[str, str]:
    return {
        "X-Planner-Revision": str(revision),
        "Cache-Control": "no-store",
    }


__all__ = [
    "MUTATING_METHODS",
    "MUTATING_PATHS",
    "WorkspaceConflict",
    "claim_mutation",
    "current_plan_fingerprint",
    "is_mutating_planner_path",
    "parse_revision",
    "revision_headers",
    "workspace_state",
]
