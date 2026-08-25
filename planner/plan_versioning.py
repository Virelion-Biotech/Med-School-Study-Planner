from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import date
from typing import Iterable

from .models import StudySession
from .workspace_revision import WorkspaceConflict, WorkspaceRevision, WorkspaceRevisionStore


def plan_fingerprint(sessions: Iterable[StudySession]) -> str:
    """Return a deterministic fingerprint for a proposed session plan."""
    canonical = []
    for session in sessions:
        payload = asdict(session)
        payload["date"] = session.date.isoformat()
        payload["session_type"] = session.session_type.value
        payload["activity"] = session.activity.value
        canonical.append(payload)
    canonical.sort(key=lambda row: (
        row["date"], row["topic_id"], row["planned_minutes"],
        row["session_type"], row["activity"],
    ))
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def claim_plan_revision(
    revisions: WorkspaceRevisionStore,
    expected_revision: int | None,
) -> WorkspaceRevision:
    """Claim a workspace revision before replacing an uncompleted plan."""
    try:
        return revisions.claim(expected_revision)
    except WorkspaceConflict:
        raise
