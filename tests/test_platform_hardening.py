from planner.health import planner_health
from planner.observability import event, complete
from planner.plan_policy import PlannerPolicy


def test_default_policy_is_valid():
    PlannerPolicy().validate()


def test_invalid_policy_is_rejected():
    try:
        PlannerPolicy(quantum_minutes=0).validate()
    except ValueError:
        pass
    else:
        raise AssertionError("invalid policy should fail validation")


def test_health_reports_ready_for_valid_configuration():
    report = planner_health(
        capacity_minutes=180,
        quantum_minutes=15,
        max_session_minutes=90,
    )
    assert report.ready
    assert all(report.checks.values())


def test_health_reports_not_ready_for_invalid_configuration():
    report = planner_health(
        capacity_minutes=100,
        quantum_minutes=15,
        max_session_minutes=120,
    )
    assert not report.ready


def test_structured_event_is_serializable():
    evt = event("plan.generated", revision=4, topic_count=12)
    finished = complete(evt, 12.3456)
    assert finished.duration_ms == 12.346
    assert '"name":"plan.generated"' in finished.to_json()
