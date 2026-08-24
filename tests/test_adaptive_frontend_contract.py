from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "planner" / "static"


def test_browser_completion_does_not_duplicate_adaptive_observation():
    source = (STATIC / "adaptive-v3.js").read_text(encoding="utf-8")
    assert "/v2/topic/${encodeURIComponent(topicId)}/session-observation" not in source
    assert "originalCompleteSession.call(this, false)" in source


def test_adaptive_completion_backend_is_imported_by_legacy_api():
    source = (ROOT / "planner" / "api.py").read_text(encoding="utf-8")
    assert "from .session_learning import AdaptiveSessionLearner" in source
    assert "adaptive_session_learner = AdaptiveSessionLearner(db)" in source
    assert "adaptive_session_learner.observe" in source
