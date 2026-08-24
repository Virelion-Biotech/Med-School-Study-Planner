from datetime import datetime, timezone

from fastapi.testclient import TestClient

from planner.v2_app import app, adaptive_db, db
from planner.models import Subject, Topic


def test_v2_status_and_topic_state(tmp_path):
    # Use the shared application objects but isolate the current user database path.
    from planner.storage import CURRENT_USER
    token = CURRENT_USER.set("v2-test")
    original_path = db.path
    db.path = str(tmp_path / "planner.db")
    try:
        db.initialize()
        db.upsert_subject(Subject("s", "Subject"))
        db.upsert_topic(Topic("t", "s", "Topic"))
        adaptive_db._ensure_schema()
        client = TestClient(app)
        status = client.get("/v2/status")
        assert status.status_code == 200
        assert status.json()["version"] == "2"
        state = client.get("/v2/topic/t/state")
        assert state.status_code == 200
        assert state.json()["topic"]["id"] == "t"
    finally:
        db.path = original_path
        CURRENT_USER.reset(token)


def test_v2_review_route_updates_fsrs(tmp_path):
    from planner.storage import CURRENT_USER
    token = CURRENT_USER.set("v2-review-test")
    original_path = db.path
    db.path = str(tmp_path / "planner.db")
    try:
        db.initialize()
        db.upsert_subject(Subject("s", "Subject"))
        db.upsert_topic(Topic("t", "s", "Topic"))
        adaptive_db._ensure_schema()
        client = TestClient(app)
        response = client.post("/v2/topic/t/review", json={"rating": 3, "reviewed_at": datetime(2026,8,24,tzinfo=timezone.utc).isoformat()})
        assert response.status_code == 200
        assert response.json()["fsrs"]["card_json"]
    finally:
        db.path = original_path
        CURRENT_USER.reset(token)
