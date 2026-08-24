from __future__ import annotations

from dataclasses import replace
from datetime import datetime
import math

from .models import clamp
from .state import StudentKnowledgeState


@dataclass(frozen=True)
class BKTParameters:
    """Conservative cold-start priors for a knowledge-component BKT model."""

    learn: float = 0.12
    guess: float = 0.20
    slip: float = 0.10
    forgetting_rate_per_day: float = 0.015


def _decay(mastery: float, elapsed_days: float, forgetting_rate: float) -> float:
    if elapsed_days <= 0:
        return clamp(mastery)
    retention = math.exp(-forgetting_rate * elapsed_days)
    # Forgetting moves probability toward the uninformed 0.5 baseline rather than zero.
    return clamp(0.5 + (mastery - 0.5) * retention)


def predict_mastery(
    state: StudentKnowledgeState,
    now: datetime | None = None,
    params: BKTParameters = BKTParameters(),
) -> float:
    if state.last_observed_at is None or now is None:
        return clamp(state.mastery_probability)
    elapsed_days = max(0.0, (now - state.last_observed_at).total_seconds() / 86400.0)
    return _decay(state.mastery_probability, elapsed_days, params.forgetting_rate_per_day)


def _posterior_after_observation(mastery: float, correct: bool, params: BKTParameters) -> float:
    p_correct = mastery * (1.0 - params.slip) + (1.0 - mastery) * params.guess
    if correct:
        posterior = mastery * (1.0 - params.slip) / max(p_correct, 1e-9)
    else:
        posterior = mastery * params.slip / max(1.0 - p_correct, 1e-9)
    return clamp(posterior)


def update_bkt(
    state: StudentKnowledgeState,
    correct: bool,
    observed_at: datetime,
    params: BKTParameters = BKTParameters(),
) -> StudentKnowledgeState:
    """Update one knowledge component from a binary question/recall observation."""
    prior = predict_mastery(state, observed_at, params)
    posterior = _posterior_after_observation(prior, correct, params)
    learned = posterior + (1.0 - posterior) * params.learn
    observations = state.observations + 1
    # Uncertainty contracts with evidence but never reaches an unjustified zero.
    uncertainty = max(0.05, 1.0 / math.sqrt(observations + 1))
    return replace(
        state,
        mastery_probability=clamp(learned),
        uncertainty=uncertainty,
        observations=observations,
        last_observed_at=observed_at,
    )
