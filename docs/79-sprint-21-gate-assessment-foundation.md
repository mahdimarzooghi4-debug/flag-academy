# 79 — Sprint 21: Gate Assessment Foundation

**Status:** IN PROGRESS  
**Date:** 2026-10-06  
**Base:** Sprint 20 — Flag Profile Capability Claim Foundation: ACCEPTED

## Goal

Establish the first auditable Gate Assessment bounded context so Parcham can review a Candidate's readiness against a versioned Gate Definition without reducing readiness to a score, without allowing AI/System/Event to pass or fail a Gate, and without letting later Profile changes rewrite the facts used for an earlier consequential decision.

The target chain is:

**Current Flag Profile → Immutable ProfileSnapshot → GateAssessment → Open Review → Human Lineage Review → Accountable Gate Decision**

Sprint 21 is a governance foundation. It does not implement ResponsibilityRecommendation, Flag Board, Appointment, automatic progression, or Parcham AI decision authority.

## Business contract

### Official Gate Matrix

The Gate catalog is exactly the existing FINAL matrix:

- Gate A — Foundation Readiness
- Gate B — Product Judgment Readiness
- Gate C — Real Project Readiness
- Gate D — Ownership Trial Readiness
- Gate E — Flag Board

Gate definitions are versioned business definitions. Existing questions/requirements in `docs/27-prerequisite-gates-evidence-graph.md` remain authoritative.

Sprint 21 MUST NOT invent:
- numeric thresholds;
- weighted averages;
- overall readiness score;
- automatic PASS/FAIL;
- automatic progression from course completion;
- automatic Gate state inference from a single Capability Claim;
- automatic Gate state inference from AI output.

### GateAssessment identity

Conceptual key:

**person × gate_definition_version × organization_context**

A Candidate may have a living GateAssessment for a Gate, while every consequential review/decision remains auditable in history.

### Authoritative Gate state

Per DEC-405 / DEC-628:

**UNPROVEN → PASS → AT_RISK → REVIEW_REQUIRED → PASS_CONFIRMED / FAIL**

If FAIL:

**FAIL → REMEDIATION → REASSESSMENT → PASS / FAIL**

Rules:

- `UNPROVEN` means readiness has not been established; it is not failure.
- `AT_RISK` is a risk signal, not a failure decision.
- `REVIEW_REQUIRED` requires Human Review before PASS confirmation or FAIL.
- `PASS_CONFIRMED` is an accountable review outcome, not an automatic result.
- Gate is living; historical decisions are append-only/auditable.
- a single incident may open review but cannot directly create FAIL.
- `INSUFFICIENT EVIDENCE` and `GATE FAILURE` remain conceptually distinct. Sprint 21 must never encode missing Evidence as FAIL.

### Consequential snapshot rule

Opening a consequential Gate Review pins an immutable `ProfileSnapshot`.

The snapshot must preserve enough facts to answer later:

> What exact Profile facts and lineage were available when this Gate Review was opened?

At minimum:
- organization_context_id;
- subject_person_id;
- snapshot version/time;
- source FlagProfile IDs/versions;
- exact CapabilityClaim IDs/versions;
- Claim state/level/proven scope/recency;
- Gate-relevant Pattern references;
- Claim lineage references sufficient to reach Pattern → Evidence → Interpretation → Observation → Source.

The Gate decision reads the snapshot, not the mutable Current Profile.

Later Profile changes:
- may trigger a future reassessment;
- must not rewrite the prior Gate review;
- must not silently alter a prior Gate decision.

### Human accountability

Only an authorized accountable Human Reviewer may complete a `REVIEW_REQUIRED` decision to:
- `PASS_CONFIRMED`
- `FAIL`

Every decision requires:
- reviewer identity;
- rationale;
- exact GateAssessment version;
- exact GateDefinition version;
- exact ProfileSnapshot ID/version;
- timestamp;
- idempotency;
- trace/correlation context.

No AI/System route may directly call a pass/fail mutation.

### Candidate transparency and secrecy

Candidate-visible Gate projection may expose:
- Gate code/name;
- current safe Gate status;
- evidence gaps / next evidence needed when policy permits;
- remediation status when applicable.

Candidate-visible projection MUST NOT expose:
- hidden assessment triggers;
- reviewer-private rationale;
- internal risk trigger mechanics;
- confidential source lineage;
- other reviewers' private notes;
- internal AI/system proposals.

## Technical contract

### Bounded context

Sprint 21 introduces a dedicated **Gate Assessment** bounded context.

Gate Assessment owns:
- GateDefinition + GateDefinitionVersion;
- GateAssessment;
- GateReview history;
- GateRemediation/Reassessment state needed by the aggregate;
- immutable Gate-facing ProfileSnapshot references/snapshots;
- Gate read models.

Gate Assessment MUST NOT:
- import Flag Profile persistence models/repositories directly;
- use cross-context foreign keys to `flag_profile`, `patterns`, `evidence`, Mission Runtime, or Curriculum internals;
- mutate CapabilityClaim;
- mutate BehaviourPattern or Evidence;
- create ResponsibilityRecommendation;
- create Flag Board or Appointment decisions;
- allow AI/System/Event direct PASS/FAIL.

Cross-context integration must use public contracts and/or versioned events.

### Flag Profile contract dependency

Flag Profile remains owner of Current CapabilityClaim truth.

Sprint 21 requires a **Flag-Profile-owned public snapshot contract** that can provide:
- subject/org scoped Current Flag Profile;
- exact claim versions/facts;
- durable Claim lineage references required for Gate review.

