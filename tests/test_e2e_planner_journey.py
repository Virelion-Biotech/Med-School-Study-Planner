from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient

from planner.reconcile_api import app
from planner.storage import CURRENT_USER
from planner.v2_app import adaptive_db, db


TODAY = date(2026, 8, 26)


def _reset_database(tmp_path, user: str):
    token = CURRENT_USER.set(user)
    original_path = db.path
    db.path = str(tmp_path / "planner.db")
    db.initialize()
    adaptive_db._ensure_schema()
    return token, original_path


def test_full_student_journey_survives_restart_and_updates_adaptive_state(tmp_path):
    token, original_path = _reset_database(tmp_path, "e2e-student")
    try:
        client = TestClient(app)
        headers = {"X-Planner-User": "e2e-student"}

        health = client.get("/health", headers=headers)
        assert health.status_code == 200
        assert health.json()["status"] == "ok"

        first_workspace = client.get("/workspace/state", headers=headers)
        assert first_workspace.status_code == 200
        assert first_workspace.json()["revision"] == 0

        setup = client.post(
            "/setup/step1",
            headers=headers,
            json={"start_date": TODAY.isoformat(), "current_block": "cardio"},
        )
        assert setup.status_code == 200, setup.text
        setup_payload = setup.json()
        assert setup_payload["preset"] == "USMLE Step 1"
        assert setup_payload["subjects"] > 0
        assert setup_payload["topics"] > 0
        assert setup_payload["sessions"]

        snapshot = client.get("/snapshot", headers=headers)
        assert snapshot.status_code == 200
        snap = snapshot.json()
        assert snap["subjects"]
        assert snap["topics"]
        assert snap["sessions"]

        session_rows = [row for row in snap["sessions"] if not row["completed"]]
        assert session_rows
        first = session_rows[0]
        session_id = int(first["id"])
        topic_id = first["topic_id"]

        before = client.get(f"/v2/topic/{topic_id}/state", headers=headers)
        assert before.status_code == 200
        before_state = before.json()
        assert before_state["topic"]["id"] == topic_id
        assert before_state["fsrs"] is None

        complete = client.post(
            f"/sessions/{session_id}/complete",
            headers=headers,
            json={
                "actual_minutes": int(first["planned_minutes"]) + 10,
                "performance_score": 0.88,
                "completed_on": TODAY.isoformat(),
            },
        )
        assert complete.status_code == 200, complete.text
        completed_payload = complete.json()
        assert completed_payload["status"] == "completed"
        assert completed_payload["session_id"] == session_id
        assert completed_payload["fsrs"]["card_json"]
        assert completed_payload["workload"]["sample_count"] == 1

        duplicate = client.post(
            f"/sessions/{session_id}/complete",
            headers=headers,
            json={
                "actual_minutes": 30,
                "performance_score": 0.5,
                "completed_on": TODAY.isoformat(),
            },
        )
        assert duplicate.status_code == 409

        after = client.get(f"/v2/topic/{topic_id}/state", headers=headers)
        assert after.status_code == 200
        after_state = after.json()
        assert after_state["fsrs"]["card_json"] == completed_payload["fsrs"]["card_json"]
        assert after_state["workload"]["sample_count"] == 1
        assert after_state["topic"]["memory_retrievability"] is not None

        replan = client.post(
            "/replan",
            headers=headers,
            json={"start_date": TODAY.isoformat(), "days": 7, "optimizer": True, "locked_session_ids": []},
        )
        assert replan.status_code == 200, replan.text
        replan_payload = replan.json()
        assert "sessions" in replan_payload
        assert "subject_minutes" in replan_payload

        refreshed = client.get("/snapshot", headers=headers).json()
        remaining = [row for row in refreshed["sessions"] if not row["completed"]]
        if remaining:
            movable = next((row for row in remaining if row["id"] != session_id), remaining[0])
            new_date = TODAY + timedelta(days=3)
            move = client.post(
                f"/sessions/{int(movable['id'])}/reschedule",
                headers=headers,
                json={"new_date": new_date.isoformat()},
            )
            assert move.status_code == 200, move.text
            moved = client.get("/snapshot", headers=headers).json()
            moved_row = next(row for row in moved["sessions"] if int(row["id"]) == int(movable["id"]))
            assert moved_row["session_date"] == new_date.isoformat()

        readiness = client.get("/v2/readiness", headers=headers)
        assert readiness.status_code == 200
        assert "readiness" in readiness.json() or "score" in readiness.json()

        why = client.get(f"/v2/topic/{topic_id}/why", headers=headers)
        assert why.status_code == 200
        assert "reasons" in why.json()

        exported = client.get("/export/snapshot.json", headers=headers)
        assert exported.status_code == 200
        assert '"topics"' in exported.text

        # A fresh TestClient models a process restart while reusing the same DB.
        restarted = TestClient(app)
        persisted = restarted.get("/snapshot", headers=headers)
        assert persisted.status_code == 200
        persisted_payload = persisted.json()
        assert any(int(row["id"]) == session_id and row["completed"] for row in persisted_payload["sessions"])

        restart_state = restarted.get(f"/v2/topic/{topic_id}/state", headers=headers)
        assert restart_state.status_code == 200
        assert restart_state.json()["fsrs"] is not None
        assert restart_state.json()["workload"]["sample_count"] == 1
    finally:
        db.path = original_path
        CURRENT_USER.reset(token)


