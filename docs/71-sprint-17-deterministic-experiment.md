# 71 — Sprint 17: Deterministic Experiment Runtime

**Status:** IN PROGRESS  
**Date:** 2026-10-05

## Goal

Close the final currently unimplemented Mission Runtime action gap by making `RUN_EXPERIMENT` executable as a bounded, pre-registered, Mission-Version-pinned experiment whose result is produced by the Mission Engine without automatic interpretation.

## Product boundary

Experiment execution reduces uncertainty inside Canonical Simulation State. It does **not** create Evidence, prove Capability, interpret causality for the Candidate, or mutate Profile/Gate state.

**Experiment Result ≠ Evidence**  
**Experiment Result ≠ Proven Capability**  
**Experiment Result ≠ Automatic Interpretation**

In Assessment Mode, the Engine may expose deterministic Control/Treatment measurements, noise/context and events. Interpretation and subsequent decision remain the Candidate's responsibility.

## FINAL decision alignment

The runtime contract follows:

- DEC-195 — Metrics & Experimentation reduces uncertainty about action/result relationships.
- DEC-196 — Outcome → Behavior → Metric → Baseline → Target → Guardrails → Intervention → Measurement → Interpretation → Decision.
- DEC-200 — Experiment Contract is frozen before Result.
- DEC-201 — Experiment method is not assumed to be A/B-only.
- DEC-204 — Assessment AI must not interpret the Result for the Candidate.
- DEC-206 — Experiment requires User Risk / Ethical Review.
- DEC-367/378 — Mission Engine produces Observation; Evidence interpretation is downstream.

## Runtime contract

A Mission Version may expose `experiment_options`. Each option pins:

- `code`
- Candidate-visible `label`
- `method`
- pre-result `contract`:
  - hypothesis
  - population
  - intervention
  - control/comparison
  - primary metrics
  - secondary metrics
  - guardrails
  - baseline
  - expected effect
  - decision rule
  - duration/stopping rule
  - known risks
  - ethical review
- Engine-owned deterministic `result`:
  - control measurements
  - treatment measurements
  - noise/context
  - observed events
- deterministic `world_effect`
- Engine response

Candidate submits only:

- `experiment_code`
- rationale
- expected World State version
- idempotency key

Candidate cannot submit or rewrite the frozen contract, Result, Dataset, world patch, Evidence claim, Capability score or Gate state.

## Invariants

For every accepted experiment:

1. Experiment contract must exist before execution and satisfy all mandatory DEC-200 fields.
2. Ethical review is mandatory.
3. Result must be Engine-owned and resolved from the exact pinned Mission Version.
4. Result payload is descriptive measurement only; no `interpretation`, `verdict`, `evidence_strength`, `capability_score` or Gate/Profile mutation is allowed.
5. World mutation may record experiment execution/result state but may not write Evidence/Profile/Competency/Gate namespaces.
6. `mission.accountability_owner` remains `CANDIDATE`.
7. Candidate receives factual `EXPERIMENT_RESULT_OBSERVED`; no Evidence entity is created.

## Execution

1. Lock Mission Instance.
2. Enforce RUNNING and World optimistic concurrency.
3. Resolve experiment only from the pinned Mission Version.
4. Validate frozen contract completeness and ethical review.
5. Validate Result as descriptive Engine-owned data with forbidden interpretation keys rejected.
6. Apply Engine-owned world effect through reserved namespace guard.
7. Enforce Candidate accountability invariant.
8. Emit `experiment.requested`.
9. Emit `experiment.completed` with candidate-safe pre-registered contract/result projection.
10. Persist factual `EXPERIMENT_RESULT_OBSERVED`.
11. Run scheduled-effect cancellation.
12. Run state-triggered fixed-point evaluation.
13. Record internal `mission.experiment_processed.v1`.

## Acceptance scenario

The recovery Mission exposes a bounded canary experiment before resource allocation:

- hypothesis: a limited rollback canary will reduce incident error rate without breaching the customer-impact guardrail;
- population: 10% recovery traffic;
- intervention: controlled rollback canary;
- comparison: current degraded path;
- primary metric: error rate percent;
- guardrail: customer-impact percent;
- baseline: error rate 13%;
- expected effect and decision rule are pre-registered;
- duration/stopping rule is fixed;
- ethical review declares no sensitive-data or protected-population exposure.

Engine-owned deterministic result:

- control error rate remains 13%;
- treatment error rate is 5%;
- guardrail remains within the pre-registered limit;
- noise/context and observed event are exposed separately;
- Engine does not label the result success/failure and does not recommend a decision.

Expected runtime result:

- `mission.experiment_status=COMPLETED`;
- factual result is candidate-visible;
- `mission.accountability_owner=CANDIDATE`;
- no raw mutation rule or hidden Result metadata leaks;
- later ALLOCATE_RESOURCE / DELEGATE / ESCALATE / DECIDE remains operational;
- Candidate remains `UNPROVEN`.

## Out of scope

- Evidence Engine
- Experiment Memory beyond this Mission Runtime observation/history
- statistical inference engine
- AI interpretation
- automatic success/failure verdict
- Profile/Gate mutation
- Candidate-authored arbitrary experiment/result patches
