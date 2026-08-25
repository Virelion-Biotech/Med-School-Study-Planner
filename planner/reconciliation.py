from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class SessionRevision:
    session_id: int
    state: tuple


@dataclass(frozen=True)
class ReconciliationResult:
    status: str
    merged: tuple[SessionRevision, ...] = ()
    conflicts: tuple[int, ...] = ()
    additions_from_client: tuple[int, ...] = ()
    additions_from_server: tuple[int, ...] = ()


def _index(rows: Iterable[SessionRevision]) -> dict[int, SessionRevision]:
    return {row.session_id: row for row in rows}


def reconcile_sessions(
    base: Iterable[SessionRevision],
    server: Iterable[SessionRevision],
    client: Iterable[SessionRevision],
) -> ReconciliationResult:
    """Three-way merge session state.

    A session is auto-mergeable when only one side differs from the base.
    If both server and client changed the same session differently, the
    session is a true conflict and remains unresolved. Deletions are treated
    conservatively: a delete versus an edit is a conflict.
    """
    b = _index(base)
    s = _index(server)
    c = _index(client)
    merged: dict[int, SessionRevision] = {}
    conflicts: list[int] = []
    additions_client: list[int] = []
    additions_server: list[int] = []

    for session_id in sorted(set(b) | set(s) | set(c)):
        base_row = b.get(session_id)
        server_row = s.get(session_id)
        client_row = c.get(session_id)

        if base_row is None:
            if server_row is not None and client_row is not None:
                if server_row.state == client_row.state:
                    merged[session_id] = server_row
                else:
                    conflicts.append(session_id)
            elif client_row is not None:
                merged[session_id] = client_row
                additions_client.append(session_id)
            elif server_row is not None:
                merged[session_id] = server_row
                additions_server.append(session_id)
            continue

        server_changed = server_row != base_row
        client_changed = client_row != base_row

        if not server_changed and not client_changed:
            merged[session_id] = base_row
        elif server_changed and not client_changed:
            if server_row is not None:
                merged[session_id] = server_row
        elif client_changed and not server_changed:
            if client_row is not None:
                merged[session_id] = client_row
        else:
            if server_row == client_row:
                if server_row is not None:
                    merged[session_id] = server_row
            else:
                conflicts.append(session_id)

    if conflicts:
        return ReconciliationResult(
            status="conflict",
            merged=tuple(merged[k] for k in sorted(merged)),
            conflicts=tuple(conflicts),
            additions_from_client=tuple(additions_client),
            additions_from_server=tuple(additions_server),
        )

    return ReconciliationResult(
        status="merged",
        merged=tuple(merged[k] for k in sorted(merged)),
        additions_from_client=tuple(additions_client),
        additions_from_server=tuple(additions_server),
    )
