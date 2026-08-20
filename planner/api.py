from __future__ import annotations

import csv
import io
import os
from dataclasses import asdict
from datetime import date, timedelta
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .adaptation import recalibrated_complexity, update_topic_from_session
from .analytics import summarize, topic_time_history
from .export import sessions_csv, snapshot_json
from .memory import next_memory_state
from .models import Exam, PriorityWeights, Subject, Topic, UserProfile
from .optimizer import optimize_week
from .storage import StudyDB
from .weekly import generate_balanced_week

app = FastAPI(title="Med School Study Planner", version="0.6.0")
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
    optimizer: bool = True
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

class SubjectRequest(BaseModel):
    id: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")
    name: str = Field(min_length=1, max_length=200)
    exam_weight: float = Field(default=1.0, ge=0)
    category: str = Field(default="general", max_length=100)

class TopicRequest(BaseModel):
    id: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")
    subject_id: str
    name: str = Field(min_length=1, max_length=200)
    complexity: float = Field(default=0.5, ge=0, le=1)
    estimated_hours: float = Field(default=1.0, gt=0, le=100)
    mastery: float = Field(default=0, ge=0, le=1)
    self_difficulty: float = Field(default=3, ge=1, le=5)
    volume: float = Field(default=0.5, ge=0, le=1)
    cognitive_load: float = Field(default=0.5, ge=0, le=1)
    last_studied: date | None = None
    next_review_due: date | None = None

class ExamRequest(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    date: date
    subject_ids: list[str] = Field(default_factory=list)
    topic_ids: list[str] = Field(default_factory=list)
    weight: float = Field(default=1.0, ge=0)

class ProfileRequest(BaseModel):
    daily_available_minutes: int = Field(default=240, ge=30, le=1440)
    minimum_subject_minutes_week: int = Field(default=60, ge=0, le=10080)
    review_fraction: float = Field(default=0.25, ge=0, le=1)
    max_session_minutes: int = Field(default=60, ge=15, le=240)
    rest_weekdays: list[int] = Field(default_factory=list)
    energy_pattern: list[str] = Field(default_factory=lambda: ["high", "medium", "medium", "low"])

@app.get("/", include_in_schema=False)
def root():
    return FileResponse(STATIC_DIR / "index.html")

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "engine": "adaptive-tiered-optimizer", "ui": "available", "version": "0.6.0"}

@app.get("/profile")
def get_profile():
    return asdict(db.get_profile())

@app.put("/profile")
def update_profile(request: ProfileRequest):
    if any(day < 0 or day > 6 for day in request.rest_weekdays):
        raise HTTPException(status_code=422, detail="rest_weekdays values must be 0..6")
    profile = UserProfile(request.daily_available_minutes, request.minimum_subject_minutes_week,
                          request.review_fraction, request.max_session_minutes,
                          tuple(sorted(set(request.rest_weekdays))), tuple(request.energy_pattern))
    db.save_profile(profile)
    return asdict(profile)

@app.post("/subjects")
def create_subject(request: SubjectRequest):
    db.upsert_subject(Subject(request.id, request.name, request.exam_weight, request.category))
    return {"status": "saved", "subject": request.model_dump()}

@app.delete("/subjects/{subject_id}")
def remove_subject(subject_id: str):
    try:
        db.delete_subject(subject_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Subject not found") from exc
    return {"status": "deleted", "id": subject_id}

@app.post("/topics")
def create_topic(request: TopicRequest):
    topic = Topic(request.id, request.subject_id, request.name, request.complexity, request.estimated_hours,
                  request.mastery, request.last_studied, request.next_review_due,
                  request.self_difficulty, request.volume, request.cognitive_load)
    try:
        db.upsert_topic(topic)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "saved", "topic": asdict(topic)}

@app.delete("/topics/{topic_id}")
def remove_topic(topic_id: str):
    try:
        db.delete_topic(topic_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Topic not found") from exc
    return {"status": "deleted", "id": topic_id}

@app.post("/exams")
def create_exam(request: ExamRequest):
    exam = Exam(request.id, request.date, tuple(dict.fromkeys(request.subject_ids)), tuple(dict.fromkeys(request.topic_ids)), request.weight)
    try:
        db.upsert_exam(exam)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "saved", "exam": asdict(exam)}

@app.delete("/exams/{exam_id}")
def remove_exam(exam_id: str):
    try:
        db.delete_exam(exam_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Exam not found") from exc
    return {"status": "deleted", "id": exam_id}

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
    memory = db.get_memory_state(topic.id)
    updated, new_memory = update_topic_from_session(topic, request.actual_minutes, request.performance_score, completed_on, memory)
    try:
        db.complete_session(session_id, request.actual_minutes, request.performance_score)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    db.update_topic(updated)
    db.save_memory_state(topic.id, new_memory)
    return {"topic": asdict(updated), "memory": asdict(new_memory)}

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
    result = (optimize_week if request.optimizer else generate_balanced_week)(subjects, topics, exams, profile, request.start_date, request.days, request.weights)
    end = request.start_date + timedelta(days=request.days)
    db.delete_uncompleted_sessions_in_range(request.start_date, end, set(request.locked_session_ids))
    ids = db.save_sessions(result.sessions)
    sessions = [asdict(s) | {"session_type": s.session_type.value, "session_id": ids[i]} for i, s in enumerate(result.sessions)]
    return {"sessions": sessions, "subject_minutes": result.subject_minutes, "unfulfilled_floor": result.unfulfilled_floor,
            "optimizer": request.optimizer, "locked_session_ids": request.locked_session_ids}

@app.get("/analytics")
def analytics():
    return asdict(summarize(db.snapshot())) | {"topic_time_history": topic_time_history(db.snapshot())}

@app.get("/memory/{topic_id}")
def memory(topic_id: str):
    return asdict(db.get_memory_state(topic_id))

@app.post("/calibrate")
def calibrate():
    snap = db.snapshot()
    histories = topic_time_history(snap)
    changed = []
    for topic in db.load_curriculum()[1]:
        history = histories.get(topic.id, [])
        if len(history) >= 2:
            recalibrated = recalibrated_complexity(topic, history)
            if abs(recalibrated - topic.complexity) >= 0.02:
                topic.complexity = recalibrated
                db.update_topic(topic)
                changed.append({"topic_id": topic.id, "complexity": recalibrated})
    return {"updated": changed, "count": len(changed)}

@app.get("/export/snapshot.json", response_class=PlainTextResponse)
def export_snapshot():
    return snapshot_json(db.snapshot())

@app.get("/export/sessions.csv", response_class=PlainTextResponse)
def export_sessions():
    return sessions_csv(db.snapshot())

@app.get("/snapshot")
def snapshot():
    return db.snapshot()
