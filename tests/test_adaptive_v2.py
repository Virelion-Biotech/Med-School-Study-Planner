from datetime import date, datetime, timedelta, timezone

from planner.curriculum import CurriculumGraph
from planner.fsrs import FSRSAdapter
from planner.mastery import StudentKnowledgeState, update_bkt
from planner.models import Exam, Subject, Topic
from planner.utility import action_utility, smooth_exam_urgency
from planner.workload import initial_workload, update_workload
from planner.state import CurriculumNode


def test_curriculum_graph_supports_multiple_levels():
    graph = CurriculumGraph([
        CurriculumNode("root", "Cardiovascular", "block", source="school"),
        CurriculumNode("phys", "Physiology", "discipline", parent_id="root", source="school"),
        CurriculumNode("kc", "Cardiac cycle", "topic", parent_id="phys", source="school"),
    ])
    assert graph.children("root")[0].id == "phys"
    assert [node.id for node in graph.ancestors("kc")] == ["phys", "root"]


def test_bkt_updates_correct_answer_and_tracks_uncertainty():
    state = StudentKnowledgeState("kc")
    updated = update_bkt(state, True, datetime(2026, 8, 24, tzinfo=timezone.utc))
    assert updated.mastery_probability > state.mastery_probability
    assert updated.observations == 1
    assert updated.uncertainty < state.uncertainty


def test_bkt_forgetting_moves_state_toward_uncertainty_baseline():
    state = StudentKnowledgeState(
        "kc", mastery_probability=0.95, uncertainty=0.2, observations=20,
        last_observed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    later = update_bkt(state, True, datetime(2026, 8, 24, tzinfo=timezone.utc))
    assert later.mastery_probability < 0.95


def test_workload_learns_from_actual_time():
    topic = Topic("t", "s", "Topic", estimated_hours=1)
    prior = initial_workload(topic)
    learned = update_workload(prior, [90, 100, 95])
    assert learned.predicted_minutes < prior.predicted_minutes
    assert learned.sample_count == 3
    assert learned.confidence > prior.confidence


def test_utility_per_minute_is_explainable_and_exam_sensitive():
    topic = Topic("t", "s", "Cardiology", mastery=0.2, memory_retrievability=0.4)
    subject = Subject("s", "Cardiology", exam_weight=0.9)
    exam = Exam("e", date(2026, 8, 30), subject_ids=("s",), weight=1.0)
    score = action_utility(topic, subject, date(2026, 8, 24), exam, 60)
    assert score.per_minute > 0
    assert score.exam_urgency > 0.5
    assert score.mastery_gap == 0.8
    assert score.retention_gap == 0.6
    assert score.reasons


def test_fsrs_round_trip_and_ratings():
    adapter = FSRSAdapter(enable_fuzzing=False)
    state = adapter.new_state("t")
    updated = adapter.review(state, 3, datetime(2026, 8, 24, tzinfo=timezone.utc))
    assert updated.card_json
    assert updated.stability is not None
    assert updated.due is not None
    assert 0 <= adapter.retrievability(updated, datetime(2026, 8, 24, tzinfo=timezone.utc)) <= 1


def test_urgency_is_smooth_not_discontinuous():
    start = date(2026, 8, 24)
    values = [smooth_exam_urgency(start, start + timedelta(days=offset)) for offset in range(0, 4)]
    assert values[0] > values[1] > values[2] > values[3]
