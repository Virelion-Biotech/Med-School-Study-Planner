from planner.reconciliation import SessionRevision, reconcile_sessions


def test_disjoint_edit_auto_merges():
    base = [SessionRevision(1, ("a",)), SessionRevision(2, ("b",))]
    server = [SessionRevision(1, ("a-server",)), SessionRevision(2, ("b",))]
    client = [SessionRevision(1, ("a",)), SessionRevision(2, ("b-client",))]
    result = reconcile_sessions(base, server, client)
    assert result.status == "merged"
    assert [r.state for r in result.merged] == [("a-server",), ("b-client",)]


def test_same_session_divergent_edit_conflicts():
    base = [SessionRevision(1, ("a",))]
    server = [SessionRevision(1, ("server",))]
    client = [SessionRevision(1, ("client",))]
    result = reconcile_sessions(base, server, client)
    assert result.status == "conflict"
    assert result.conflicts == (1,)


def test_identical_concurrent_edit_is_idempotent():
    base = [SessionRevision(1, ("a",))]
    changed = [SessionRevision(1, ("same",))]
    result = reconcile_sessions(base, changed, changed)
    assert result.status == "merged"
    assert result.merged == tuple(changed)


def test_client_and_server_additions_merge():
    result = reconcile_sessions(
        [],
        [SessionRevision(1, ("server",))],
        [SessionRevision(2, ("client",))],
    )
    assert result.status == "merged"
    assert result.additions_from_client == (2,)
    assert result.additions_from_server == (1,)
    assert {r.session_id for r in result.merged} == {1, 2}


def test_delete_vs_edit_is_conflict():
    base = [SessionRevision(1, ("a",))]
    server = []
    client = [SessionRevision(1, ("edited",))]
    result = reconcile_sessions(base, server, client)
    assert result.status == "conflict"
    assert result.conflicts == (1,)
