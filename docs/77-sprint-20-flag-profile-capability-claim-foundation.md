# 77 — Sprint 20: Flag Profile Capability Claim Foundation

**Status:** IN PROGRESS  
**Date:** 2026-10-06

## Goal

Establish the first auditable Flag Profile update path so a human-reviewed Behaviour Pattern can propose and, after the required Human Review, apply a Capability Claim without allowing Pattern, Evidence, AI or raw events to mutate the current profile directly.

The first executable chain is:

**Reviewed Behaviour Pattern → Profile Update Case → Human Review → Apply → Capability Claim → `profile.claim_changed.v1`**

This Sprint is the first implementation step after Sprint 19 Pattern Engine Foundation.

## FINAL decision alignment

This Sprint implements the already-final architecture in:

- DEC-390 — Evidence Engine chain continues Accepted Evidence → Pattern → Profile Claim → Gate Review → Responsibility Recommendation.
- DEC-392 — CapabilityClaim, CompetencyClaim, GateAssessment and ProfileSnapshot are first-class domain entities.
- DEC-403 — CapabilityClaim stores State, Level, Proven Scope, Supporting/Contradictory Patterns, Recency, Claim Confidence, Reviewer and Next Evidence Needed; Level and Scope are independent.
- DEC-404 — Promotion/Downgrade is Evidence-based and Human-reviewed; no numeric threshold or automatic progression rule may be invented.
- DEC-406 — Candidate has Profile Transparency while Assessment Secrecy remains protected.
- DEC-409 — Flag Profile is living; immutable ProfileSnapshot belongs to consequential decision points and is not introduced casually.
- DEC-410 — Consequential Profile updates follow Profile Update Proposal → Human Review → Apply.
- DEC-416 — No claim without full lineage: Claim → Pattern → Evidence → Interpretation → Observation → Source.
- DEC-419 — No claim without lineage; no Gate failure without accountable Human Review; no responsibility assignment from black-box score.
- DEC-547 — Flag Profile API is permission-sensitive, has no overall score, and Claim lineage must be queryable end to end.
- DEC-556 — Profile Update only comes from ProfileUpdateCase approve/reject or explicitly defined auto-eligible developmental path; direct PATCH on Flag Profile is forbidden.
- DEC-564 — Aggregate persistence is versioned/auditable; JSONB is not used for vital business state.
- DEC-565 — Domain Event + Outbox + Inbox are canonical persistence contracts.
- DEC-567 — `profile.claim_changed.v1` is a core event contract.
- DEC-572 — stale commands return `409 VERSION_CONFLICT`; clients refresh rather than blind-retry.
- DEC-625 through DEC-627 — approved governed data will eventually enter Parcham AI automatically and quickly, but Sprint 20 does not implement Automatic Dataset Builder, Training or Model Promotion.

## Authoritative Claim vocabulary

The existing technical model defines CapabilityClaim state exactly as:

- `UNPROVEN`
- `EMERGING`
- `DEMONSTRATED`
- `PROVEN`

Capability level is exactly:

- `L0`
- `L1`
- `L2`
- `L3`
- `L4`

Level and Proven Scope are independent.

Sprint 20 MUST NOT invent:
- numeric promotion thresholds;
- score-based progression;
- automatic Level inference;
- automatic Proven Scope inference;
- a new Claim state;
- Gate state from Capability Claim state.

## Bounded Context

Sprint 20 introduces/extends the **Flag Profile** bounded context.

Pattern Engine remains the owner of Reviewed Behaviour Pattern and its lineage.

Flag Profile owns:
- ProfileUpdateCase;
- CapabilityClaim;
- current Flag Profile projection for Capability Claims;
- Claim lineage projection;
- Profile update Human Review history.

Flag Profile MUST NOT:
- import Pattern persistence models/repositories;
- use cross-context foreign keys to `patterns`, `evidence` or Mission schemas;
- mutate Pattern, Evidence or Mission Runtime state;
- create or decide GateAssessment;
- create ResponsibilityRecommendation;
- mark any Capability Claim from a raw Observation or unreviewed Evidence.

Cross-context integration must use a Pattern-owned public contract and/or versioned event contract.

## Pattern intake

Canonical intake event is `pattern.updated.v1`.

The event is a notification that a Reviewed Behaviour Pattern exists. It is not sufficient by itself to invent a Capability Claim.

On intake, Flag Profile may obtain the reviewed Pattern's canonical lineage only through a Pattern-owned public contract.

