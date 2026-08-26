from __future__ import annotations

from datetime import date, timedelta

from fastapi import app

from .api import app, db
from .models import ActivityType, SessionType, StudySession


@app.post("/v2/plan/persist")
def persist_canonical_plan(request: dict):
    """Generate the canonical KC-aware plan and persist it as the active plan."""
    from .v2_app import AdaptivePlanRequest, adaptive_plan

    request_model = AdaptivePlanRequest.model_validate(request)
    payload = adaptive_plan(request_model)
    if not payload.get("sessions"):
        return payload | {"persisted": False, "session_ids": []}

    end = request_model.start_date + timedelta(days=request_model.days)
    db.delete_uncompleted_sessions_in_range(request_model.start_date, end)

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
