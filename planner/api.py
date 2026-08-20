from __future__ import annotations

import os
from dataclasses import asdict
from datetime import date, timedelta
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .adaptation import update_topic_from_session
from .models import Exam, PriorityWeights, Subject, Topic, UserProfile
from .optimizer import optimize_week
from .storage import StudyDB
from .weekly import generate_balanced_week

app = FastAPI(title="Med School Study Planner", version="0.4.0")
db = StudyDB(os.getenv("STUDY_PLANNER_DB", "study_planner.db"))
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

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

class RescheduleRequest(BaseModel):
    new_date: date

class ReplanRequest(BaseModel):
    start_date: date
    days: int = Field(default=7, ge=1, le=31)
    weights: PriorityWeights = PriorityWeights()
    optimizer: bool = True
    locked_session_ids: list[int] = Field(default_factory=list)

@app.get("/", include_in_schema=False)
def root():
    return FileResponse(STATIC_DIR / "index.html")

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "engine": "tiered-rule-based-cpsat", "ui": "available"}


def _serialize_plan(result):
    return [asdict(s) | {"session_type": s.session_type.value} for s in result.sessions]

@app.post("/plan")
def plan(request: PlanRequest):
    result = (optimize_week if request.optimizer else generate_balanced_week)(
        request.subjects, request.topics, request.exams, request.profile,
        request.start_date, request.days, request.weights,
    )
    session_ids: list[int] = []
    if request.persist:
        db.save_profile(request.profile)
        db.save_curriculum(request.subjects, request.topics, request.exams)
        session_ids = db.save_sessions(result.sessions)
    sessions = []
    for index, session in enumerate(result.sessions):
        payload = asdict(session) | {"session_type": session.session_type.value}
        if request.persist:
            payload["session_id"] = session_ids[index]
        sessions.append(payload)
    return {"sessions": sessions, "subject_minutes": result.subject_minutes,
            "unfulfilled_floor": result.unfulfilled_floor, "optimizer": request.optimizer,
            "persisted": request.persist}

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

@app.post("/sessions/{session_id}/reschedule")
def reschedule(session_id: int, request: RescheduleRequest):
    profile = db.get_profile()
    if request.new_date.weekday() in profile.rest_weekdays:
        raise HTTPException(status_code=409, detail="That day is configured as a rest day")
    try:
        db.reschedule_session(session_id, request.new_date)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"status": "rescheduled", "session_id": session_id, "date": request.new_date}

@app.post("/replan")
def replan(request: ReplanRequest):
    subjects, topics, exams = db.load_curriculum()
    profile = db.get_profile()
    if not subjects or not topics:
        raise HTTPException(status_code=409, detail="No saved curriculum to replan")
    result = (optimize_week if request.optimizer else generate_balanced_week)(
        subjects, topics, exams, profile, request.start_date, request.days, request.weights,
    )
    end = request.start_date + timedelta(days=request.days)
    # Preserve sessions explicitly moved by the user; rebuild the remaining uncompleted schedule.
    db.delete_uncompleted_sessions_in_range(request.start_date, end, set(request.locked_session_ids))
    db.save_sessions(result.sessions)
    return {"sessions": _serialize_plan(result), "subject_minutes": result.subject_minutes,
            "unfulfilled_floor": result.unfulfilled_floor, "optimizer": request.optimizer,
            "locked_session_ids": request.locked_session_ids}

@app.get("/snapshot")
def snapshot():
    return db.snapshot()
