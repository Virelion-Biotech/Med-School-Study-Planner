from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .storage import StudyDB


class WorkspaceConflict(RuntimeError):
    """Raised when a client attempts to mutate stale workspace state."""


@dataclass(frozen=True)
class WorkspaceRevision:
    revision: int
    updated_at: str | None = None


class WorkspaceRevisionStore:
    """Per-workspace optimistic-concurrency primitive.

    StudyDB already isolates workspaces by CURRENT_USER. This layer adds a
    monotonically increasing revision inside that isolated database. Clients
    can use the revision as an opaque ETag-like token when coordinating
    multiple tabs/devices.
    """

    def __init__(self, db: StudyDB) -> None:
        self.db = db
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with self.db.connection() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS workspace_revision (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    revision INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )"""
            )
            conn.execute(
                "INSERT OR IGNORE INTO workspace_revision(id, revision) VALUES (1, 0)"
            )

    def current(self) -> WorkspaceRevision:
        self._ensure_schema()
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT revision, updated_at FROM workspace_revision WHERE id=1"
            ).fetchone()
        return WorkspaceRevision(int(row["revision"]), row["updated_at"])

    def claim(self, expected_revision: Optional[int] = None) -> WorkspaceRevision:
        """Atomically reserve the next revision.

        The compare-and-swap happens before a mutating request performs its
        writes. A failed request may therefore consume a revision, which is
        intentional: revisions are versions, not contiguous event counts.
        """
        self._ensure_schema()
        with self.db.connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT revision FROM workspace_revision WHERE id=1"
            ).fetchone()
            current = int(row["revision"])
            if expected_revision is not None and expected_revision != current:
                raise WorkspaceConflict(
                    f"stale workspace revision: expected {expected_revision}, current {current}"
                )
            next_revision = current + 1
            conn.execute(
                "UPDATE workspace_revision SET revision=?, updated_at=CURRENT_TIMESTAMP WHERE id=1",
                (next_revision,),
            )
            return WorkspaceRevision(next_revision)
