from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReadinessComponents:
    knowledge: float
    retention: float
    coverage: float
    practice: float
    deadline_protection: float

    @property
    def score(self) -> float:
        return (
            0.30 * self.knowledge
            + 0.20 * self.retention
            + 0.20 * self.coverage
            + 0.20 * self.practice
            + 0.10 * self.deadline_protection
        )

    @property
    def label(self) -> str:
        value = self.score
        if value >= 0.80:
            return "Strong"
        if value >= 0.65:
            return "Good"
        if value >= 0.50:
            return "Moderate"
        if value >= 0.35:
            return "At risk"
        return "Low"


def readiness_from_signals(
    knowledge: float,
    retention: float,
    coverage: float,
    practice: float,
    deadline_protection: float,
) -> ReadinessComponents:
    clamp = lambda x: max(0.0, min(1.0, float(x)))
    return ReadinessComponents(clamp(knowledge), clamp(retention), clamp(coverage), clamp(practice), clamp(deadline_protection))
