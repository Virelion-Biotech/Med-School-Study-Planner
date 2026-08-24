from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import date

from planner.evaluation_v2 import deltas, summarize_population
from planner.evaluation import synthetic_student
from planner.simulation import compare_student_population


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark legacy vs adaptive study planning on synthetic students.")
    parser.add_argument("--seeds", type=int, default=20)
    parser.add_argument("--days", type=int, default=28)
    parser.add_argument("--start", default="2026-08-24")
    args = parser.parse_args()
    subjects, topics, exams, profile = synthetic_student(7)
    start = date.fromisoformat(args.start)
    metrics = compare_student_population(subjects, topics, exams, profile, start, range(1, args.seeds + 1), args.days)
    summary = summarize_population(metrics)
    payload = asdict(summary)
    payload["deltas"] = deltas(summary, "legacy_greedy", "adaptive_cpsat")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
