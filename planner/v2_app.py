from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime, timezone

from fastapi import HTTPException
from pydantic import BaseModel, Field

from .adaptive_cpsat import optimize_adaptive_week
from .adaptive_db import AdaptiveDB
from .api import app, db
from .fsrs import FSRSAdapter
from .irt import evidence_sufficient
from .models import PriorityWeights
from .questions import QuestionOutcome, record_question
from .readiness import readiness_from_signals
from .state import ActivityType
from .utility import UtilityWeights, action_utility
from .workload import WorkloadEstimate, initial_workload, update_workload

adaptive_db = AdaptiveDB(db)
fsrs = FSRSAdapter(enable_fuzzing=False)


class AdaptivePlanRequest(BaseModel):
    start_date: date
    days: int = Field(default=7, ge=1, le=31)
    current_block: str | None = Field(default=None, max_length=100)
    weights: UtilityWeights = UtilityWeights()
    blocked_minutes_by_day: dict[str, int] = Field(default_factory=dict)
    preallocated_subject_minutes: dict[str, int] = Field(default_factory=dict)
    preallocated_topic_minutes: dict[str, int] = Field(default_factory=dict)


class ReviewRequest(BaseModel):
    rating: int = Field(ge=1, le=4)
    reviewed_at: datetime | None = None


class QuestionRequest(BaseModel):
    question_id: str = Field(min_length=1, max_length=200)
    correct: bool
    response_time_seconds: float | None = Field(default=None, ge=0)
    confidence: float | None = Field(default=None, ge=0, le=1)
    knowledge_component_id: str | None = Field(default=None, max_length=200)
    attempted_at: datetime | None = None


@app.get("/v2/status")
def adaptive_status():
    return {
        "version": "2",
        "engine": "FSRS + BKT + workload + utility/min + CP-SAT",
        "legacy_routes_preserved": True,
        "irt_enabled": False,
    }


@app.get("/v2/topic/{topic_id}/state")
def adaptive_topic_state(topic_id: str):
    topic = db.get_topic(topic_id)
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")
    fsrs_state = adaptive_db.get_fsrs_state(topic_id)
    workload_row = adaptive_db.get_workload(topic_id)
    components = adaptive_db.load_knowledge_components(topic_id)
    knowledge = [adaptive_db.get_knowledge_state(k.id, k.initial_mastery) for k in components]
    return {
        "topic": asdict(topic),
        "fsrs": asdict(fsrs_state) if fsrs_state else None,
        "workload": workload_row,
        "knowledge_components": [asdict(k) for k in components],
        "knowledge": [asdict(k) for k in knowledge],
    }


@app.post("/v2/topic/{topic_id}/review")
def adaptive_review(topic_id: str, request: ReviewRequest):
    topic = db.get_topic(topic_id)
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")
    current = adaptive_db.get_fsrs_state(topic_id) or fsrs.new_state(topic_id)
    reviewed_at = request.reviewed_at or datetime.now(timezone.utc)
    updated = fsrs.review(current, request.rating, reviewed_at)
    updated.retrievability = fsrs.retrievability(updated, reviewed_at)
    adaptive_db.save_fsrs_state(updated)
    topic.memory_retrievability = updated.retrievability
    topic.next_review_due = updated.due.date() if updated.due else topic.next_review_due
    db.update_topic(topic)
    adaptive_db.record_event("fsrs_review", {"rating": request.rating, "due": str(updated.due)}, topic_id)
    return {"topic": asdict(topic), "fsrs": asdict(updated)}


@app.post("/v2/topic/{topic_id}/question")
def adaptive_question(topic_id: str, request: QuestionRequest):
    topic = db.get_topic(topic_id)
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")
    attempted_at = request.attempted_at or datetime.now(timezone.utc)
    result = record_question(
        adaptive_db,
        QuestionOutcome(
            request.question_id,
            topic_id,
            request.correct,
            request.response_time_seconds,
            request.confidence,
            request.knowledge_component_id,
        ),
        topic,
        attempted_at,
    )
    if request.knowledge_component_id:
        topic.mastery = float(result["mastery_probability"])
        topic.mastery_uncertainty = float(result["uncertainty"])
        db.update_topic(topic)
    return result | {"topic": asdict(topic)}


