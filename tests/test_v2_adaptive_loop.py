from datetime import datetime, timezone

from fastapi.testclient import TestClient

from planner.v2_app import app, adaptive_db, db
from planner.models import Subject, Topic
from planner.state import CurriculumNode, KnowledgeComponent


def test_adaptive_session_observation_updates_workload_and_fsrs(tmp_path):
    from planner.storage import CURRENT_USER
    token = CURRENT_USER.set("adaptive-loop-test")
    original_path = db.path
    db.path = str(tmp_path / "planner.db")
    try:
        db.initialize()
        db.upsert_subject(Subject("s", "Subject"))
        db.upsert_topic(Topic("t", "s", "Topic"))
        adaptive_db._ensure_schema()
        adaptive_db.save_curriculum_nodes([CurriculumNode("root", "Course", "course")])
        adaptive_db.save_knowledge_components([KnowledgeComponent("kc", "t", "Skill")])
        adaptive_db.link_topic_to_nodes("t", ["root"])
        client = TestClient(app)
        response = client.post(
            "/v2/topic/t/session-observation",
            json={"actual_minutes": 75, "performance_score": 0.82, "observed_at": datetime(2026,8,24,tzinfo=timezone.utc).isoformat()},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["workload"]["sample_count"] == 1
        assert payload["fsrs"]["card_json"]
        assert payload["knowledge"][0]["observations"] == 1
        state = client.get("/v2/topic/t/state").json()
        assert state["curriculum_nodes"][0]["id"] == "root"
    finally:
        db.path = original_path
        CURRENT_USER.reset(token)
