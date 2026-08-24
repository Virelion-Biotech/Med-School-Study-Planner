from __future__ import annotations

from dataclasses import asdict
from datetime import date

from fastapi import HTTPException
from pydantic import BaseModel, Field

from .adaptive_db import AdaptiveDB
from .api import app, db
from .kc_conflicts import detect_kc_conflicts
from .kc_explanations import explain_kc
from .kc_planning import optimize_with_kc_state
from .kc_state import aggregate_topic_kc_signals

_adaptive_db = AdaptiveDB(db)


class CanonicalPlanRequest(BaseModel):
    start_date: date
    days: int = Field(default=7, ge=1, le=31)
    current_block: str | None = Field(default=None, max_length=100)


@app.get("/v2/kc/{kc_id}/explanation")
def kc_explanation(kc_id: str):
    kc = _adaptive_db.load_knowledge_components_for_id(kc_id)
    if kc is None:
        raise HTTPException(status_code=404, detail="Knowledge component not found")
    state = _adaptive_db.get_knowledge_state(kc_id, kc.initial_mastery)
    topics = db.load_curriculum()[1]
    mapped_topics = [t for t in topics if t.id == kc.topic_id]
    mappings = _adaptive_db.curriculum_mappings_for_kc(kc_id)
    summary = aggregate_topic_kc_signals(
        [state], tuple(t.id for t in mapped_topics), tuple(m.source for m in mappings)
    )
    return asdict(explain_kc(summary, mappings))


@app.get("/v2/kc/{kc_id}/conflicts")
def kc_conflicts(kc_id: str):
    components = _adaptive_db.load_knowledge_components()
    kc = next((k for k in components if k.id == kc_id), None)
    if kc is None:
        raise HTTPException(status_code=404, detail="Knowledge component not found")
    topics = [t for t in db.load_curriculum()[1] if t.id == kc.topic_id]
    conflict = detect_kc_conflicts(kc_id, topics)
    return {"conflict": asdict(conflict) if conflict else None}


@app.post("/v2/plan/canonical")
def canonical_plan(request: CanonicalPlanRequest):
    subjects, topics, exams = db.load_curriculum()
    if not subjects or not topics:
        raise HTTPException(status_code=409, detail="No saved curriculum to plan")
    plan = optimize_with_kc_state(
        _adaptive_db,
        subjects,
        topics,
        exams,
        db.get_profile(),
        request.start_date,
        request.days,
        current_block=request.current_block,
    )
    return {
        "status": plan.status,
        "sessions": [asdict(s) | {"session_type": s.session_type.value, "activity_type": s.activity.value} for s in plan.sessions],
        "subject_minutes": plan.subject_minutes,
        "unfulfilled_subject_floor": plan.unfulfilled_subject_floor,
        "unfulfilled_exam_coverage": plan.unfulfilled_exam_coverage,
        "explanations": plan.explanations,
        "planner": "canonical_kc",
    }
