from datetime import date

from planner.evaluation import compare_planners, synthetic_student


def test_synthetic_student_is_deterministic():
    a = synthetic_student(11)
    b = synthetic_student(11)
    assert [t.id for t in a[1]] == [t.id for t in b[1]]
    assert [round(t.mastery, 6) for t in a[1]] == [round(t.mastery, 6) for t in b[1]]


def test_evaluation_returns_legacy_and_adaptive_baselines():
    subjects, topics, exams, profile = synthetic_student(3)
    results = compare_planners(subjects, topics, exams, profile, date(2026, 8, 24), 7)
    assert {r.name for r in results} == {"legacy_greedy", "adaptive_cpsat"}
    assert all(0 <= r.topic_coverage <= 1 for r in results)
    assert all(r.planned_minutes >= 0 for r in results)
