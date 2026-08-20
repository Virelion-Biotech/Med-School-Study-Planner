from __future__ import annotations

import os
from dataclasses import asdict
from datetime import date

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .adaptation import update_topic_from_session
from .models import Exam, PriorityWeights, Subject, Topic, UserProfile
from .optimizer import optimize_week
from .storage import StudyDB
from .weekly import generate_balanced_week

app = FastAPI(title="Med School Study Planner", version="0.2.0")
db = StudyDB(os.getenv("STUDY_PLANNER_DB", "study_planner.db"))

class PlanRequest(BaseModel):
    subjects: list[Subject]
    topics: list[Topic]
    exams: list[Exam] = Field(default_factory=list)
    profile: UserProfile = UserProfile()
    start_date: date
    days: int = Field(default=7, ge=1, le=31)
    weights: PriorityWeights = PriorityWeights()
    optimizer: bool = False
    persist: bool = False

class CompleteRequest(BaseModel):
    actual_minutes: int = Field(ge=0)
    performance_score: float = Field(ge=0, le=1)
    completed_on: date | None = None

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "engine": "tiered-rule-based-cpsat"}

@app.post("/plan")
def plan(request: PlanRequest):
    result = (optimize_week if request.optimizer else generate_balanced_week)(
        request.subjects, request.topics, request.exams, request.profile,
        request.start_date, request.days, request.weights,
    )
    if request.persist:
        db.save_profile(request.profile)
        db.save_curriculum(request.subjects, request.topics, request.exams)
        db.save_sessions(result.sessions)
    return {
        "sessions": [asdict(s) | {"session_type": s.session_type.value} for s in result.sessions],
        "subject_minutes": result.subject_minutes,
        "unfulfilled_floor": result.unfulfilled_floor,
        "optimizer": request.optimizer,
        "persisted": request.persist,
    }

@app.post("/sessions/{session_id}/complete")
def complete(session_id: int, request: CompleteRequest):
    topic = db.get_topic_for_session(session_id)
    if topic is None:
        raise HTTPException(status_code=404, detail="Session or topic not found")
    completed_on = request.completed_on or date.today()
    updated = update_topic_from_session(topic, request.actual_minutes, request.performance_score, completed_on)
    try:
        db.complete_session(session_id, request.actual_minutes, request.performance_score)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    db.update_topic(updated)
    return {"topic": asdict(updated)}

@app.get("/snapshot")
def snapshot():
    return db.snapshot()
