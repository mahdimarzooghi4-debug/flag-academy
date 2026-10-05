# 73 — Sprint 18: Evidence Engine Foundation

**Status:** IN PROGRESS  
**Date:** 2026-10-05

## Goal

Establish the first real Evidence Engine bounded context so sealed factual Mission Runtime observations can enter an auditable human-review workflow without mutating Profile, Gate, Capability proof or Mission truth.

The first executable chain is:

**Mission Runtime Observation → `observation.sealed.v1` → EvidenceCase DRAFT → Interpretation v1 → SUBMITTED → UNDER_REVIEW → ACCEPTED / REJECTED / NEEDS_CONTEXT**

## FINAL decision alignment

This Sprint implements the already-final architecture in:

- DEC-328 — Raw Event → Observation → Candidate Evidence → Reviewed Evidence → Pattern → Profile Claim.
- DEC-330 — raw fact remains immutable; Interpretation can version/supersede.
- DEC-332 — source independence is explicit.
- DEC-333 — prompt contamination is recorded.
- DEC-367 — Mission Engine produces Observation, not Evidence.
- DEC-378 — Action → Consequence → Observation → Evidence Review.
- DEC-390/391 — Evidence Engine owns interpretation; Mission Runtime owns fact.
- DEC-393/394/395/396 — provenance, versioned interpretation, target-specific links and review state machine.
- DEC-397 — Parcham AI may propose later but cannot make consequential decisions.
- DEC-416 — no claim without lineage.
- DEC-419 — no gate failure without accountable human review; no black-box responsibility assignment.
- DEC-465/466 — sealed Observation is immutable; EvidenceCase is the Evidence aggregate.
- DEC-469 — EvidenceCase cannot directly mutate Flag Profile.
- DEC-484 — governance records use history, not ordinary delete.
- DEC-553 — Candidate Response adds context and cannot rewrite Evidence.
- DEC-567/576 — versioned events, immutable evidence boundary and cross-context contract/event writes.

## Observation boundary

Mission Runtime system-generated observations are factual and immutable by construction. In Sprint 18 they are treated as **SEALED at creation** and emit the cross-context contract `observation.sealed.v1`.

Evidence Engine must ingest the event payload. It must not import or directly write Mission Runtime repositories/tables, and it must not create a database foreign key into `mission_runtime`.

The sealed event snapshot carries enough lineage to reconstruct the source:

- observation id;
- subject person id;
- organization context;
- source context = `MISSION_RUNTIME`;
- mission instance id;
- source runtime event id;
- observation type;
- factual statement;
- factual payload;
- occurred_at;
- source independence group;
- provenance.

For Mission Runtime observations, the conservative independence group is the Mission Instance. Multiple observations from one Mission execution are therefore not silently treated as independent sources.

## EvidenceCase aggregate

Evidence schema owns:

- `EvidenceCase`
- `EvidenceInterpretation`
- `EvidenceLink`
- `EvidenceReview`
- `CandidateResponse`

### EvidenceCase

State:

**DRAFT → SUBMITTED → UNDER_REVIEW → ACCEPTED / REJECTED / NEEDS_CONTEXT**

`NEEDS_CONTEXT → UNDER_REVIEW` occurs only through an explicit reviewer action after Candidate context is added.

The Case stores an immutable source snapshot and opaque source IDs. It has its own optimistic-concurrency `version`.

### EvidenceInterpretation

Sprint 18 creates Interpretation v1 when a Case is submitted.

Interpretation includes:

- behaviour code;
- behaviour description;
- signal: POSITIVE / NEGATIVE / CRITICAL / NEUTRAL;
- scope;
- confidence about interpretation validity;
- context difficulty;
- prompt contamination;
- AI contribution;
- assessment mode;
- rationale.

Interpretation records are versioned. The schema supports ACTIVE / SUPERSEDED history; supersession workflow itself is deferred.

### EvidenceLink

Each Interpretation may contain target-specific links:

- target type: CAPABILITY / COMPETENCY / GATE;
- opaque target ref;
- signal;
- scope;
- relevance;
- confidence.

A link never mutates its target.

## Human review boundary

Sprint 18 introduces the existing architecture role `ASSESSOR` as an organization membership and real OIDC development identity.

