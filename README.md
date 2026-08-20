# Med-School-Study-Planner

An adaptive, fairness-constrained medical study planner that turns curriculum, exams, mastery, memory state, and real study performance into a continuously replanned schedule.

## USMLE-first onboarding

The first-run experience includes a one-click **USMLE Step 1** preset. It uses the current official Step 1 content-outline system ranges as planning signals, stores their midpoints as blueprint weights, generates a starter curriculum, and immediately produces a weekly plan. USMLE itself describes these as ranges that can change, so the planner treats them as priorities rather than exact prediction of any individual form.

API endpoints:

```text
POST /setup/step1
GET  /presets/step1
```

Official source: https://www.usmle.org/exam-resources/step-1-materials/step-1-content-outline-and-specifications

## Pipeline

`Curriculum + Exams + Profile -> Blueprint/Complexity + Priority -> Weekly fairness + memory/review -> Rule scheduler / CP-SAT -> Study sessions -> Completion/performance -> Memory + mastery + time calibration -> Replan`

## Implemented

- Subject, Topic, Exam, StudySession, and UserProfile domain model.
- Official USMLE Step 1 starter blueprint with preloaded system priorities.
- Complexity scoring from volume, cognitive load, and personal difficulty.
- Priority scoring from urgency, complexity, mastery gap, normalized exam weighting, and review state.
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
- Beginner-focused browser UI for Today, Week, Curriculum, Exams, Insights, session completion, and planner settings.
- JSON snapshot and CSV session exports.
- Dockerfile + Compose deployment with persistent SQLite storage.
- GitHub Actions CI with compile checks and full test suite.
- GitHub Pages frontend + Render/FastAPI backend deployment path.

## Run locally

```bash
pip install -e '.[all]'
uvicorn planner.api:app --reload
pytest -q
```

The local UI is available at `http://127.0.0.1:8000/`.

## GitHub Pages frontend

The static frontend deploys to:

`https://virelion-biotech.github.io/Med-School-Study-Planner/`

Create a GitHub repository variable named `PLANNER_API_BASE` containing the public FastAPI URL. The Pages workflow injects it during deployment.

## Backend deployment

A Render deployment definition is provided in `render.yaml`. The backend runs FastAPI with OR-Tools, exposes `/health`, supports GitHub Pages through CORS, and persists SQLite data on the configured disk.

## Docker

```bash
docker compose up --build
```

The planner stores its SQLite database at `/data/study_planner.db` inside the container volume.
