# P22-06 — Human Promotion Governance

**Status:** IMPLEMENTED — acceptance requires green CI on this record  
**Date:** 2026-10-07  
**Sprint:** 22 — Parcham AI Foundation  
**PR:** #20 — Draft/Open/Unmerged

## Goal

Add the explicit Human Promotion Governance boundary after Offline Evaluation:

**SUCCEEDED Evaluation Run + Immutable Evaluation Result + Exact Model Version →
Explicit Human Reviewer Decision → Immutable Promotion Authorization Record**

This slice records authorization evidence only. It does not activate a runtime, alter routing,
change a production model pointer, deploy a model, or perform any consequential product
decision.

## Human-only decision contract

The application command is `RecordHumanPromotionDecision`.

It accepts:

- organization context;
- exact Model Version ID;
- exact Evaluation Run ID;
- Human reviewer ID;
- rationale;
- decision;
- target environment;
- optional prior active Model Version ID;
- trace ID.

It intentionally has no generic actor type or SYSTEM actor field. The event actor is always
recorded as `PERSON` using the Human reviewer ID.

Decision vocabulary remains exactly:

- `APPROVED`
- `REJECTED`

No score, threshold, benchmark winner rule, or model-selection algorithm is introduced.

## Evaluation and Model lineage

Before a decision can be recorded, the service requires:

- the Model Version to belong to the requested organization context;
- the Evaluation Run to belong to the requested organization context;
- the Evaluation Run to reference the exact same Model Version;
- the latest Evaluation state to be exactly `SUCCEEDED`;
- the Evaluation Run to have its immutable Evaluation Result.

A failed, running, requested, missing-result, mismatched-model, or cross-organization
Evaluation cannot be promoted.

If `prior_active_model_version_id` is supplied, it must resolve to a Model Version in the
same organization context. P22-06 does not claim to verify runtime-active status because
runtime activation is explicitly outside Sprint 22.

## Idempotency and concurrency

The existing immutable registry already defines one Promotion Decision per:

`evaluation_run_id + target_environment`

P22-06 serializes this identity with a PostgreSQL advisory transaction lock.

An exact retry returns the existing immutable decision.

A retry that changes any material decision semantics fails closed, including changes to:

- Model Version;
- reviewer;
- rationale;
- APPROVED/REJECTED decision;
- prior active Model Version reference.

No internal transaction commit is performed by the service.

## Database enforcement

Migration `0029_human_model_promotion_governance.py` adds an independent PostgreSQL
guard for Promotion Decision insertion.

The migration refuses to proceed if legacy Promotion Decisions already exist because
P22-06 will not invent missing lineage validation for historical rows.

PostgreSQL independently verifies on every new Promotion Decision:

- Evaluation Run exists;
- Model Version exactly matches the Evaluation Run;
- Model Version organization matches the Evaluation organization;
- latest Evaluation state is `SUCCEEDED`;
- immutable Evaluation Result exists;
- optional prior active Model Version exists and belongs to the same organization.

The existing immutable UPDATE/DELETE trigger continues to protect Promotion Decision
history.

## Event and outbox

A first accepted decision records:

`ai.model_promotion_decision_recorded.v1`

as Domain Event + transactional Outbox evidence.

The event records:

- Promotion Decision ID;
- exact Model Version ID;
- exact Evaluation Run ID;
- Human reviewer ID;
- APPROVED/REJECTED decision;
- target environment;
- optional prior active Model Version ID;
- `authorization_only=true`;
- `runtime_activation=false`.

The event does not invoke any runtime, deployment, routing policy, Gate, Profile,
Responsibility, Flag Board, or Appointment mutation.

## CI acceptance

CI runs `backend/scripts/ai_human_promotion_acceptance.py` after Offline Evaluation
acceptance.

The acceptance proves:

- an explicit Human reviewer is recorded;
- the exact Model Version is pinned;
- only a successful Evaluation Run can be decided;
- immutable Evaluation Result is required;
- exact retry is idempotent;
- conflicting retry fails closed;
- PostgreSQL independently rejects promotion of a failed Evaluation Run;
- APPROVED is authorization evidence only;
- no automatic promotion or runtime activation is implemented.

## Explicit exclusions

P22-06 adds no runtime activation, active-model pointer, production route, routing policy,
deployment, external AI provider, external model API, external inference endpoint, API key,
provider token, automatic promotion, automatic pass/fail policy, threshold, weighted score,
benchmark winner rule, Gate decision, CapabilityClaim mutation, ResponsibilityRecommendation
mutation, Flag Board decision, or Appointment action.

## Result

When full CI is green on this implementation, **P22-06 — Human Promotion Governance is
COMPLETE**.

The next planned slice is **P22-07 — Admin Read Models / UI**.