Assessor may:

- list organization Evidence Cases;
- inspect immutable source Observation snapshot;
- submit Interpretation v1;
- start/re-enter review;
- ACCEPT;
- REJECT;
- REQUEST_CONTEXT.

Every state-changing command requires `expected_version` and fails on stale state.

Accepted/Rejected decisions emit:

- `evidence.accepted.v1`
- `evidence.rejected.v1`

Acceptance means **reviewed evidence only**. It does not imply a Capability Claim, Profile update, Gate result or proven status.

## Candidate response boundary

Candidate may see only own Evidence Cases through a candidate-safe projection. Mission Runtime pins both canonical Observation payload and the candidate-visible projection into the sealed event; Evidence Engine persists both and never reconstructs Candidate visibility from raw payload later.

A non-candidate-visible Observation is not listed to the Candidate and cannot enter REQUEST_CONTEXT, preventing hidden-world leakage and deadlocked context requests.

Before ACCEPTED, hidden assessor interpretation/mapping/review notes are not exposed. Candidate may see:

- immutable source observation;
- case state;
- explicit context request;
- own appended responses.

On ACCEPTED, the accepted interpretation may be shown as reviewed evidence.

Candidate Response:

- allowed only for the subject Candidate;
- allowed only while Case is `NEEDS_CONTEXT`;
- append-only;
- never edits source Observation;
- never edits Interpretation;
- never edits Review history.

## Parcham AI boundary

Sprint 18 does not invoke Parcham AI.

The schema records `ai_contribution` so future Parcham-owned model proposals have explicit provenance. In Sprint 18 the only valid value is `NONE`; no UI or API caller may claim AI contribution before an explicit Parcham AI integration contract exists. Any future Parcham AI Interpretation remains a Proposal until human review according to consequence policy.

No external or internal AI-provider dependency is introduced.

## Events and idempotency

Evidence observation ingestion uses a dedicated NATS consumer with Inbox idempotency.

- duplicate `observation.sealed.v1` delivery cannot create duplicate Evidence Cases;
- `source_observation_id` is unique inside Evidence Engine;
- Evidence commands record Domain Event + Outbox in the same transaction;
- event payloads carry facts/refs, not aggregate dumps.

## Acceptance scenario

1. Academy Admin creates/activates/assigns the deterministic recovery Mission.
2. Candidate executes the full Mission including `RUN_EXPERIMENT`.
3. Mission Runtime creates factual Observations and emits `observation.sealed.v1`.
4. Evidence consumer creates DRAFT Evidence Cases without reading Mission Runtime tables directly.
5. Assessor signs in with real OIDC and opens `EXPERIMENT_RESULT_OBSERVED`.
6. Assessor submits Interpretation v1 linked to `METRICS_EXPERIMENTATION`.
7. Assessor starts review and requests Candidate context.
8. Candidate signs in, sees the context request but cannot see hidden assessor notes/mapping and appends context.
9. Assessor re-enters review and ACCEPTS the Evidence.
10. Candidate can see the accepted reviewed interpretation.
11. Candidate Home remains `UNPROVEN`; no Flag Profile, Gate or Responsibility state is created or mutated.

## Out of scope

- BehaviourPattern / Pattern Engine
- EvidenceConflict automation
- independent multi-review / Calibration Case
- Interpretation supersession command
- ProfileUpdateCase
- Capability/Competency Claim mutation
- Gate Assessment
- Responsibility recommendation
- Flag Board
- Parcham AI-generated interpretation
- manual Assessor Observation creation
- Real Project observation ingestion

## Release gates

Sprint 18 is accepted only if:

- migration succeeds from clean PostgreSQL;
- backend lint/type/unit/API tests pass;
- OpenAPI/client regeneration passes;
- live OIDC browser acceptance covers Candidate + Assessor workflow;
- event/outbox/inbox ingestion is proven;
- duplicate Observation delivery is idempotent;
- Candidate cannot access another person's Case;
- Candidate cannot mutate Observation/Interpretation;
- stale EvidenceCase commands return 409;
- Accepted Evidence does not change Candidate `UNPROVEN` state;
- Stage artifact proves Evidence counts, review transitions and zero Profile/Gate mutation.
