# Sprint 21 — Gate Assessment Foundation Code Review

**Status:** PASS  
**Date:** 2026-10-07  
**PR:** #19 — Sprint 21: Gate Assessment Foundation  
**Reviewed implementation commit:** `4d8ca8b35faf40bba8fa39571f946228df5943e4`  
**Stage acceptance record commit:** `6bf01f35904051367ce60eb6ed0df8ab04ad8501`  
**Latest verified CI before this review record:** Run `37602156114` — SUCCESS  
**Latest verified Stage Acceptance before this review record:** Run `37602156083` — SUCCESS

## Review scope

- canonical Gate A–E vocabulary and versioned GateDefinition registry;
- GateAssessment state machine and transition guards;
- Flag-Profile-owned public Current Profile snapshot contract;
- Gate-owned immutable point-in-time ProfileSnapshot;
- Claim → Pattern → Evidence → Interpretation → Observation → Source lineage;
- Open Human Review idempotency and optimistic concurrency;
- final Human Gate Decision and exact Definition/Snapshot pinning;
- Domain Event + transactional Outbox publication;
- remediation / reassessment lifecycle;
- Candidate-safe projection and Assessor-only lineage;
- tenant / subject scoping and OIDC authorization;
- bounded-context isolation and absence of cross-context foreign keys;
- absence of numeric thresholds, scores, auto-evaluators and automatic progression;
- absence of CapabilityClaim, ResponsibilityRecommendation, Flag Board or Appointment mutation;
- Live OIDC operational UI and Stage acceptance evidence.

## Findings

### CR-21-001 — Assessor UI initially refetched the Candidate-only projection after Human decision

**Severity:** Blocking before merge  
**Status:** RESOLVED

The first Assessor UI wiring called both the Assessor Gate query and the Candidate-only
`/api/v1/me/gate-assessments` query after a Human Gate decision.

The backend correctly rejected that Candidate endpoint when called with an Assessor token
with `403`. The Human decision itself had already succeeded, but the frontend entered an
error state before rendering the completed decision.

Resolution:

- the Assessor success path now refetches only the Assessor Gate query;
- Candidate projection remains Candidate-role-only;
- Live OIDC E2E verifies the Human decision is rendered as completed;
- Candidate login separately verifies the safe projection and receives `403` on Assessor-only Gate endpoints.

Resolved in commit `93310f98c5e00a76f4aca94af419bcad1a013325`.

### CR-21-002 — Gate bounded-context isolation

**Status:** PASS

Gate Assessment owns its own persistence for:

- GateDefinition and immutable GateDefinitionVersion;
- GateAssessment;
- Gate-owned ProfileSnapshots and copied lineage references;
- Gate Review and Human decisions;
- Remediation, Reassessment and Reassessment decisions.

Review confirmed there is no direct import from Gate Assessment to:

- `app.flag_profile.models`;
- Pattern persistence;
- Evidence persistence.

Gate reads Current Profile only through the Flag-Profile-owned public contract and adapter.
All Gate foreign keys remain inside the `gate_assessment` schema. IDs copied from Profile,
Pattern and Evidence lineage are opaque references, not cross-context foreign keys.

### CR-21-003 — Immutable historical decision context

**Status:** PASS

Every consequential Review pins:

- exact GateDefinitionVersion;
- exact Gate ProfileSnapshot version;
- exact Current CapabilityClaim versions;
- Pattern references;
- Evidence / Interpretation / Observation / Source lineage.

Database triggers reject UPDATE or DELETE of immutable Gate snapshot history.
Review and decision history is append-only.

Reassessment creates a fresh ProfileSnapshot and does not rewrite the original Review
snapshot or original decision.

### CR-21-004 — Human-only consequential decisions

**Status:** PASS

Initial final Gate Review permits only:

- `PASS_CONFIRMED`;
- `FAIL`.

Reassessment permits only:

- `PASS`;
- `FAIL`.

Both paths require:

- an accountable Human reviewer;
- non-empty rationale;
- expected GateAssessment version;
- exact GateDefinitionVersion;
- exact ProfileSnapshot ID and version.

No AI, System or Event path can directly produce `PASS`, `PASS_CONFIRMED` or `FAIL`.

### CR-21-005 — Missing Evidence is not Gate failure

**Status:** PASS

