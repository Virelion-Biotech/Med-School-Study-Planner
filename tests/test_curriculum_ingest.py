from planner.curriculum_ingest import CurriculumRecord, ingest_records, stable_node_id, validate_snapshot


def test_stable_node_id_is_deterministic():
    a = stable_node_id("usmle", "cv-001", "Cardiovascular")
    b = stable_node_id("usmle", "cv-001", "Cardiovascular")
    assert a == b


def test_duplicate_records_are_reported_and_merged():
    snapshot = ingest_records(
        "school",
        "2026-fall",
        [
            CurriculumRecord("school", "a", "Cardiovascular", "block"),
            CurriculumRecord("school", "b", "Cardiovascular", "block"),
        ],
    )
    assert len(snapshot.nodes) == 1
    assert any(issue.code == "duplicate" for issue in snapshot.issues)


def test_unknown_parent_is_rejected():
    snapshot = ingest_records(
        "school",
        "2026-fall",
        [CurriculumRecord("school", "child", "topic", "missing")],
    )
    assert any(issue.code == "unknown_parent" for issue in snapshot.issues)


def test_snapshot_fingerprint_changes_with_content():
    a = ingest_records("personal", "1", [CurriculumRecord("personal", "x", "Heart", "topic")])
    b = ingest_records("personal", "1", [CurriculumRecord("personal", "x", "Heart Failure", "topic")])
    assert a.fingerprint != b.fingerprint


def test_validation_detects_cycles():
    snapshot = ingest_records(
        "school",
        "cycle",
        [
            CurriculumRecord("school", "a", "A", "block"),
            CurriculumRecord("school", "b", "B", "topic", "a"),
        ],
    )
    # Synthetic mutation is intentional: this validates the validator independently
    # of ingestion's ordered-parent rule.
    nodes = list(snapshot.nodes)
    nodes[0] = type(nodes[0])(nodes[0].id, nodes[0].name, nodes[0].node_type, nodes[1].id, nodes[0].source)
    cyclic = type(snapshot)(snapshot.source, snapshot.version, tuple(nodes), snapshot.issues, snapshot.fingerprint)
    issues = validate_snapshot(cyclic)
    assert any(issue.code == "cycle" for issue in issues)
