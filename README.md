# Med-School-Study-Planner

An adaptive, fairness-constrained medical study planner that turns curriculum, exams, student state, memory, workload, and real study performance into a continuously replanned schedule.

## Architecture

The planner is being migrated from a hand-weighted priority engine to a modular adaptive architecture:

```text
Curriculum graph
      ↓
Exam / blueprint model ─── Workload model ─── Student model
      │                         │                    │
      └─────────────────────────┼────────────────────┘
                                ↓
                       Utility-per-minute
                                ↓
                         CP-SAT scheduler
                                ↓
                         Daily / weekly plan
                                ↓
                         Study behaviour
                         ↙            ↘
                      BKT            FSRS
                         ↘            ↙
                         Student state
                                ↓
                              Replan
```

The application keeps the stable legacy APIs and data structures while introducing the new components behind explicit interfaces.

## Current adaptive components

- **Curriculum graph:** reusable school, USMLE, and personal hierarchies with knowledge-component mapping.
- **BKT-style mastery:** probability of learned knowledge, uncertainty, observations, and time-dependent forgetting.
- **FSRS adapter:** production memory scheduling behind a planner-owned interface; the rest of the code does not depend directly on the third-party API.
- **Workload estimation:** cold-start priors plus robust student-specific calibration from actual study duration.
- **Utility engine:** expected learning value per minute, with explicit exam urgency, mastery gap, retention gap, blueprint weight, workload, and block relevance components.
- **Adaptive CP-SAT:** daily capacity, rest-day protection, fairness floors, review capacity, exam-coverage constraints, and locked/preallocated work.
- **Activity model:** distinguishes learning, review, questions, recall, and mixed sessions.
- **Question pipeline:** persistent question attempts can update knowledge-component BKT state.
- **IRT layer:** a deliberately deferred 2PL analytical layer with an evidence gate; it does not infer student ability from tiny samples.
- **Readiness model:** knowledge, retention, coverage, practice, and deadline protection remain separate signals rather than being collapsed into an opaque exam score.
- **Evaluation harness:** deterministic synthetic students and baseline comparison between the legacy planner and adaptive CP-SAT.
- **Adaptive UI:** current study state, readiness, catch-up/rebalance, minimum-day mode, and learning-state export.
- **Adaptive session loop:** completing a session updates workload, FSRS, and mapped knowledge components before an optional replan.

## USMLE-first onboarding

The first-run experience includes a one-click **USMLE Step 1** preset. It uses the current official Step 1 content-outline system ranges as planning signals, stores their midpoints as blueprint weights, generates a starter curriculum, and immediately produces a weekly plan. USMLE itself describes these as ranges that can change, so the planner treats them as priorities rather than exact prediction of any individual form.

API endpoints:

```text
POST /setup/step1
GET  /presets/step1
```

Official source: https://www.usmle.org/exam-resources/step-1-materials/step-1-content-outline-and-specifications

## Adaptive API

The adaptive application entrypoint is `planner.v2_app:app`. It preserves every legacy route and adds:

```text
GET  /v2/status
GET  /v2/topic/{topic_id}/state
GET  /v2/topic/{topic_id}/why
POST /v2/topic/{topic_id}/review
POST /v2/topic/{topic_id}/question
POST /v2/topic/{topic_id}/session-observation
POST /v2/plan
POST /v2/workload/{topic_id}/calibrate
GET  /v2/readiness
```

A normal completed session flows through the legacy persistence path and then into the adaptive learning loop. Question-level evidence remains the preferred granular BKT signal; session-level evidence is deliberately coarser.

## Adaptive data model

V2 state is stored separately from the legacy topic schema so existing student data remains readable while the migration proceeds. The adaptive store contains:

```text
curriculum_nodes
knowledge_components
student_knowledge
student_fsrs
workload_estimates
question_attempts
planner_events
```

This keeps identity/curriculum data separate from learning-state and event data and provides a clean audit trail for future research analyses.

## Planning behaviour

The scheduler does not permanently equate "importance" with one scalar hand-tuned priority.

- **When will I forget it?** FSRS.
- **Have I learned it?** BKT-style mastery.
- **How long will it take me?** empirical workload estimation.
- **What matters for the assessment?** exam/blueprint metadata.
- **What can physically fit?** CP-SAT constraints.
- **How do we avoid starving subjects?** fairness constraints.
- **Why was this scheduled?** utility decomposition and machine-readable reasons.

The existing `/plan` and `/replan` APIs remain stable; the optimizer path now routes through the adaptive utility-driven engine.

## Testing

The repository includes regression tests for:

- legacy scheduling behaviour;
- adaptive curriculum, BKT, workload, and utility behaviour;
- FSRS round-trips;
- adaptive CP-SAT capacity, rest, preallocation, and exam constraints;
- persistent adaptive learning state;
- deterministic synthetic scheduler evaluation;
- readiness and IRT evidence guardrails;
- V2 API status/state/review behavior;
- frontend integrity and existing rescheduling/state-management tests.

GitHub Actions runs `compileall` and the full pytest suite on pushes and pull requests.

The development runtime used for these edits cannot resolve `github.com`, so local execution from this environment was not possible. CI remains the authoritative executable validation path.

## Run locally

```bash
pip install -e '.[all]'
uvicorn planner.v2_app:app --reload
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
