from datetime import date

from fastapi.testclient import TestClient

from planner.models import StudySession, Subject, Topic
from planner.v2_app import adaptive_db, app, db
from planner.storage import CURRENT_USER


def test_workload_calibration_rebuilds_from_history(tmp_path):
    token = CURRENT_USER.set("calibration-idempotent-test")
    original_path = db.path
    db.path = str(tmp_path / "planner.db")
    try:
        db.initialize()
        db.upsert_subject(Subject("s", "Subject"))
        db.upsert_topic(Topic("t", "s", "Topic", estimated_hours=1))
        db.save_sessions([
            StudySession(date(2026, 8, 24), "t", 60, actual_minutes=75),
            StudySession(date(2026, 8, 25), "t", 60, actual_minutes=90),
        ])
        # Mark the sessions completed using the existing persistence method.
        snap = db.snapshot()
        for row in snap["sessions"]:
            db.complete_session(int(row["id"]), int(row["actual_minutes"]), 0.8)
        adaptive_db._ensure_schema()
        client = TestClient(app)
        first = client.post("/v2/workload/t/calibrate").json()
        second = client.post("/v2/workload/t/calibrate").json()
        assert first["sample_count"] == second["sample_count"] == 2
        assert first["predicted_minutes"] == second["predicted_minutes"]
        assert first["confidence"] == second["confidence"]
    finally:
        db.path = original_path
        CURRENT_USER.reset(token)
