from __future__ import annotations

from dataclasses import dataclass, replace

from .adaptive_cpsat import optimize_adaptive_week
from .models import ActivityType, Exam, Subject, Topic, UserProfile
from .simulation import SimulationMetrics, SyntheticStudent, simulate_planner


@dataclass(frozen=True)
class AblationVariant:
    name: str
    adaptive: bool = True
    use_activity_evidence: bool = True
    use_reviews: bool = True
    use_fairness: bool = True


def topic_without_evidence(topic: Topic) -> Topic:
    return replace(
        topic,
        question_attempts=0,
        recent_question_accuracy=0.5,
        question_confidence_gap=0.0,
        question_evidence_strength=0.0,
    )


def topic_without_reviews(topic: Topic) -> Topic:
    return replace(topic, next_review_due=None, memory_retrievability=1.0)


def simulate_variant(
    variant: AblationVariant,
    subjects: list[Subject],
    topics: list[Topic],
    exams: list[Exam],
    profile: UserProfile,
    student: SyntheticStudent,
    start,
    days: int = 28,
) -> SimulationMetrics:
    variant_topics = list(topics)
    if not variant.use_activity_evidence:
        variant_topics = [topic_without_evidence(t) for t in variant_topics]
    if not variant.use_reviews:
        variant_topics = [topic_without_reviews(t) for t in variant_topics]
    variant_profile = profile
    if not variant.use_fairness:
        variant_profile = replace(profile, minimum_subject_minutes_week=0)
    planner_name = variant.name if variant.adaptive else "legacy_greedy"
    return simulate_planner(planner_name, subjects, variant_topics, exams, variant_profile, student, start, days).metrics


def default_ablation_variants() -> tuple[AblationVariant, ...]:
    return (
        AblationVariant("full_adaptive"),
        AblationVariant("no_evidence", use_activity_evidence=False),
        AblationVariant("no_reviews", use_reviews=False),
        AblationVariant("no_fairness", use_fairness=False),
        AblationVariant("legacy", adaptive=False),
    )
