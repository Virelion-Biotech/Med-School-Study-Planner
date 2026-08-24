from __future__ import annotations

import argparse
import math
import sys
from datetime import date

from planner.calibration import calibration_report
from planner.evaluation import synthetic_student
from planner.models import StudySession
from planner.simulation import compare_student_population
from planner.adaptive_cpsat import optimize_adaptive_week


def _validate_sessions(sessions: list[StudySession], daily_capacity: int, max_session: int) -> list[str]:
    errors: list[str] = []
    by_day: dict[date, int] = {}
    for session in sessions:
        if session.planned_minutes <= 0:
            errors.append(f"non-positive session: {session}")
        if session.planned_minutes > max_session:
            errors.append(f"session exceeds max_session_minutes: {session}")
        if session.planned_minutes % 15 != 0:
            errors.append(f"session is not aligned to 15-minute quantum: {session}")
        by_day[session.date] = by_day.get(session.date, 0) + session.planned_minutes
    for day, minutes in by_day.items():
        if minutes > daily_capacity:
            errors.append(f"daily capacity exceeded on {day}: {minutes}>{daily_capacity}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Deterministic planner regression/invariant gate.")
    parser.add_argument("--seeds", type=int, default=5)
    parser.add_argument("--days", type=int, default=14)
    parser.add_argument("--start", default="2026-08-24")
    parser.add_argument("--max-ece", type=float, default=0.20)
    parser.add_argument("--max-brier", type=float, default=0.25)
    args = parser.parse_args()

    subjects, topics, exams, profile = synthetic_student(7)
    start = date.fromisoformat(args.start)
    plan = optimize_adaptive_week(subjects, topics, exams, profile, start, args.days)
    errors = _validate_sessions(plan.sessions, profile.daily_available_minutes, profile.max_session_minutes)

    if not all(math.isfinite(x) for x in (t.mastery for t in topics)):
        errors.append("non-finite topic mastery")
    if not all(0.0 <= t.mastery <= 1.0 for t in topics):
        errors.append("topic mastery outside [0,1]")

    # Smoke-test the longitudinal simulator on paired students. This is intentionally
    # small enough for CI while still exercising the full scheduler stack.
    metrics = compare_student_population(subjects, topics, exams, profile, start, range(1, args.seeds + 1), args.days)
    for metric in metrics:
        values = (
            metric.completion_rate,
            metric.mean_mastery,
            metric.mean_retention,
            metric.topic_coverage,
            metric.deadline_coverage,
        )
        if not all(math.isfinite(x) for x in values):
            errors.append(f"non-finite simulation metric for seed={metric.student_seed}, planner={metric.planner}")

    # Deterministic binary calibration smoke-test for the validation layer.
    cal = calibration_report([0.1, 0.3, 0.7, 0.9], [0, 0, 1, 1])
    if cal.expected_calibration_error > args.max_ece:
        errors.append(f"calibration ECE too high: {cal.expected_calibration_error:.4f}>{args.max_ece:.4f}")
    if cal.brier_score > args.max_brier:
        errors.append(f"calibration Brier score too high: {cal.brier_score:.4f}>{args.max_brier:.4f}")

    if errors:
        print("REGRESSION GATE: FAILED")
        for error in errors:
            print(f"- {error}")
        return 1

    print("REGRESSION GATE: PASSED")
    print(f"planner_sessions={len(plan.sessions)} simulated_students={args.seeds} horizon_days={args.days}")
    print(f"calibration_ece={cal.expected_calibration_error:.4f} calibration_brier={cal.brier_score:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
