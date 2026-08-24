from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import date

from planner.ablation import default_ablation_variants, simulate_variant
from planner.evaluation_v2 import deltas, summarize_population
from planner.evaluation import synthetic_student
from planner.simulation import compare_student_population, make_student
from planner.statistics import paired_from_metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark and ablate study-planning algorithms on synthetic students.")
    parser.add_argument("--seeds", type=int, default=20)
    parser.add_argument("--days", type=int, default=28)
    parser.add_argument("--start", default="2026-08-24")
    parser.add_argument("--ablation", action="store_true", help="run component ablations in addition to the main comparison")
    args = parser.parse_args()

    subjects, topics, exams, profile = synthetic_student(7)
    start = date.fromisoformat(args.start)
    seeds = range(1, args.seeds + 1)
    metrics = compare_student_population(subjects, topics, exams, profile, start, seeds, args.days)
    summary = summarize_population(metrics)
    payload = asdict(summary)
    payload["deltas"] = deltas(summary, "legacy_greedy", "adaptive_cpsat")

    paired = {}
    for field in ("mean_mastery", "mean_retention", "completion_rate", "topic_coverage", "deadline_coverage", "overdue_reviews", "fairness_gap_minutes"):
        effect = paired_from_metrics(metrics, field, "legacy_greedy", "adaptive_cpsat")
        paired[field] = asdict(effect)
    payload["paired_effects"] = paired

    if args.ablation:
        ablation_metrics = []
        for variant in default_ablation_variants():
            for seed in seeds:
                student = make_student(seed)
                ablation_metrics.append(simulate_variant(variant, subjects, topics, exams, profile, student, start, args.days))
        ablation_summary = summarize_population(ablation_metrics)
        payload["ablation_summary"] = asdict(ablation_summary)
        baseline = "full_adaptive"
        payload["ablation_effects_vs_full"] = {
            planner: {
                field: asdict(paired_from_metrics(ablation_metrics, field, baseline, planner))
                for field in ("mean_mastery", "mean_retention", "completion_rate", "topic_coverage", "deadline_coverage", "overdue_reviews", "fairness_gap_minutes")
            }
            for planner in ablation_summary.planners
            if planner != baseline
        }

    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
