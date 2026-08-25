from planner.workspace_revision import WorkspaceConflict, WorkspaceRevisionStore
from planner.workspace_sync import current_plan_fingerprint, is_mutating_planner_path, parse_revision


def test_mutating_path_classification():
    assert is_mutating_planner_path("POST", "/replan")
    assert is_mutating_planner_path("POST", "/sessions/42/complete")
    assert is_mutating_planner_path("PUT", "/profile")
    assert not is_mutating_planner_path("GET", "/replan")
    assert not is_mutating_planner_path("GET", "/workspace/state")


def test_revision_parser():
    assert parse_revision(None) is None
    assert parse_revision("0") == 0
    assert parse_revision(" 12 ") == 12


def test_revision_parser_rejects_invalid_values():
    for value in ("-1", "abc", "1.5"):
        try:
            parse_revision(value)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid revision was accepted")


def test_revision_store_rejects_stale_revision(tmp_path):
    from planner.storage import StudyDB

    db = StudyDB(str(tmp_path / "planner.db"))
    store = WorkspaceRevisionStore(db)
    first = store.claim(0)
    assert first.revision == 1
    try:
        store.claim(0)
    except WorkspaceConflict:
        pass
    else:
        raise AssertionError("stale revision was accepted")


def test_plan_fingerprint_is_deterministic_for_snapshot_rows():
    snapshot_a = {
        "sessions": [
            {"session_date": "2026-08-25", "topic_id": "b", "planned_minutes": 30, "completed": 0, "activity": "learn", "session_type": "new"},
            {"session_date": "2026-08-24", "topic_id": "a", "planned_minutes": 45, "completed": 0, "activity": "review", "session_type": "review"},
        ]
    }
    snapshot_b = {"sessions": list(reversed(snapshot_a["sessions"]))}
    assert current_plan_fingerprint(snapshot_a) == current_plan_fingerprint(snapshot_b)


def test_plan_fingerprint_changes_when_session_changes():
    base = {"sessions": [{"session_date": "2026-08-25", "topic_id": "a", "planned_minutes": 45, "completed": 0, "activity": "learn", "session_type": "new"}]}
    changed = {"sessions": [{"session_date": "2026-08-25", "topic_id": "a", "planned_minutes": 60, "completed": 0, "activity": "learn", "session_type": "new"}]}
    assert current_plan_fingerprint(base) != current_plan_fingerprint(changed)
