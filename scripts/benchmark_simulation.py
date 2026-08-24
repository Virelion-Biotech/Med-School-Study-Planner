from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import date

from planner.ablation import default_ablation_variants, simulate_variant
from planner.calibration import calibration_passes
from planner.evaluation_v2 import deltas, summarize_population
from planner.evaluation import synthetic_student
from planner.model_validation import validate_models
from planner.simulation import compare_student_population, make_student
from planner.statistics import paired_bootstrap_ci, paired_from_metrics


FIELDS = (
    "mean_mastery",
    "mean_retention",
    "completion_rate",
    "topic_coverage",
    "deadline_coverage",
    "overdue_reviews",
    "fairness_gap_minutes",
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark and ablate study-planning algorithms on synthetic students.")
    parser.add_argument("--seeds", type=int, default=20)
    parser.add_argument("--days", type=int, default=28)
    parser.add_argument("--start", default="2026-08-24")
    parser.add_argument("--ablation", action="store_true", help="run component ablations in addition to the main comparison")
    parser.add_argument("--bootstrap", action="store_true", help="add paired bootstrap 95% confidence intervals")
    parser.add_argument("--model-validation", action="store_true", help="validate BKT and retention calibration on synthetic observations")
    args = parser.parse_args()

    subjects, topics, exams, profile = synthetic_student(7)
    start = date.fromisoformat(args.start)
    seeds = range(1, args.seeds + 1)
    metrics = compare_student_population(subjects, topics, exams, profile, start, seeds, args.days)
    summary = summarize_population(metrics)
    payload = asdict(summary)
    payload["deltas"] = deltas(summary, "legacy_greedy", "adaptive_cpsat")

    paired = {}
    for field in FIELDS:
        effect = paired_from_metrics(metrics, field, "legacy_greedy", "adaptive_cpsat")
        item = asdict(effect)
        if args.bootstrap:
            reference = {m.student_seed: float(getattr(m, field)) for m in metrics if m.planner == "legacy_greedy"}
            candidate = {m.student_seed: float(getattr(m, field)) for m in metrics if m.planner == "adaptive_cpsat"}
            seeds_shared = sorted(set(reference) & set(candidate))
            item["bootstrap_ci95_low"], item["bootstrap_ci95_high"] = paired_bootstrap_ci(
                [reference[s] for s in seeds_shared], [candidate[s] for s in seeds_shared]
            )
        paired[field] = item
    payload["paired_effects"] = paired

    if args.model_validation:
        model_report = validate_models(seed=17, observations=max(1000, args.seeds * 100))
        payload["model_validation"] = {
            "bkt": asdict(model_report.bkt),
            "fsrs_like_retention": asdict(model_report.fsrs),
            "bkt_calibration_pass": calibration_passes(model_report.bkt),
            "retention_calibration_pass": calibration_passes(model_report.fsrs),
        }

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
                for field in FIELDS
            }
            for planner in ablation_summary.planners
            if planner != baseline
        }

    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
