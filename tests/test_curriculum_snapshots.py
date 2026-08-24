from pathlib import Path

from planner.curriculum_ingest import CurriculumRecord, ingest_records
from planner.adaptive_db import AdaptiveDB
from planner.storage import StudyDB


def test_curriculum_snapshot_round_trip(tmp_path: Path):
    db = AdaptiveDB(StudyDB(tmp_path / "study.db"))
    snapshot = ingest_records(
        "usmle",
        "2026-v1",
        [
            CurriculumRecord("usmle", "cv", "Cardiovascular", "system"),
            CurriculumRecord("usmle", "ecg", "ECG", "topic", "cv"),
        ],
    )
    db.save_curriculum_snapshot(snapshot)
    rows = db.list_curriculum_snapshots("usmle")
    assert len(rows) == 1
    assert rows[0]["version"] == "2026-v1"
    assert rows[0]["fingerprint"] == snapshot.fingerprint
    assert rows[0]["node_count"] == 2
