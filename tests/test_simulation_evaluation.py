from datetime import date

from planner.evaluation_v2 import deltas, summarize_population
from planner.evaluation import synthetic_student
from planner.simulation import compare_student_population, make_student, simulate_planner


# Uses the established deterministic synthetic fixture from evaluation.py.
def test_synthetic_student_is_deterministic():
    assert make_student(12) == make_student(12)


def test_simulation_is_reproducible():
    subjects, topics, exams, profile = synthetic_student(3)
    student = make_student(4)
    first = simulate_planner("adaptive_cpsat", subjects, topics, exams, profile, student, date(2026, 8, 24), 7).metrics
    second = simulate_planner("adaptive_cpsat", subjects, topics, exams, profile, student, date(2026, 8, 24), 7).metrics
    assert first == second


def test_population_summary_and_delta():
    subjects, topics, exams, profile = synthetic_student(5)
    metrics = compare_student_population(subjects, topics, exams, profile, date(2026, 8, 24), range(1, 4), 7)
    summary = summarize_population(metrics)
    assert summary.samples == 3
    delta = deltas(summary, "legacy_greedy", "adaptive_cpsat")
    assert set(delta) == {
        "mastery", "retention", "completion_rate", "topic_coverage",
        "deadline_coverage", "overdue_reviews", "fairness_gap_minutes",
    }
