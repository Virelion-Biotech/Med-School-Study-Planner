# Med-School Study Planner — Platform Architecture

## Runtime flow

```text
Curriculum sources
  -> versioned curriculum graph
  -> cross-curriculum mappings
  -> canonical knowledge components
  -> student state (BKT + FSRS + question evidence)
  -> utility-per-minute activity selection
  -> constrained CP-SAT allocation
  -> Topic-level study sessions
  -> observed behavior / question attempts
  -> state update
  -> adaptive replan
```

## Canonical state

A curriculum node describes where a concept is taught. A knowledge component (KC)
describes the underlying skill/concept. Student state belongs to the KC rather than
to every curriculum representation. This allows a school topic, USMLE topic, and
personal topic to share evidence without duplicating mastery or memory state.

Topics remain the execution unit for backward compatibility and user-facing
sessions.

## Scheduling layers

1. **Utility engine** estimates expected learning value per minute.
2. **Activity selection** chooses learning, review, questions, recall, or mixed work.
3. **CP-SAT** allocates time subject to capacity, deadlines, fairness, review, rest,
   and session-size constraints.
4. **Session splitter** converts allocations into executable sessions.

## Adaptive evidence

- BKT estimates knowledge acquisition and uncertainty.
- FSRS models review/retention behavior.
- Question evidence updates the student state.
- IRT remains evidence-gated and is intended for sufficiently large response sets.

The system must not present population priors as personalized certainty.

## Data provenance

Curriculum imports are normalized and validated before becoming versioned snapshots.
Snapshots carry source, version, fingerprint, and validation diagnostics. Existing
student state is not silently duplicated when multiple curriculum sources map to the
same KC.

## Synchronization

Workspace mutations use optimistic revisions. A matching revision can be applied;
a stale revision requires reconciliation. Three-way session reconciliation merges
disjoint edits and leaves same-session conflicts explicit. Plan fingerprints provide
a deterministic representation for stale-plan detection.

## Quality gates

The repository contains unit tests, simulation/ablation evaluation, calibration
metrics, regression gates, and a fast platform smoke test. Correctness invariants
are intentionally separated from performance claims: CI should reject impossible
plans or materially invalid model outputs without hard-coding an unsupported claim
that one scheduling algorithm must always outperform another.

## End-to-end acceptance scenario

A release should be able to exercise:

1. create/identify a student workspace;
2. import and validate curriculum;
3. map curriculum nodes to KCs;
4. generate a canonical adaptive plan;
5. complete a study session;
6. submit question evidence;
7. update BKT/FSRS state;
8. replan within remaining capacity;
9. detect a stale second-device revision;
10. reconcile independent edits automatically;
11. surface true conflicts explicitly;
12. preserve an auditable plan fingerprint and workspace revision.
