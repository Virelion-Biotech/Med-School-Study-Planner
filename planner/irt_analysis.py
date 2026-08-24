from __future__ import annotations

from dataclasses import dataclass
import math

from .irt import IRTItem, IRTResponse, evidence_sufficient, probability_correct


@dataclass(frozen=True)
class IRTEstimate:
    theta: float
    standard_error: float | None
    converged: bool
    iterations: int
    responses: int
    unique_questions: int
    reliable: bool


def estimate_theta(
    responses: list[tuple[IRTResponse, IRTItem]],
    initial_theta: float = 0.0,
    max_iterations: int = 50,
    tolerance: float = 1e-5,
    min_attempts: int = 1000,
    min_questions: int = 100,
) -> IRTEstimate:
    unique_questions = len({r.question_id for r, _ in responses})
    reliable = evidence_sufficient(len(responses), unique_questions, min_attempts, min_questions)
    if not reliable:
        return IRTEstimate(initial_theta, None, False, 0, len(responses), unique_questions, False)

    theta = max(-4.0, min(4.0, initial_theta))
    converged = False
    iterations = 0
    for iterations in range(1, max_iterations + 1):
        gradient = 0.0
        information = 0.0
        for response, item in responses:
            p = probability_correct(theta, item)
            p = min(1.0 - 1e-9, max(1e-9, p))
            a = max(1e-6, item.discrimination)
            y = 1.0 if response.correct else 0.0
            gradient += a * (y - p)
            information += a * a * p * (1.0 - p)
        if information <= 1e-9:
            break
        step = gradient / information
        step = max(-0.75, min(0.75, step))
        new_theta = max(-4.0, min(4.0, theta + step))
        if abs(new_theta - theta) < tolerance:
            theta = new_theta
            converged = True
            break
        theta = new_theta

    information = 0.0
    for _, item in responses:
        p = probability_correct(theta, item)
        p = min(1.0 - 1e-9, max(1e-9, p))
        a = max(1e-6, item.discrimination)
        information += a * a * p * (1.0 - p)
    standard_error = math.sqrt(1.0 / information) if information > 1e-9 else None
    return IRTEstimate(theta, standard_error, converged, iterations, len(responses), unique_questions, reliable)
