from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class IRTItem:
    question_id: str
    difficulty: float = 0.0
    discrimination: float = 1.0


@dataclass(frozen=True)
class IRTResponse:
    question_id: str
    correct: bool
    student_id: str


def probability_correct(theta: float, item: IRTItem, guessing: float = 0.0) -> float:
    """2PL probability with optional lower asymptote; fitting is deliberately external."""
    z = max(-35.0, min(35.0, item.discrimination * (theta - item.difficulty)))
    logistic = 1.0 / (1.0 + math.exp(-z))
    return guessing + (1.0 - guessing) * logistic


def weighted_log_likelihood(theta: float, responses: list[tuple[IRTResponse, IRTItem]]) -> float:
    """Diagnostic likelihood used once enough question data exists."""
    total = 0.0
    for response, item in responses:
        p = min(1 - 1e-9, max(1e-9, probability_correct(theta, item)))
        total += math.log(p if response.correct else 1.0 - p)
    return total


def evidence_sufficient(attempt_count: int, unique_questions: int, min_attempts: int = 1000, min_questions: int = 100) -> bool:
    """Prevent premature per-student IRT inference from tiny samples."""
    return attempt_count >= min_attempts and unique_questions >= min_questions
