from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class PlannerAnalytics:
    planned_minutes: int
    actual_minutes: int
    completion_rate: float
    mean_performance: float | None
    planning_error_minutes: int
    planning_error_rate: float
    mastery_mean: float
    reviews_due: int
    subject_minutes: dict[str, int]


def summarize(snapshot: dict, as_of: date | None = None) -> PlannerAnalytics:
    as_of = as_of or date.today()
    sessions = snapshot.get("sessions", [])
    topics = snapshot.get("topics", [])
    planned = sum(int(s.get("planned_minutes", 0)) for s in sessions)
    completed = [s for s in sessions if s.get("completed")]
    actual = sum(int(s.get("actual_minutes") or 0) for s in completed)
    completion_rate = len(completed) / len(sessions) if sessions else 0.0
    scores = [float(s["performance_score"]) for s in completed if s.get("performance_score") is not None]
    mean_performance = sum(scores) / len(scores) if scores else None
    planning_error = actual - sum(int(s.get("planned_minutes", 0)) for s in completed)
    denominator = max(1, sum(int(s.get("planned_minutes", 0)) for s in completed))
    mastery = [float(t.get("mastery", 0)) for t in topics]
    due = sum(1 for t in topics if t.get("next_review_due") and t["next_review_due"] <= as_of.isoformat())
    subject_by_topic = {t["id"]: t.get("subject_id", "") for t in topics}
    subject_minutes: dict[str, int] = defaultdict(int)
    for s in sessions:
        subject_minutes[subject_by_topic.get(s.get("topic_id"), "")] += int(s.get("actual_minutes") or s.get("planned_minutes") or 0)
    return PlannerAnalytics(
        planned_minutes=planned,
        actual_minutes=actual,
        completion_rate=completion_rate,
        mean_performance=mean_performance,
        planning_error_minutes=planning_error,
        planning_error_rate=planning_error / denominator,
        mastery_mean=sum(mastery) / len(mastery) if mastery else 0.0,
        reviews_due=due,
        subject_minutes=dict(subject_minutes),
    )


def topic_time_history(snapshot: dict) -> dict[str, list[int]]:
    history: dict[str, list[int]] = defaultdict(list)
    for s in snapshot.get("sessions", []):
        if s.get("completed") and s.get("actual_minutes") is not None:
            history[s["topic_id"]].append(int(s["actual_minutes"]))
    return dict(history)