Sprint 21 introduces no automatic evaluator that maps an Evidence gap to `FAIL`.

Stage acceptance proves a Human `PASS_CONFIRMED` can coexist with a non-empty
`next_evidence_needed` field.

Therefore:

**INSUFFICIENT EVIDENCE ≠ GATE FAILURE**

remains enforced.

### CR-21-006 — No invented scoring or automatic progression

**Status:** PASS

Review found no:

- numeric Gate threshold;
- weighted average;
- readiness score;
- overall score;
- automatic recovery;
- auto-pass / auto-fail evaluator;
- automatic Gate progression.

Gate requirements are the canonical versioned A–E definitions derived from repository
documentation and remain qualitative Human-review inputs.

### CR-21-007 — Event / Outbox integrity

**Status:** PASS

`gate.review_completed.v1` is recorded with:

- PERSON actor;
- exact reviewer identity;
- decision state;
- GateAssessment lineage;
- exact ProfileSnapshot ID/version;
- exact GateDefinitionVersion.

Domain Event and Outbox are created transactionally with the decision. Stage acceptance
verifies publication, zero event/outbox mismatches, zero non-human review events and
matching persisted decision lineage.

### CR-21-008 — Idempotency and concurrency

**Status:** PASS

Open Review and final decision are both:

- tenant scoped;
- optimistic-version guarded;
- row-lock protected where the state transition is applied;
- idempotent under retry.

Stage acceptance replays both commands and verifies no duplicate Review, Snapshot,
Decision, Domain Event or Outbox row is created.

Recovery/reassessment history has its own idempotency boundaries and remains append-only.

### CR-21-009 — Candidate visibility boundary

**Status:** PASS

Candidate Gate projection exposes only:

- `gate_code`;
- `gate_name`;
- `status`;
- `evidence_gaps`;
- `remediation_status`.

It does not expose reviewer identity, rationale, ProfileSnapshot IDs/versions,
Interpretation IDs, source references, internal risk mechanics or Assessor-only lineage.

Live OIDC E2E verifies:

- Candidate receives the safe projection;
- Assessor-only lineage is not rendered to Candidate;
- Candidate receives `403` on Assessor Gate endpoints.

### CR-21-010 — No downstream authority mutation

**Status:** PASS

Sprint 21 does not directly mutate or create:

- CapabilityClaim;
- ResponsibilityRecommendation;
- Flag Board decision;
- Appointment.

It also does not activate a Parcham AI runtime and introduces no external AI provider.

Stage acceptance verifies zero downstream Gate/Responsibility decision events from the
accepted Gate Review path.

### CR-21-011 — Recovery / reassessment governance

**Status:** PASS

The accepted recovery path remains:

**FAIL → REMEDIATION → REASSESSMENT → PASS / FAIL**

Review confirms:

- remediation requires a Human-backed FAIL;
- reassessment pins a new Current Profile snapshot;
- final reassessment decision is Human-only;
- prior snapshots and decisions remain historical and immutable;
- recovery does not mutate Profile, Responsibility, Flag Board or Appointment;
- no score, threshold or automatic recovery rule exists.

### CR-21-012 — Operational verification

**Status:** PASS

CI Run `37602156114` on `6bf01f35904051367ce60eb6ed0df8ab04ad8501` passed:

- backend lint;
- backend type check;
- backend unit/API/architecture tests;
- clean migrations;
- development seed;
- OpenAPI export;
- frontend generated API types;
- frontend type check;
- frontend unit tests;
- frontend build;
- Live OIDC browser E2E.

Stage Acceptance Run `37602156083` also passed on the same HEAD and produced
`stage-acceptance-evidence` artifact ID `11473651214`,
digest `sha256:4205925fd421ec4c69c24fc37572a2fdd9c4fc12f9e4d17697ee2cefa6f5d11f`.

The implementation commit accepted by Stage is
`4d8ca8b35faf40bba8fa39571f946228df5943e4`; the only commit between that
implementation and `6bf01f…` is the Stage acceptance document itself.

## Review conclusion

No blocking findings remain.

**Sprint 21 — Gate Assessment Foundation: CODE REVIEW PASS**

This review does **not** authorize merge or Production deployment. PR #19 must remain
Draft/Open and unmerged until the user explicitly instructs otherwise.
