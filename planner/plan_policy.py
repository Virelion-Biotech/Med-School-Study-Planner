"""Central policy for safe scheduling defaults.

Keeping safety constraints in one pure module makes API, optimizer and
regression tests agree on the same invariants.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlannerPolicy:
    quantum_minutes: int = 15
    max_session_minutes: int = 90
    min_session_minutes: int = 15
    max_daily_minutes: int = 12 * 60
    minimum_rest_days_per_week: int = 0

    def validate(self) -> None:
        if self.quantum_minutes <= 0:
            raise ValueError("quantum_minutes must be positive")
        if self.min_session_minutes < self.quantum_minutes:
            raise ValueError("min_session_minutes must be >= quantum_minutes")
        if self.max_session_minutes < self.min_session_minutes:
            raise ValueError("max_session_minutes must be >= min_session_minutes")
        if self.max_session_minutes % self.quantum_minutes:
            raise ValueError("max_session_minutes must align to quantum")
        if self.max_daily_minutes < self.max_session_minutes:
            raise ValueError("max_daily_minutes must cover one session")
        if not 0 <= self.minimum_rest_days_per_week <= 7:
            raise ValueError("minimum_rest_days_per_week must be 0..7")
