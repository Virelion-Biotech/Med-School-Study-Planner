from datetime import date

from planner.kc_planning import optimize_with_kc_state
from planner.models import Exam, Subject, Topic, UserProfile


class StubDB:
    def __init__(self, context):
        self.context = context

    def load_knowledge_components_for_id(self, kc_id):
        return self.context["kc"]

    def curriculum_mappings_for_kc(self, kc_id):
        return self.context["mappings"]

    def get_knowledge_state(self, kc_id, initial_mastery):
        return self.context["state"]

    def question_history(self, topic_id=None):
        return []


def test_kc_aware_entrypoint_preserves_topic_execution_units():
    from planner.cross_curriculum import CurriculumMapping
    from planner.state import KnowledgeComponent, StudentKnowledgeState

    subject = Subject("s", "Cardiology")
    topic = Topic("t", "s", "Heart failure", mastery=0.1, knowledge_component_ids=("kc",))
    context = {
        "kc": KnowledgeComponent("kc", "t", "Heart failure"),
        "mappings": [CurriculumMapping("kc", "school-hf", "school")],
        "state": StudentKnowledgeState("kc", mastery_probability=0.75, uncertainty=0.2, observations=10),
    }
    db = StubDB(context)
    plan = optimize_with_kc_state(
        db,
        [subject],
        [topic],
        [Exam("e", date(2026, 9, 7), ("s",))],
        UserProfile(daily_available_minutes=60, max_session_minutes=60),
        date(2026, 8, 24),
        days=1,
    )
    assert all(session.topic_id == "t" for session in plan.sessions)
