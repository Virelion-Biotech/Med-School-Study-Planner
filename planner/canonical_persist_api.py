from __future__ import annotations

from datetime import date, timedelta

from fastapi import HTTPException

from .api import app, db
from .models import ActivityType, SessionType, StudySession


@app.post("/v2/plan/persist")
def persist_canonical_plan(request):
    """Generate the canonical KC-aware plan and persist it as the active plan."""
    # Import lazily to avoid coupling package initialization to the V2 app module.
    from .v2_app import AdaptivePlanRequest, adaptive_plan

    if not isinstance(request, AdaptivePlanRequest):
        request = AdaptivePlanRequest.model_validate(request)

    payload = adaptive_plan(request)
    if not payload.get("sessions"):
        return payload | {"persisted": False, "session_ids": []}

    end = request.start_date + timedelta(days=request.days)
    db.delete_uncompleted_sessions_in_range(request.start_date, end)

    sessions: list[StudySession] = []
    for row in payload["sessions"]:
        session_type = SessionType(row.get("session_type", SessionType.NEW.value))
        activity = ActivityType(row.get("activity_type", ActivityType.MIXED.value))
        sessions.append(
            StudySession(
                date.fromisoformat(row["date"]),
                row["topic_id"],
                int(row["planned_minutes"]),
                session_type=session_type,
                activity=activity,
            )
        )
    ids = db.save_sessions(sessions)
    return payload | {
        "persisted": True,
        "session_ids": ids,
        "sessions": [payload["sessions"][i] | {"session_id": ids[i]} for i in range(len(ids))],
    }
