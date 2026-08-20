# Med-School-Study-Planner

A complexity-aware, fairness-constrained study scheduling engine for medical education.

## Architecture

`Curriculum + Exams + Performance -> Priority scoring -> Weekly fairness debt + protected review -> Rule scheduler / CP-SAT optimizer -> Study sessions -> completion -> mastery/review feedback`

## v0.2 engine

- Subject / Topic / Exam / StudySession / UserProfile domain model.
- Complexity estimate from cognitive load, topic volume, and personal difficulty.
- Priority score from urgency, complexity, mastery gap, exam weighting, and review due state.
- Weekly fairness debt: subject minimums are treated as explicit weekly obligations instead of daily approximations.
- Protected review budget that increases as the nearest exam approaches.
- SQLite persistence for curriculum, exams, topics, sessions, and user settings.
- Persisted session IDs plus `/sessions/{id}/complete` for actual-time and quiz-performance feedback.
- Adaptive mastery updates and review-date feedback after completion.
- Optional OR-Tools CP-SAT optimizer using 15-minute scheduling quanta; automatic Tier-1 fallback when the extra is not installed.
- Deterministic rule-based scheduling remains the default for a lightweight MVP.
- Unit tests covering fairness/rest days, adaptation, and SQLite round-trips.

## API

```text
GET  /health
POST /plan
POST /sessions/{session_id}/complete
GET  /snapshot
```

`POST /plan` supports `optimizer=true` for CP-SAT and `persist=true` to store the generated plan. Persisted responses include `session_id` so completion can feed the topic state back into the planner.

## Run locally

```bash
pip install -e '.[test]'
uvicorn planner.api:app --reload
pytest -q
```

For the optimizer:

```bash
pip install -e '.[test,optimizer]'
```

## Roadmap

1. Leitner/SM-2 or FSRS-style configurable retention scheduler.
2. Historical actual-vs-planned time model and per-topic learning curves.
3. Hard exam coverage constraints and multi-exam conflict optimization.
4. React + calendar dashboard and session completion UX.
5. Authentication, exports, analytics, and multi-user deployment.