@app.get("/v2/topic/{topic_id}/why")
def adaptive_why(topic_id: str):
    subjects, topics, exams = db.load_curriculum()
    topic = next((t for t in topics if t.id == topic_id), None)
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")
    subject = next((s for s in subjects if s.id == topic.subject_id), None)
    if subject is None:
        raise HTTPException(status_code=404, detail="Subject not found")
    exam = next((e for e in exams if topic_id in e.topic_ids or topic.subject_id in e.subject_ids), None)
    workload = adaptive_db.get_workload(topic_id)
    minutes = workload["predicted_minutes"] if workload else topic.estimated_hours * 60.0
    breakdown = action_utility(topic, subject, date.today(), exam, minutes, current_block=None, topic_block=topic.block_id, weights=UtilityWeights())
    return asdict(breakdown)


@app.post("/v2/plan")
def adaptive_plan(request: AdaptivePlanRequest):
    subjects, topics, exams = db.load_curriculum()
    if not subjects or not topics:
        raise HTTPException(status_code=409, detail="No saved curriculum to plan")
    workloads: dict[str, float] = {}
    for topic in topics:
        row = adaptive_db.get_workload(topic.id)
        workloads[topic.id] = float(row["predicted_minutes"]) if row else initial_workload(topic).predicted_minutes
    plan = optimize_adaptive_week(
        subjects,
        topics,
        exams,
        db.get_profile(),
        request.start_date,
        request.days,
        workloads,
        request.blocked_minutes_by_day,
        request.preallocated_subject_minutes,
        request.preallocated_topic_minutes,
        request.current_block,
        request.weights,
    )
    return {
        "status": plan.status,
        "sessions": [asdict(s) | {"session_type": s.session_type.value} for s in plan.sessions],
        "subject_minutes": plan.subject_minutes,
        "unfulfilled_subject_floor": plan.unfulfilled_subject_floor,
        "unfulfilled_exam_coverage": plan.unfulfilled_exam_coverage,
        "explanations": plan.explanations,
    }


@app.post("/v2/workload/{topic_id}/calibrate")
def calibrate_workload(topic_id: str):
    topic = db.get_topic(topic_id)
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")
    history = [x["actual_minutes"] for x in db.snapshot()["sessions"] if x["topic_id"] == topic_id and x["completed"] and x["actual_minutes"]]
    current_row = adaptive_db.get_workload(topic_id)
    estimate = WorkloadEstimate(**current_row) if current_row else initial_workload(topic)
    updated = update_workload(estimate, [int(x) for x in history])
    adaptive_db.save_workload(updated)
    topic.workload_confidence = updated.confidence
    db.update_topic(topic)
    return asdict(updated)


@app.get("/v2/readiness")
def adaptive_readiness():
    snap = db.snapshot()
    topics = snap["topics"]
    knowledge = sum(float(t.get("mastery", 0)) for t in topics) / len(topics) if topics else 0.0
    sessions = snap["sessions"]
    completed = [s for s in sessions if s["completed"]]
    practice = sum(float(s.get("performance_score") or 0) for s in completed) / len(completed) if completed else 0.5
    coverage = len({s["topic_id"] for s in completed}) / len(topics) if topics else 0.0
    due = sum(1 for t in topics if t.get("next_review_due") and t["next_review_due"] <= date.today().isoformat())
    retention = max(0.0, 1.0 - due / max(1, len(topics)))
    future_exams = [e for e in snap["exams"] if e["exam_date"] >= date.today().isoformat()]
    deadline = 1.0 if not future_exams else max(0.0, 1.0 - min(1.0, min((date.fromisoformat(e["exam_date"]) - date.today()).days for e in future_exams) / 60.0))
    r = readiness_from_signals(knowledge, retention, coverage, practice, deadline)
    attempts = adaptive_db.question_history()
    sufficient_irt = evidence_sufficient(len(attempts), len({x["question_id"] for x in attempts}))
    return {"score": r.score, "label": r.label, "components": asdict(r), "irt_evidence_sufficient": sufficient_irt}
