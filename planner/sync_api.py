from __future__ import annotations

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from .api import app, db
from .workspace_revision import WorkspaceConflict, WorkspaceRevisionStore
from .workspace_sync import claim_mutation, is_mutating_planner_path, revision_headers, workspace_state

_revisions = WorkspaceRevisionStore(db)


@app.middleware("http")
async def workspace_revision_middleware(request: Request, call_next):
    if not is_mutating_planner_path(request.method, request.url.path):
        return await call_next(request)

    try:
        revision = claim_mutation(_revisions, request.headers.get("x-planner-revision"))
    except ValueError as exc:
        return JSONResponse(status_code=422, content={"detail": str(exc)})
    except WorkspaceConflict as exc:
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


@app.get("/workspace/state")
def get_workspace_state():
    state = workspace_state(db, _revisions)
    return state


@app.get("/workspace/revision")
def get_workspace_revision():
    current = _revisions.current()
    return {"revision": current.revision, "updated_at": current.updated_at}