def test_workspace_revision_isolated_between_users(tmp_path):
    original_path = db.path
    db.path = str(tmp_path / "planner.db")
    try:
        client = TestClient(app)
        alice = {"X-Planner-User": "alice"}
        bob = {"X-Planner-User": "bob"}

        assert client.get("/workspace/state", headers=alice).json()["revision"] == 0
        assert client.get("/workspace/state", headers=bob).json()["revision"] == 0

        a = client.post(
            "/subjects",
            headers={**alice, "X-Planner-Revision": "0"},
            json={"id": "alice-subject", "name": "Alice Subject", "exam_weight": 1.0, "category": "test"},
        )
        assert a.status_code == 200
        assert a.headers["X-Planner-Revision"] == "1"

        # Bob remains at revision zero and can mutate independently.
        b = client.post(
            "/subjects",
            headers={**bob, "X-Planner-Revision": "0"},
            json={"id": "bob-subject", "name": "Bob Subject", "exam_weight": 1.0, "category": "test"},
        )
        assert b.status_code == 200
        assert b.headers["X-Planner-Revision"] == "1"

        # Alice's stale revision must conflict only with Alice's workspace.
        stale = client.post(
            "/subjects",
            headers={**alice, "X-Planner-Revision": "0"},
            json={"id": "alice-stale", "name": "Stale", "exam_weight": 1.0, "category": "test"},
        )
        assert stale.status_code == 409
        assert stale.json()["error"] == "workspace_conflict"

        alice_snapshot = client.get("/snapshot", headers=alice).json()
        bob_snapshot = client.get("/snapshot", headers=bob).json()
        assert any(row["id"] == "alice-subject" for row in alice_snapshot["subjects"])
        assert not any(row["id"] == "bob-subject" for row in alice_snapshot["subjects"])
        assert any(row["id"] == "bob-subject" for row in bob_snapshot["subjects"])
        assert not any(row["id"] == "alice-subject" for row in bob_snapshot["subjects"])
    finally:
        db.path = original_path


def test_reconcile_route_exposes_true_conflicts_and_auto_merges_single_side_changes(tmp_path):
    token, original_path = _reset_database(tmp_path, "reconcile-e2e")
    try:
        client = TestClient(app)
        headers = {"X-Planner-User": "reconcile-e2e"}

        merged = client.post(
            "/v2/reconcile/sessions",
            headers=headers,
            json={
                "base": [
                    {"session_id": 1, "state": ["2026-08-26", 45, "new"]},
                    {"session_id": 2, "state": ["2026-08-27", 30, "review"]},
                ],
                "server": [
                    {"session_id": 1, "state": ["2026-08-26", 60, "new"]},
                    {"session_id": 2, "state": ["2026-08-27", 30, "review"]},
                ],
                "client": [
                    {"session_id": 1, "state": ["2026-08-26", 45, "new"]},
                    {"session_id": 2, "state": ["2026-08-27", 45, "review"]},
                ],
            },
        )
        assert merged.status_code == 200
        assert merged.json()["status"] == "merged"
        assert {row["session_id"] for row in merged.json()["merged"]} == {1, 2}

        conflict = client.post(
            "/v2/reconcile/sessions",
            headers=headers,
            json={
                "base": [{"session_id": 1, "state": ["2026-08-26", 45, "new"]}],
                "server": [{"session_id": 1, "state": ["2026-08-26", 60, "new"]}],
                "client": [{"session_id": 1, "state": ["2026-08-26", 30, "new"]}],
            },
        )
        assert conflict.status_code == 200
        assert conflict.json()["status"] == "conflict"
        assert conflict.json()["conflicts"] == [1]
    finally:
        db.path = original_path
        CURRENT_USER.reset(token)
