# Med-School-Study-Planner

An adaptive, fairness-constrained medical study planner that turns curriculum, exams, mastery, memory state, and real study performance into a continuously replanned schedule.

## Pipeline

`Curriculum + Exams + Profile -> Complexity + Priority -> Weekly fairness + memory/review -> Rule scheduler / CP-SAT -> Study sessions -> Completion/performance -> Memory + mastery + time calibration -> Replan`

## Implemented

- Subject, Topic, Exam, StudySession, and UserProfile domain model.
- Complexity scoring from volume, cognitive load, and personal difficulty.
- Priority scoring from urgency, complexity, mastery gap, exam weighting, and review state.
- Weekly subject fairness floors with explicit residual debt.
- Protected review allocation that increases near exams.
- SQLite persistence for curriculum, exams, topics, sessions, profile, and memory state.
- SM-2-inspired transparent memory scheduling with bounded ease/stability.
- Adaptive mastery updates from session performance.
- Actual-vs-planned study-time history and complexity recalibration.
- CP-SAT optimization with daily capacity, rest-day, fairness, locked-session, and near-term exam-coverage constraints.
- Rule-based fallback when OR-Tools is unavailable or the optimization problem is infeasible.
- Explicit reporting of unfulfilled fairness and exam-coverage requirements.
- Drag-and-drop session rescheduling with server-side rest-day, daily-cap, and exam-deadline validation.
- Locked-session replanning that preserves moved work and accounts for its subject/time/topic coverage.
- Browser UI for Today, Week, Curriculum, Exams, Insights, session completion, and planner settings.
- Curriculum/exam CRUD and profile settings UI.
- JSON snapshot and CSV session exports.
- Dockerfile + Compose deployment with persistent SQLite storage.
- GitHub Actions CI with compile checks and full test suite.

## API

```text
GET  /health
GET  /profile
PUT  /profile
POST /subjects
DELETE /subjects/{id}
POST /topics
DELETE /topics/{id}
POST /exams
DELETE /exams/{id}
POST /plan
POST /replan
POST /sessions/{id}/complete
POST /sessions/{id}/reschedule
GET  /analytics
GET  /memory/{topic_id}
POST /calibrate
GET  /snapshot
GET  /export/snapshot.json
GET  /export/sessions.csv
```

## Run locally

```bash
pip install -e '.[all]'
uvicorn planner.api:app --reload
pytest -q
```

## Docker

```bash
docker compose up --build
```

The planner stores its SQLite database at `/data/study_planner.db` inside the container volume.

## Design principles

The scheduling engine is intentionally interpretable. Optimization is optional, hard constraints are surfaced instead of silently violated, and real usage data is fed back into memory scheduling and complexity estimation rather than treated as static inputs.
