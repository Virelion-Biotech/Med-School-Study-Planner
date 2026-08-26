from planner.decision_audit import build_audit


def test_decision_audit_is_structured_and_serializable():
    audit = build_audit(
        topic_id="hf",
        activity="QUESTIONS",
        utility_per_minute=1.25,
        reasons=["exam soon", "weak recent performance"],
        signals={"mastery_gap": 0.7, "retention_need": 0.4},
        constraints=["daily capacity"],
    )
    payload = audit.to_dict()
    assert payload["activity"] == "QUESTIONS"
    assert payload["signals"]["mastery_gap"] == 0.7
    assert "weak recent performance" in audit.to_json()
