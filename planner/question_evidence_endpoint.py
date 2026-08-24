from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone

from fastapi import HTTPException

from .adaptive_db import AdaptiveDB
from .api import app, db
from .evidence import summarize_question_evidence

adaptive_db = AdaptiveDB(db)


@app.get("/v2/topic/{topic_id}/evidence")
def topic_evidence(topic_id: str):
    if db.get_topic(topic_id) is None:
        raise HTTPException(status_code=404, detail="Topic not found")
    return asdict(summarize_question_evidence(adaptive_db, topic_id, datetime.now(timezone.utc)))
