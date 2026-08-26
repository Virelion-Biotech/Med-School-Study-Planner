from __future__ import annotations

import re

from fastapi import Request
from fastapi.responses import JSONResponse

from .api import app, db
from .storage import CURRENT_USER
from .workspace_revision import WorkspaceConflict, WorkspaceRevisionStore
from .workspace_sync import claim_mutation, is_mutating_planner_path, revision_headers, workspace_state

_revisions = WorkspaceRevisionStore(db)


def _bind_user(request: Request) -> str:
    raw = request.headers.get("x-planner-user", "default").strip()
    if not raw or len(raw) > 128 or not re.fullmatch(r"[A-Za-z0-9._:-]+", raw):
        return "default"
    return raw


@app.middleware("http")
async def workspace_revision_middleware(request: Request, call_next):
    token = CURRENT_USER.set(_bind_user(request))
    try:
        if not is_mutating_planner_path(request.method, request.url.path):
            return await call_next(request)

        try:
            revision = claim_mutation(_revisions, request.headers.get("x-planner-revision"))
        except ValueError as exc:
            return JSONResponse(status_code=422, content={"detail": str(exc)})
        except WorkspaceConflict:
            current = _revisions.current()
            return JSONResponse(
                status_code=409,
                content={
                    "detail": "Workspace changed on another tab or device. Refresh before retrying.",
                    "error": "workspace_conflict",
                    "expected": request.headers.get("x-planner-revision"),
                    "current": current.revision,
                },
                headers=revision_headers(current.revision),
            )

        response = await call_next(request)
        for key, value in revision_headers(revision).items():
            response.headers[key] = value
        return response
    finally:
        CURRENT_USER.reset(token)


@app.get("/workspace/state")
def get_workspace_state():
    return workspace_state(db, _revisions)


@app.get("/workspace/revision")
def get_workspace_revision():
    current = _revisions.current()
    return {"revision": current.revision, "updated_at": current.updated_at}