Gate Assessment may snapshot those contract facts into its own persistence, but it may not query `flag_profile.*` tables directly.

### Persistence

Use a dedicated `gate_assessment` PostgreSQL schema.

Vital business state remains relational/queryable, not hidden only in JSONB.

Expected foundation tables include:
- `gate_definitions`
- `gate_definition_versions`
- `gate_assessments`
- `gate_profile_snapshots`
- `gate_profile_snapshot_claims`
- `gate_snapshot_pattern_refs`
- review/decision history tables as required by the aggregate

Only intra-context foreign keys are allowed.

### Mutation contract

Public API remains aligned with DEC-557:

- `GET /api/v1/gate-assessments/{id}`
- `POST /api/v1/gate-assessments/{id}/open-review`
- `POST /api/v1/gate-assessments/{id}/decisions`
- `POST /api/v1/gate-assessments/{id}/start-remediation`
- `POST /api/v1/gate-assessments/{id}/reassess`

Creation/discovery endpoints may be added only if required by the implementation and must remain business commands rather than direct state PATCH.

Every mutation command must be:
- tenant scoped before lock;
- version checked;
- idempotent;
- actor audited;
- traceable;
- fail-closed on stale ProfileSnapshot/current-state assumptions.

### Event contract

Existing core event names remain authoritative:
- `gate.at_risk.v1`
- `gate.review_completed.v1`
- `profile.snapshot_created.v1`

Domain mutation and Outbox write must be in the same transaction.

Event payloads are facts, not aggregate dumps, and contain IDs rather than unnecessary PII.

### Initial automation boundary

Signals may:
- propose/open risk review;
- surface contradictions/gaps;
- prepare explainable context.

Signals may not:
- decide PASS;
- decide FAIL;
- invent thresholds;
- mutate Current CapabilityClaim;
- assign Responsibility.

The previously selected Parcham AI baseline is not invoked by Sprint 21 foundation.

## Scrum / Product Backlog

### P21-01 — Gate domain vocabulary and architecture guards
- exact GateAssessment state vocabulary;
- exact transition tests;
- no score/threshold fields;
- no AI/System direct decision path.

### P21-02 — Versioned Gate Definition registry
- Gate A–E canonical codes/names/questions;
- immutable versions;
- no invented numeric threshold evaluator.

### P21-03 — Flag Profile public snapshot contract
- Flag Profile owns query;
- Gate consumes contract only;
- exact Current Claim versions + lineage refs;
- tenant/subject scoped.

### P21-04 — Gate persistence foundation
- dedicated schema;
- GateAssessment;
- immutable ProfileSnapshot;
- explicit snapshot claim/pattern lineage;
- no cross-context FK.

### P21-05 — Open Review command
- snapshot current Profile;
- transition to `REVIEW_REQUIRED` only through allowed state;
- optimistic concurrency;
- idempotency;
- accountable actor;
- no PASS/FAIL side effect.

### P21-06 — Assessor pre-decision read model
- Gate definition version;
- pinned ProfileSnapshot;
- Claim facts;
- supporting/contradictory lineage;
- evidence gaps/risks without score.

### P21-07 — Human decision contract
- `REVIEW_REQUIRED → PASS_CONFIRMED / FAIL`;
- full rationale;
- Human reviewer;
- stale-snapshot safety;
- event + outbox atomic.

### P21-08 — Remediation / Reassessment foundation
- `FAIL → REMEDIATION → REASSESSMENT → PASS / FAIL`;
- no automatic recovery;
- new assessment facts do not rewrite old decision history.

### P21-09 — Candidate-safe Gate projection
- allowlist only;
- no hidden triggers/private rationale/internal lineage.

### P21-10 — Assessor UI + Live OIDC E2E
- Current Profile → snapshot → open review → lineage inspection → accountable decision;
- Candidate visibility/security checks.

### P21-11 — Stage acceptance
Executable assertions for:
- exact Gate state vocabulary;
- immutable profile snapshot;
- full snapshot lineage;
- human-only PASS/FAIL;
- idempotent/versioned commands;
- published Gate events;
- no cross-context FK;
- zero direct AI/System Gate decision;
- zero CapabilityClaim/Responsibility/FlagBoard mutation caused by Gate decision.

## First implementation slice

The first code slice after this contract is intentionally smaller than the full Sprint:

**Gate domain vocabulary + GateDefinition registry foundation**

It will not yet:
- open a review;
- create a ProfileSnapshot;
- decide a Gate;
- emit Gate decision events;
- build UI.

## Definition of Done

Sprint 21 is accepted only when:

1. Gate A–E definitions are versioned and auditable.
2. GateAssessment uses the exact authoritative state machine.
3. a consequential review is pinned to an immutable ProfileSnapshot.
4. Claim/Pattern/Evidence lineage remains reconstructable from the snapshot.
5. PASS/FAIL requires explicit accountable Human Review.
6. missing Evidence is never silently converted to FAIL.
7. no AI/System/Event endpoint can directly pass/fail Gate.
8. Candidate projection is allowlisted and secrecy-safe.
9. Gate decision produces the defined Domain Event + Outbox atomically.
10. Gate does not mutate CapabilityClaim, Responsibility, Flag Board or Appointment.
11. CI and Live OIDC E2E are green.
12. Ephemeral Stage acceptance proves the invariants above.

## Out of scope

- ResponsibilityRecommendation;
- Flag Board;
- Appointment;
- automatic Gate policy evaluator;
- numeric thresholds/weights;
- overall readiness score;
- automatic progression;
- Parcham AI inference/training/dataset implementation;
- Production deployment.
