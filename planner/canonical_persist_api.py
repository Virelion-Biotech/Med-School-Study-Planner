from __future__ import annotations

from datetime import date, timedelta

from .v2_app import app, adaptive_plan, AdaptivePlanRequest
from .api import db
from .models import ActivityType, SessionType, StudySession


@app.post("/v2/plan/persist")
def persist_canonical_plan(request: AdaptivePlanRequest):
    """Generate the canonical KC-aware plan and persist it on the production V2 app."""
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
