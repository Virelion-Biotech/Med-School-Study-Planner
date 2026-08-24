from __future__ import annotations

from datetime import date, timedelta

from planner.adaptive_db import AdaptiveDB
from planner.api import db
from planner.kc_planning import optimize_with_kc_state
from planner.models import Subject, Topic
from planner.state import KnowledgeComponent


def _fixture(tmp_path):
    db.path = str(tmp_path / "planner.db")
    subject = Subject("s1", "Cardio")
    mapped = Topic("t1", "s1", "Heart failure", mastery=0.1, estimated_hours=1.0)
    legacy = Topic("t2", "s1", "Pericarditis", mastery=0.6, estimated_hours=1.0)
    db.upsert_subject(subject)
    db.upsert_topic(mapped)
    db.upsert_topic(legacy)
    adaptive = AdaptiveDB(db)
    adaptive.save_knowledge_components([KnowledgeComponent("kc1", "t1", "HF physiology", 0.5)])
    return adaptive, [subject], [mapped, legacy]


def test_kc_aware_projection_preserves_legacy_topics(tmp_path):
    adaptive, subjects, topics = _fixture(tmp_path)
    plan = optimize_with_kc_state(adaptive, subjects, topics, [], db.get_profile(), date.today(), days=1)
    assert plan.sessions
    assert {s.topic_id for s in plan.sessions}.issubset({"t1", "t2"})


def test_canonical_plan_uses_one_constrained_solve(tmp_path):
    adaptive, subjects, topics = _fixture(tmp_path)
    plan = optimize_with_kc_state(adaptive, subjects, topics, [], db.get_profile(), date.today(), days=2)
    by_day: dict[date, int] = {}
    for session in plan.sessions:
        by_day[session.date] = by_day.get(session.date, 0) + session.planned_minutes
    assert all(minutes <= db.get_profile().daily_available_minutes for minutes in by_day.values())


def test_mixed_curriculum_does_not_require_kc_for_unmapped_topic(tmp_path):
    adaptive, subjects, topics = _fixture(tmp_path)
    assert adaptive.load_knowledge_components("t1")
    assert adaptive.load_knowledge_components("t2") == []
    plan = optimize_with_kc_state(
        adaptive,
        subjects,
        topics,
        [],
        db.get_profile(),
        date.today() + timedelta(days=1),
        days=1,
    )
    assert all(session.topic_id in {"t1", "t2"} for session in plan.sessions)
