# Med-School-Study-Planner

A complexity-aware, fairness-constrained study scheduling engine for medical education.

## Architecture

`Curriculum + Exams + Performance -> Priority scoring -> Fairness/review allocation -> Study sessions -> Performance feedback`

### v0.1 core

- Explicit Subject / Topic / Exam / StudySession / UserProfile domain model.
- Complexity score from cognitive load, topic volume, and personal difficulty.
- Priority score from exam urgency, complexity, mastery gap, exam weighting, and review due date.
- Daily wellbeing cap and configurable rest days.
- Subject fairness floor before priority-weighted allocation.
- Protected spaced-review budget.
- Deterministic weekly plan generation.
- Conservative mastery update + review interval feedback loop.
- Historical time-to-mastery complexity recalibration primitive.
- FastAPI `/health` and `/plan` endpoints.
- Unit tests and GitHub Actions CI.

## Roadmap

1. Persist curriculum, exams, sessions, and performance in SQLite/Postgres.
2. Track weekly fairness debt rather than using only a daily proxy.
3. Add Leitner/SM-2 scheduling with configurable retention targets.
4. Add OR-Tools constrained optimization for hard exam/deadline constraints.
5. Add adaptive learning-curve models once real usage data exists.
6. Add React/FullCalendar dashboard and session completion UX.
7. Add authentication, exports, analytics, and multi-user support.

## Run locally

```bash
pip install -e '.[test]'
uvicorn planner.api:app --reload
pytest -q
```
