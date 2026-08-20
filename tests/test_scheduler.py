from datetime import date, timedelta

from planner.models import Exam, PriorityWeights, Subject, Topic, UserProfile, complexity_score, topic_priority
from planner.scheduler import allocate_day, generate_week


def fixtures():
    subjects = [Subject("cardio", "Cardiology", 1.0), Subject("renal", "Renal", 0.8), Subject("neuro", "Neurology", 0.9)]
    topics = [
        Topic("ecg", "cardio", "ECG interpretation", complexity=.7, mastery=.2, self_difficulty=5, volume=.8, cognitive_load=.9),
        Topic("aki", "renal", "AKI", complexity=.5, mastery=.4, next_review_due=date.today()),
        Topic("stroke", "neuro", "Stroke syndromes", complexity=.6, mastery=.3),
    ]
    exams = [Exam("midterm", date.today() + timedelta(days=10), ("cardio", "renal"), weight=1.0)]
    return subjects, topics, exams


def test_complexity_is_bounded():
    _, topics, _ = fixtures()
    assert 0 <= complexity_score(topics[0]) <= 1


def test_exam_urgency_increases_priority():
    subjects, topics, exams = fixtures()
    p_now = topic_priority(topics[0], subjects[0], date.today(), exams[0])
    p_later = topic_priority(topics[0], subjects[0], date.today() + timedelta(days=30), exams[0])
    assert p_now > p_later


def test_rest_day_produces_no_sessions():
    subjects, topics, exams = fixtures()
    profile = UserProfile(daily_available_minutes=180, rest_weekdays=(date.today().weekday(),))
    assert allocate_day(subjects, topics, exams, profile, date.today()) == []


def test_week_contains_all_active_subjects():
    subjects, topics, exams = fixtures()
    profile = UserProfile(daily_available_minutes=180, minimum_subject_minutes_week=30)
    sessions = generate_week(subjects, topics, exams, profile, date.today(), 7)
    assert {s.topic_id for s in sessions} >= {"ecg", "aki", "stroke"}


def test_daily_budget_never_exceeded():
    subjects, topics, exams = fixtures()
    profile = UserProfile(daily_available_minutes=120, minimum_subject_minutes_week=20)
    sessions = generate_week(subjects, topics, exams, profile, date.today(), 7)
    for day in {s.date for s in sessions}:
        assert sum(s.planned_minutes for s in sessions if s.date == day) <= 120
