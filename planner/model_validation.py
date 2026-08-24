from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import math
import random

from .calibration import CalibrationReport, calibrate_binary_predictions
from .mastery import BKTParameters, update_bkt
from .models import clamp
from .state import StudentKnowledgeState


@dataclass(frozen=True)
class ModelValidationReport:
    bkt: CalibrationReport
    fsrs: CalibrationReport


def validate_bkt_simulation(seed: int = 7, observations: int = 2000) -> CalibrationReport:
    rng = random.Random(seed)
    params = BKTParameters()
    predictions: list[float] = []
    outcomes: list[bool] = []
    for student_idx in range(max(1, observations // 20)):
        state = StudentKnowledgeState(f"kc-{student_idx}", rng.uniform(0.15, 0.85))
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        for _ in range(20):
            predicted = state.mastery_probability
            latent = clamp(predicted + rng.gauss(0.0, 0.06))
            p_correct = latent * (1.0 - params.slip) + (1.0 - latent) * params.guess
            correct = rng.random() < p_correct
            predictions.append(predicted)
            outcomes.append(correct)
            state = update_bkt(state, correct, now, params)
            now += timedelta(days=rng.uniform(0.2, 2.0))
    return calibrate_binary_predictions(predictions[:observations], outcomes[:observations])


def validate_fsrs_like_simulation(seed: int = 11, observations: int = 2000) -> CalibrationReport:
    rng = random.Random(seed)
    predictions: list[float] = []
    outcomes: list[bool] = []
    for _ in range(observations):
        stability = math.exp(rng.uniform(math.log(1.5), math.log(30.0)))
        elapsed = rng.uniform(0.0, 45.0)
        predicted = math.exp(-elapsed / stability)
        difficulty_factor = rng.uniform(0.75, 1.25)
        recall_probability = clamp(predicted ** difficulty_factor)
        predictions.append(predicted)
        outcomes.append(rng.random() < recall_probability)
    return calibrate_binary_predictions(predictions, outcomes)


def validate_models(seed: int = 7, observations: int = 2000) -> ModelValidationReport:
    return ModelValidationReport(
        validate_bkt_simulation(seed, observations),
        validate_fsrs_like_simulation(seed + 1, observations),
    )
