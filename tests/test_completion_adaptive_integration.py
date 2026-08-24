from datetime import date

from fastapi.testclient import TestClient

from planner.models import StudySession, Subject, Topic
from planner.storage import CURRENT_USER
from planner.v2_app import adaptive_db, app, db


def test_normal_session_completion_updates_adaptive_state_once(tmp_path):
    token = CURRENT_USER.set("completion-adaptive-integration")
    original_path = db.path
    db.path = str(tmp_path / "planner.db")
    try:
        db.initialize()
        db.upsert_subject(Subject("s", "Subject"))
        db.upsert_topic(Topic("t", "s", "Topic", estimated_hours=1, mastery=0.2))
        session_id = db.save_sessions([StudySession(date(2026, 8, 24), "t", 45)])[0]
        adaptive_db._ensure_schema()
        client = TestClient(app)

        response = client.post(
            f"/sessions/{session_id}/complete",
            json={"actual_minutes": 60, "performance_score": 0.85, "completed_on": "2026-08-24"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "completed"
        assert payload["fsrs"]["card_json"]
        assert payload["workload"]["sample_count"] == 1

        state = client.get("/v2/topic/t/state").json()
        assert state["fsrs"]["card_json"] == payload["fsrs"]["card_json"]
        assert state["workload"]["sample_count"] == 1

        # Re-sending completion must not create another observation because the
        # session is already completed.
        second = client.post(
            f"/sessions/{session_id}/complete",
            json={"actual_minutes": 60, "performance_score": 0.85, "completed_on": "2026-08-24"},
        )
        assert second.status_code == 409
        state_after = client.get("/v2/topic/t/state").json()
        assert state_after["workload"]["sample_count"] == 1
    finally:
        db.path = original_path
        CURRENT_USER.reset(token)
