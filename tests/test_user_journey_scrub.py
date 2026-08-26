from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from planner.models import Subject, Topic
from planner.storage import CURRENT_USER
from planner.v2_app import adaptive_db, app, db
from planner.workspace_sync import is_mutating_planner_path


def test_real_user_setup_build_replan_complete_journey(tmp_path):
    token = CURRENT_USER.set("human-journey")
    original_path = db.path
    db.path = str(tmp_path / "planner.db")
    try:
        db.initialize()
        adaptive_db._ensure_schema()
        client = TestClient(app)

        # Empty workspace is still reachable.
        assert client.get("/snapshot").status_code == 200

        # The personal-builder's API path is usable before any curriculum exists.
        client.post("/profile", json={
            "daily_available_minutes": 120,
            "minimum_subject_minutes_week": 30,
            "review_fraction": 0.25,
            "max_session_minutes": 60,
            "rest_weekdays": [],
            "energy_pattern": ["high", "medium", "medium", "low"],
        })
        client.post("/subjects", json={"id": "cardio", "name": "Cardiology", "exam_weight": 1, "category": "Personal"})
        client.post("/topics", json={
            "id": "hf", "subject_id": "cardio", "name": "Heart failure",
            "complexity": 0.5, "estimated_hours": 1, "mastery": 0,
            "self_difficulty": 3, "volume": 0.5, "cognitive_load": 0.6,
        })

        # Canonical planner must persist executable sessions.
        plan = client.post("/v2/plan/persist", json={"start_date": date(2026, 8, 26).isoformat(), "days": 7}).json()
        assert plan["persisted"] is True
        assert plan["session_ids"]
        assert client.get("/snapshot").json()["sessions"]

        session_id = plan["session_ids"][0]
        completed = client.post(
            f"/sessions/{session_id}/complete",
            json={"actual_minutes": 50, "performance_score": 0.85, "completed_on": "2026-08-26"},
        )
        assert completed.status_code == 200
        state = client.get("/v2/topic/hf/state").json()
        assert state["fsrs"] is not None
        assert state["workload"]["sample_count"] == 1

        rebuilt = client.post("/v2/plan/persist", json={"start_date": date(2026, 8, 26).isoformat(), "days": 7})
        assert rebuilt.status_code == 200
        assert rebuilt.json()["persisted"] is True

    finally:
        db.path = original_path
        CURRENT_USER.reset(token)


def test_v2_mutations_participate_in_workspace_revision_policy():
    assert is_mutating_planner_path("POST", "/v2/plan/persist")
    assert is_mutating_planner_path("POST", "/v2/topic/hf/question")
    assert is_mutating_planner_path("POST", "/v2/topic/hf/review")
    assert not is_mutating_planner_path("POST", "/v2/reconcile/sessions")
