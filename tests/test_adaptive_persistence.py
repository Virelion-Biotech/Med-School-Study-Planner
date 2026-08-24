from datetime import datetime, timezone

from planner.adaptive_db import AdaptiveDB
from planner.fsrs import FSRSAdapter
from planner.models import Subject, Topic
from planner.state import CurriculumNode, KnowledgeComponent
from planner.storage import StudyDB
from planner.workload import initial_workload


def test_adaptive_state_round_trips(tmp_path):
    db = StudyDB(tmp_path / "planner.db")
    db.upsert_subject(Subject("s", "Subject"))
    db.upsert_topic(Topic("t", "s", "Topic"))
    adaptive = AdaptiveDB(db)
    adaptive.save_curriculum_nodes([CurriculumNode("root", "Course", "course", source="school")])
    adaptive.save_knowledge_components([KnowledgeComponent("kc", "t", "Skill")])
    assert adaptive.load_curriculum_nodes()[0].id == "root"
    assert adaptive.load_knowledge_components("t")[0].id == "kc"
    state = adaptive.get_knowledge_state("kc")
    adaptive.save_knowledge_state(state)
    assert adaptive.get_knowledge_state("kc").knowledge_component_id == "kc"
    workload = initial_workload(Topic("t", "s", "Topic", estimated_hours=1))
    adaptive.save_workload(workload)
    assert adaptive.get_workload("t")["topic_id"] == "t"


def test_fsrs_state_round_trips_and_question_events_persist(tmp_path):
    db = StudyDB(tmp_path / "planner.db")
    db.upsert_subject(Subject("s", "Subject"))
    db.upsert_topic(Topic("t", "s", "Topic"))
    adaptive = AdaptiveDB(db)
    fsrs = FSRSAdapter(enable_fuzzing=False)
    state = fsrs.review(fsrs.new_state("t"), 3, datetime(2026, 8, 24, tzinfo=timezone.utc))
    adaptive.save_fsrs_state(state)
    loaded = adaptive.get_fsrs_state("t")
    assert loaded and loaded.card_json == state.card_json
    adaptive.record_question_attempt("q1", "t", datetime(2026, 8, 24, tzinfo=timezone.utc), True)
    assert len(adaptive.question_history("t")) == 1
