from __future__ import annotations

import pytest

from planner.storage import CURRENT_USER, StudyDB
from planner.workspace_revision import WorkspaceConflict, WorkspaceRevisionStore


def _store(tmp_path, user: str):
    db = StudyDB(tmp_path / "planner.db")
    token = CURRENT_USER.set(user)
    return db, WorkspaceRevisionStore(db), token


def test_revision_is_isolated_by_workspace(tmp_path):
    db = StudyDB(tmp_path / "planner.db")
    store = WorkspaceRevisionStore(db)
    first = CURRENT_USER.set("alice")
    try:
        assert store.current().revision == 0
        assert store.claim().revision == 1
    finally:
        CURRENT_USER.reset(first)

    second = CURRENT_USER.set("bob")
    try:
        assert store.current().revision == 0
        assert store.claim().revision == 1
    finally:
        CURRENT_USER.reset(second)


def test_stale_revision_is_rejected_atomically(tmp_path):
    db = StudyDB(tmp_path / "planner.db")
    store = WorkspaceRevisionStore(db)
    token = CURRENT_USER.set("student")
    try:
        assert store.claim().revision == 1
        with pytest.raises(WorkspaceConflict):
            store.claim(expected_revision=0)
        assert store.current().revision == 1
        assert store.claim(expected_revision=1).revision == 2
    finally:
        CURRENT_USER.reset(token)
