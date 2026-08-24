from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum

from .models import ActivityType


@dataclass(frozen=True)
class KnowledgeComponent:
    id: str
    topic_id: str
    name: str
    initial_mastery: float = 0.50


@dataclass(frozen=True)
class CurriculumNode:
    id: str
    name: str
    node_type: str
    parent_id: str | None = None
    source: str = "personal"


@dataclass
class WorkloadEstimate:
    topic_id: str
    predicted_minutes: float
    lower_bound_minutes: float
    upper_bound_minutes: float
    confidence: float = 0.25
    sample_count: int = 0
    source: str = "prior"

    def bounded_minutes(self) -> float:
        return max(self.lower_bound_minutes, min(self.predicted_minutes, self.upper_bound_minutes))


@dataclass
class StudentKnowledgeState:
    knowledge_component_id: str
    mastery_probability: float = 0.50
    uncertainty: float = 1.0
    observations: int = 0
    last_observed_at: datetime | None = None


@dataclass
class StudentFSRSState:
    topic_id: str
    card_json: str | None = None
    stability: float | None = None
    difficulty: float | None = None
    retrievability: float | None = None
    due: datetime | None = None
    last_review: datetime | None = None
    repetitions: int = 0
    state: int = 0


@dataclass(frozen=True)
class StudyAction:
    topic_id: str
    activity: ActivityType
    day: date
    estimated_minutes: int
    utility_per_minute: float
    reasons: tuple[str, ...] = field(default_factory=tuple)
