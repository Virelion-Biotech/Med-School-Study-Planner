import pytest

from planner.platform_contract import (
    PlannerLifecycle,
    SyncAction,
    decide_sync,
)


def test_matching_revision_is_safe_to_apply():
    decision = decide_sync(7, 7)
    assert decision.action is SyncAction.APPLY
    assert not decision.stale


def test_stale_revision_requires_reconciliation():
    decision = decide_sync(7, 9)
    assert decision.action is SyncAction.RECONCILE
    assert decision.stale
    assert decision.reason == "revision_stale"


def test_missing_revision_requires_refresh():
    decision = decide_sync(None, 3)
    assert decision.action is SyncAction.REFRESH


def test_invalid_revision_is_rejected():
    with pytest.raises(ValueError):
        decide_sync(-1, 2)
    with pytest.raises(ValueError):
        decide_sync(1, -1)


def test_lifecycle_accepts_monotonic_progression():
    lifecycle = PlannerLifecycle()
    assert lifecycle.validate(["curriculum", "student_state", "plan", "session", "evidence"]) == (
        "curriculum",
        "student_state",
        "plan",
        "session",
        "evidence",
    )


def test_lifecycle_rejects_backtracking_and_unknown_stages():
    lifecycle = PlannerLifecycle()
    with pytest.raises(ValueError):
        lifecycle.validate(["plan", "curriculum"])
    with pytest.raises(ValueError):
        lifecycle.validate(["curriculum", "not-a-stage"])