The resulting profile proposal must preserve references/snapshots required to prove:

**Claim → Reviewed Pattern → Evidence relationship → Accepted Evidence snapshot → Interpretation → Observation → Source**

Duplicate `pattern.updated.v1` delivery must not duplicate a ProfileUpdateCase or Claim lineage membership.

## ProfileUpdateCase

ProfileUpdateCase is the only mutation gateway to the current Capability Claim in Sprint 20.

Canonical state vocabulary from the existing domain model:

**PROPOSED → REVIEW_REQUIRED / AUTO_ELIGIBLE → APPROVED → APPLIED**

Sprint 20 implements only the accountable Human Review path:

**PROPOSED → REVIEW_REQUIRED → APPROVED → APPLIED**

`AUTO_ELIGIBLE` is reserved but not operationalized in this Sprint because no finalized policy currently defines which developmental transitions are safe for automatic apply.

A ProfileUpdateCase must contain at least:

- `organization_context_id`
- `subject_person_id`
- target capability reference
- source Reviewed Pattern references
- supporting Pattern references
- contradictory Pattern references
- current Claim snapshot/ref, if one exists
- proposed Claim state
- proposed Level
- proposed Proven Scope
- claim recency facts
- claim confidence as a qualitative reviewed field
- Next Evidence Needed
- rationale
- proposer identity
- reviewer identity after review
- version
- timestamps
- idempotency metadata for creation/review/apply commands
- lineage sufficient for DEC-416

No ProfileUpdateCase may be built from:
- unreviewed PatternCandidate;
- rejected Evidence;
- raw Observation directly;
- hidden Candidate-inaccessible Assessment secrets as Candidate-visible output.

## CapabilityClaim

Conceptual key:

**person + capability + track + organization context**

Sprint 20 Current CapabilityClaim stores:

- Claim State;
- Level;
- Proven Scope;
- Supporting Pattern refs;
- Contradictory Pattern refs;
- Evidence Recency;
- Claim Confidence;
- Reviewed At;
- Reviewed By;
- Next Evidence Needed;
- version;
- lineage to the applied ProfileUpdateCase.

A Claim is current profile state, not a deletion/rewrite of historical evidence or prior claims.

Every applied change must remain auditable.

## Claim transition policy

Sprint 20 deliberately contains no engine that decides whether a person deserves a higher State, Level or Scope.

The Assessor/Human Reviewer explicitly supplies the proposed and reviewed target values based on the displayed canonical Pattern lineage.

Backend validates vocabulary and lineage completeness but does not infer progression.

A downgrade also requires the same accountable reviewed path.

Contradictory Patterns remain explicit and visible. They are never averaged away.

## Human Review

Before approval the reviewer must be able to inspect:

- current Capability Claim, if any;
- proposed State / Level / Proven Scope;
- every supporting Pattern;
- every contradictory Pattern;
- Pattern status and scope;
- Pattern → Evidence relationships;
- Evidence signal/confidence/context fields;
- source independence information;
- Observation/Source lineage;
- Next Evidence Needed;
- proposal rationale.

Approval without canonical lineage is forbidden.

Reviewer identity and rationale are mandatory.

Stale review/apply commands return `409 VERSION_CONFLICT`.

## Apply semantics

Only an `APPROVED` ProfileUpdateCase may be applied.

Apply must atomically:

1. create/update the current CapabilityClaim;
2. preserve the previous Claim facts required for audit;
3. transition the ProfileUpdateCase to `APPLIED`;
4. record the Human reviewer/apply metadata;
5. record Domain Event;
6. create Outbox message;
7. commit once.

The event is:

`profile.claim_changed.v1`

The event payload is minimal and must include enough identifiers and old/new Claim facts to audit the business change without dumping the aggregate or leaking hidden assessment data.

Passed validation alone never changes the current Claim.

## API contract

Minimum Assessor/Governance API surface:

- `GET /api/v1/profile-update-cases`
- `GET /api/v1/profile-update-cases/{id}`
- `GET /api/v1/profile-update-cases/{id}/lineage`
- `POST /api/v1/profile-update-cases`
- `POST /api/v1/profile-update-cases/{id}/approve`
- `POST /api/v1/profile-update-cases/{id}/reject` if rejection is represented by the existing final contract; if the current state machine cannot represent rejection without inventing a state, implementation must stop and resolve the contract rather than invent one.
- `POST /api/v1/profile-update-cases/{id}/apply`
- `GET /api/v1/people/{person_id}/flag-profile`
- `GET /api/v1/profile/claims/{claim_id}/lineage`

