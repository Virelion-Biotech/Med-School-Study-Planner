from __future__ import annotations

from fastapi import HTTPException
from pydantic import BaseModel, Field

from .api import app
from .reconciliation import SessionRevision, reconcile_sessions


class RevisionRow(BaseModel):
    session_id: int
    state: list[str | int | float | bool | None] = Field(default_factory=list)


class ReconcileRequest(BaseModel):
    base: list[RevisionRow] = Field(default_factory=list)
    server: list[RevisionRow] = Field(default_factory=list)
    client: list[RevisionRow] = Field(default_factory=list)


def _convert(rows: list[RevisionRow]) -> list[SessionRevision]:
    return [SessionRevision(row.session_id, tuple(row.state)) for row in rows]


@app.post("/v2/reconcile/sessions")
def reconcile_sessions_api(request: ReconcileRequest):
    if len({row.session_id for row in request.base}) != len(request.base):
        raise HTTPException(status_code=422, detail="duplicate session_id in base")
    if len({row.session_id for row in request.server}) != len(request.server):
        raise HTTPException(status_code=422, detail="duplicate session_id in server")
    if len({row.session_id for row in request.client}) != len(request.client):
        raise HTTPException(status_code=422, detail="duplicate session_id in client")
    result = reconcile_sessions(_convert(request.base), _convert(request.server), _convert(request.client))
    return {
        "status": result.status,
        "conflicts": list(result.conflicts),
        "additions_from_client": list(result.additions_from_client),
        "additions_from_server": list(result.additions_from_server),
        "merged": [
            {"session_id": row.session_id, "state": list(row.state)}
            for row in result.merged
        ],
    }
