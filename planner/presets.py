from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from .models import Exam, Subject, Topic, UserProfile


@dataclass(frozen=True)
class BlueprintBand:
    id: str
    name: str
    low: float
    high: float

    @property
    def midpoint(self) -> float:
        return (self.low + self.high) / 2.0


# Source: official USMLE Step 1 Content Outline and Specifications.
# Percentages are ranges; the preset stores the midpoint only as a planning signal.
STEP1_SYSTEMS = (
    BlueprintBand("development", "Human Development", 1, 3),
    BlueprintBand("immune-blood", "Blood, Lymphoreticular & Immune", 9, 13),
    BlueprintBand("neuro", "Behavioral Health & Nervous System / Special Senses", 10, 14),
    BlueprintBand("msk-skin", "Musculoskeletal, Skin & Subcutaneous", 8, 12),
    BlueprintBand("cardio", "Cardiovascular", 7, 11),
    BlueprintBand("resp-renal", "Respiratory & Renal / Urinary", 11, 15),
    BlueprintBand("gi", "Gastrointestinal", 6, 10),
    BlueprintBand("repro-endo", "Reproductive & Endocrine", 12, 16),
    BlueprintBand("multisystem", "Multisystem Processes & Disorders", 8, 12),
    BlueprintBand("biostats", "Biostatistics, Epidemiology & Population Health", 4, 6),
    BlueprintBand("communication", "Communication & Interpersonal Skills", 6, 9),
)


def step1_preset(start: date) -> tuple[list[Subject], list[Topic], list[Exam], UserProfile]:
    subjects: list[Subject] = []
    topics: list[Topic] = []
    for band in STEP1_SYSTEMS:
        midpoint = band.midpoint
        # Keep the official midpoint as a visible planning signal. Topic priority
        # normalizes this against the largest Step 1 system range.
        subjects.append(Subject(band.id, band.name, midpoint, "USMLE Step 1"))
        weight_hours = 1.25 + midpoint / 4.0
        topics.extend(
            [
                Topic(f"{band.id}-physiology", band.id, "Normal physiology & mechanisms", complexity=0.62, estimated_hours=weight_hours * 0.8, mastery=0.0, self_difficulty=3.0, volume=0.65, cognitive_load=0.75),
                Topic(f"{band.id}-pathology", band.id, "Pathology & disease mechanisms", complexity=0.72, estimated_hours=weight_hours * 1.15, mastery=0.0, self_difficulty=3.5, volume=0.75, cognitive_load=0.85),
                Topic(f"{band.id}-pharmacology", band.id, "Pharmacology & treatment mechanisms", complexity=0.68, estimated_hours=weight_hours * 0.75, mastery=0.0, self_difficulty=3.3, volume=0.65, cognitive_load=0.8),
            ]
        )

    exam = Exam(
        "USMLE Step 1",
        start + timedelta(days=56),
        tuple(s.id for s in subjects),
        (),
        1.0,
    )
    profile = UserProfile(
        daily_available_minutes=240,
        minimum_subject_minutes_week=30,
        review_fraction=0.30,
        max_session_minutes=60,
        rest_weekdays=(),
        energy_pattern=("high", "high", "medium", "medium"),
    )
    return subjects, topics, [exam], profile