No direct `PATCH` on Flag Profile or CapabilityClaim exists.

All mutating requests use:
- actor organization context;
- actor identity;
- `expected_version`;
- `idempotency_key`;
- trace id.

## Candidate-safe Profile projection

Candidate must be able to see their own allowed current profile facts without reviewer-only secrets.

Candidate-safe Capability Claim may expose:

- capability reference;
- State;
- Level;
- Proven Scope;
- Evidence Recency;
- Next Evidence Needed;
- Candidate-visible supporting/contradictory Pattern facts where policy permits.

It must not expose:

- reviewer-only rationale;
- reviewer identity where policy marks it internal;
- hidden Assessment trigger;
- hidden World/Simulation truth;
- internal idempotency/workflow metadata;
- unrestricted Assessor lineage.

The exact Candidate endpoint may follow existing Candidate Home/read-model conventions; no second source of truth may be introduced.

## Event and AI boundary

Sprint 20 emits `profile.claim_changed.v1` after an applied, reviewed update.

Sprint 20 does NOT:
- invoke Parcham AI;
- create an AI provider;
- update model weights;
- build Training Engine;
- build Automatic Dataset Builder.

However the event/lineage must be suitable for the future governed automatic ingestion required by DEC-625 through DEC-627.

Approved profile data must not be modeled in a way that would later require a manual Admin batch to enter Parcham AI.

## Security and tenancy

All Profile queries and commands are organization-scoped before row lock.

Out-of-scope IDs return `404`, not a distinguishable cross-tenant error.

No cross-organization Claim/Pattern association is allowed.

Candidate self-reads require:
- Candidate role;
- organization match;
- subject person = actor person.

## Release gates

Sprint 20 is not accepted until all are proven:

1. only Reviewed Behaviour Patterns can support a ProfileUpdateCase;
2. full Claim lineage is queryable before approval;
3. Claim state is one of UNPROVEN/EMERGING/DEMONSTRATED/PROVEN;
4. Level is one of L0–L4 and remains independent of Proven Scope;
5. no numeric progression threshold exists;
6. no backend auto-inference chooses Claim State, Level or Scope;
7. stale commands return `409 VERSION_CONFLICT`;
8. command retries are idempotent;
9. cross-tenant IDs fail closed;
10. contradictory Pattern refs are preserved explicitly;
11. only APPROVED ProfileUpdateCase can apply a current Claim change;
12. apply records `profile.claim_changed.v1` + Outbox atomically;
13. no direct Flag Profile/CapabilityClaim PATCH exists;
14. Claim lineage reaches Pattern → Evidence → Interpretation → Observation → Source;
15. Candidate projection is allowlisted/fail-closed;
16. Profile update does not mutate GateAssessment or Responsibility state;
17. Candidate proof/gate state is not silently promoted by a Capability Claim;
18. Stage artifact records ProfileUpdateCase/Claim/event/lineage counts and zero Gate/Responsibility mutation attributable to this flow;
19. full CI and Live OIDC E2E are green.

## Out of scope

Explicitly out of Sprint 20:

- CompetencyClaim implementation;
- GateAssessment implementation;
- ProfileSnapshot at consequential decision points;
- ResponsibilityRecommendation;
- Flag Board;
- Appointment;
- automatic Claim promotion/downgrade policy;
- numeric scoring or aggregate competence score;
- auto-eligible developmental apply policy;
- Parcham AI proposal generation;
- Automatic Dataset Builder implementation;
- Training/Evaluation/Model Promotion.

## Intended implementation order

1. Flag Profile persistence + migration;
2. Pattern-owned public reviewed-lineage contract;
3. ProfileUpdateCase creation and tenant/idempotency/concurrency rules;
4. pre-review lineage read;
5. Human approval contract;
6. apply CapabilityClaim + `profile.claim_changed.v1`;
7. Assessor Flag Profile reads + Claim lineage;
8. Candidate-safe Profile projection;
9. Assessor UI;
10. Live OIDC E2E;
11. Code Review;
12. Stage Acceptance.

## Result required

At the end of Sprint 20, Parcham must demonstrate:

**Reviewed Pattern → Human-reviewed Profile Update → Current Capability Claim**

with complete lineage and auditability, while keeping Gate, Responsibility and AI promotion separate.
