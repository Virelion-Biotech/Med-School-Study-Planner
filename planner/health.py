"""Cheap runtime health/readiness checks.

These checks deliberately avoid probing private infrastructure. They validate
that the mathematical engine and its configuration are usable before serving
planning requests.
"""
from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class HealthReport:
    status: str
    checks: dict[str, bool]

    @property
    def ready(self) -> bool:
        return self.status == "ready"


def check_finite(values: list[float]) -> bool:
    return all(math.isfinite(float(v)) for v in values)


def planner_health(*, capacity_minutes: int, quantum_minutes: int,
                   max_session_minutes: int) -> HealthReport:
    checks = {
        "capacity_positive": capacity_minutes > 0,
        "quantum_positive": quantum_minutes > 0,
        "capacity_divisible_by_quantum": (
            quantum_minutes > 0 and capacity_minutes % quantum_minutes == 0
        ),
        "session_positive": max_session_minutes > 0,
        "session_not_above_capacity": (
            capacity_minutes > 0 and max_session_minutes <= capacity_minutes
        ),
    }
    return HealthReport("ready" if all(checks.values()) else "not_ready", checks)
