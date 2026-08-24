from planner.models import Subject, Topic
from planner.storage import CURRENT_USER, StudyDB


def test_adaptive_topic_fields_survive_database_round_trip(tmp_path):
    db = StudyDB(tmp_path / "planner.db")
    token = CURRENT_USER.set("topic-round-trip")
    try:
        db.upsert_subject(Subject("s", "Subject"))
        original = Topic(
            "t",
            "s",
            "Topic",
            mastery=0.73,
            knowledge_component_ids=("kc-1", "kc-2"),
            curriculum_node_ids=("node-1",),
            block_id="cardio",
            mastery_uncertainty=0.21,
            memory_retrievability=0.64,
            workload_confidence=0.81,
        )
        db.upsert_topic(original)
        restored = db.get_topic("t")
        assert restored is not None
        assert restored.mastery == 0.73
        assert restored.knowledge_component_ids == ("kc-1", "kc-2")
        assert restored.curriculum_node_ids == ("node-1",)
        assert restored.block_id == "cardio"
        assert restored.mastery_uncertainty == 0.21
        assert restored.memory_retrievability == 0.64
        assert restored.workload_confidence == 0.81
    finally:
        CURRENT_USER.reset(token)
