from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import math

from .adaptive_db import AdaptiveDB


@dataclass(frozen=True)
class EvidenceSummary:
    attempts: int = 0
    recent_attempts: int = 0
    accuracy: float = 0.5
    recent_accuracy: float = 0.5
    confidence: float = 0.5
    response_time_seconds: float | None = None
    recent_response_time_seconds: float | None = None
    error_rate: float = 0.5
    evidence_strength: float = 0.0


def summarize_question_evidence(
    db: AdaptiveDB,
    topic_id: str,
    now: datetime,
    recent_days: int = 21,
    recent_limit: int = 12,
) -> EvidenceSummary:
    rows = db.question_history(topic_id)
    if not rows:
        return EvidenceSummary()
    cutoff = now - timedelta(days=recent_days)
    recent = [r for r in rows if datetime.fromisoformat(r["attempted_at"]) >= cutoff][-recent_limit:]

    def mean(values: list[float], default: float = 0.5) -> float:
        return sum(values) / len(values) if values else default

    correct = [float(r["correct"]) for r in rows]
    recent_correct = [float(r["correct"]) for r in recent]
    confidences = [float(r["confidence"]) for r in rows if r["confidence"] is not None]
    times = [float(r["response_time_seconds"]) for r in rows if r["response_time_seconds"] is not None and r["response_time_seconds"] >= 0]
    recent_times = [float(r["response_time_seconds"]) for r in recent if r["response_time_seconds"] is not None and r["response_time_seconds"] >= 0]
    n = len(rows)
    strength = 1.0 - math.exp(-n / 8.0)
    return EvidenceSummary(
        attempts=n,
        recent_attempts=len(recent),
        accuracy=mean(correct),
        recent_accuracy=mean(recent_correct),
        confidence=mean(confidences),
        response_time_seconds=mean(times, 0.0) if times else None,
        recent_response_time_seconds=mean(recent_times, 0.0) if recent_times else None,
        error_rate=1.0 - mean(recent_correct),
        evidence_strength=strength,
    )


def evidence_activity_adjustment(evidence: EvidenceSummary) -> dict[str, float]:
    """Return bounded multipliers for activity choice, not raw priority weights."""
    weak = max(0.0, 1.0 - evidence.recent_accuracy)
    overconfident = max(0.0, evidence.confidence - evidence.recent_accuracy)
    slow = 0.0
    if evidence.recent_response_time_seconds is not None and evidence.response_time_seconds:
        slow = max(0.0, min(1.0, evidence.recent_response_time_seconds / max(evidence.response_time_seconds, 1.0) - 1.0))
    return {
        "learn": 1.0 + 0.35 * weak,
        "review": 1.0 + 0.30 * max(0.0, 0.55 - evidence.recent_accuracy),
        "questions": 1.0 + 0.55 * weak + 0.20 * slow,
        "recall": 1.0 + 0.35 * weak,
        "mixed": 1.0 + 0.15 * (1.0 - weak),
        "confidence_gap": overconfident,
    }
