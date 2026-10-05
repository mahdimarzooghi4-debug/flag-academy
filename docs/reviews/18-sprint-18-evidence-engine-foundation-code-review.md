# Sprint 18 — Evidence Engine Foundation Code Review

**Status:** PASS  
**Date:** 2026-10-05  
**PR:** #16 — Sprint 18: Evidence Engine foundation  
**Reviewed implementation head:** `b0e33bc960372f4f0137d4cf2ed282fe2ff1ef89`  
**CI:** Run `37334850491` — SUCCESS

## Review scope

- Evidence bounded-context ownership and schema
- `observation.sealed.v1` event contract
- transactional Outbox and Evidence Inbox processing
- source-observation idempotency
- cross-context import / foreign-key isolation
- canonical Observation versus Candidate-safe projection
- EvidenceCase optimistic concurrency
- Interpretation contract and target links
- human Review state machine
- Candidate Response boundary
- organization-scoped ASSESSOR authorization
- Parcham AI boundary
- Accepted Evidence versus Profile/Gate/Proof separation
- live OIDC browser acceptance
- Stage SQL and replay evidence

## Findings

### CR-18-001 — Candidate and Assessor Observation projections were initially inverted

**Severity:** Blocking before merge  
**Status:** RESOLVED

The first response builders accidentally returned the Candidate-safe payload to the Assessor while returning the canonical raw Observation payload to the Candidate.

That would have created a hidden-world disclosure path through Evidence even though Mission Runtime itself correctly enforced Candidate projection.

Resolution:

- Assessor `EvidenceCaseResponse` receives canonical `observed_payload`.
- Candidate `CandidateEvidenceCaseResponse` receives only `candidate_visible_payload`.
- Candidate listing is restricted to `candidate_visible = true`.
- the sealed event pins both canonical and Candidate-safe projections at the Mission Runtime ownership boundary;
- Evidence Engine does not attempt to reconstruct visibility from raw data later;
- regression tests explicitly verify that a hidden source field remains Assessor-visible and Candidate-invisible.

This preserves the rule that Evidence cannot become a side channel around Mission Runtime visibility.

### CR-18-002 — Candidate context could initially be requested for hidden Evidence

**Severity:** Blocking before merge  
**Status:** RESOLVED

A non-Candidate-visible Observation could enter `NEEDS_CONTEXT`, but the Candidate could not see that Case. That creates a deadlocked workflow and risks future pressure to expose hidden Evidence.

Resolution:

- `request-context` fails closed unless `candidate_visible=true`;
- hidden Evidence may still be reviewed by authorized Assessors without becoming Candidate-visible;
- Candidate access remains subject-scoped and projection-scoped.

### CR-18-003 — Review resume initially accepted any previous Candidate response

**Severity:** Blocking before merge  
**Status:** RESOLVED

The original `NEEDS_CONTEXT → UNDER_REVIEW` guard checked only whether any Candidate Response existed for the Case. A response from an earlier context-request cycle could therefore satisfy a later request.

Resolution:

- review resume loads the latest `NEEDS_CONTEXT` timestamp;
- it loads the latest Candidate Response timestamp;
- resume is rejected unless the Candidate Response exists after the latest request.

Each context cycle now requires fresh Candidate participation.

### CR-18-004 — Observation / Evidence bounded-context isolation

**Status:** PASS

Mission Runtime creates the factual Observation and records `observation.sealed.v1` in the same transaction through Domain Event + Outbox.

Evidence Engine:

- consumes the versioned event;
- does not import Mission Runtime;
- does not query Mission Runtime tables;
- stores Mission IDs/Event IDs as opaque lineage references;
- has no foreign key into another bounded context.

An architecture test explicitly prevents `evidence ↔ mission_runtime` imports.

### CR-18-005 — Delivery and source idempotency

**Status:** PASS

Two separate dedupe boundaries exist:

1. Inbox uniqueness on `consumer_name + event_id`;
2. EvidenceCase uniqueness on `source_observation_id`.

Stage replay proof publishes:

- the same sealed envelope again;
- another envelope with a fresh event ID but the same source Observation.

Acceptance requires the Evidence consumer Inbox count to increase for the fresh event ID while duplicate Evidence source rows remain zero.

### CR-18-006 — Evidence acceptance does not mean Proof

**Status:** PASS

`evidence.accepted.v1` means human-reviewed Evidence only.

Sprint 18 does not:

- create CapabilityClaim / CompetencyClaim;
- mutate Flag Profile;
- alter Gate state;
- create Responsibility Recommendation;
- change Candidate proof state.

The live browser flow confirms the Candidate remains `UNPROVEN` before and after Evidence acceptance.

### CR-18-007 — Parcham AI boundary

**Status:** PASS

Sprint 18 does not invoke Parcham AI.

`ai_contribution` exists for future lineage but is constrained to exactly `NONE` in this Sprint at both API and domain-validation layers, and the UI exposes it read-only.

No external/internal AI provider, Foundation Model API, managed AI service or provider credential is introduced.

### CR-18-008 — Human authorization and concurrency

**Status:** PASS

- ASSESSOR permission is derived from organization membership, not trusted from an IdP role alone.
- Candidate can list/respond only to own Candidate-visible Cases.
- Candidate receives 403 on Assessor-only Evidence endpoints.
- every EvidenceCase state-changing command requires `expected_version`;
- stale Review command is verified as `409 VERSION_CONFLICT`.
- Candidate Response is append-only and cannot mutate Observation, Interpretation or Review history.

### CR-18-009 — Real workflow verification

**Status:** PASS

CI Run `37334850491` passed on reviewed head `b0e33bc...`:

- backend lint — PASS
- backend type check — PASS
- backend unit/API/architecture tests — PASS
- clean migration — PASS
- development seed — PASS
- OpenAPI export — PASS
- frontend client generation — PASS
- frontend type check — PASS
- frontend unit tests — PASS
- frontend build — PASS
- live OIDC browser E2E — PASS

The browser path verifies:

1. deterministic Mission execution creates factual Observations;
2. Evidence consumer materializes a DRAFT Evidence Case;
3. real OIDC Assessor submits Interpretation v1;
4. stale Review is rejected;
5. human Review enters UNDER_REVIEW;
6. Assessor requests Candidate context;
7. Candidate sees the request but not hidden interpretation/review notes;
8. Candidate cannot access Assessor-only endpoint;
9. Candidate appends context without rewriting Evidence;
10. Assessor resumes review and ACCEPTS;
11. Candidate sees the accepted reviewed Interpretation;
12. Candidate remains UNPROVEN.

## Review conclusion

No blocking findings remain.

Sprint 18 implementation is approved for merge **only after** CI for the commit containing this review document is fully Green.
