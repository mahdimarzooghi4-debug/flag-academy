# 97 — P23-09C Classroom Assessor Observation Capture (Foundation)

**Date:** 2026-10-09
**Scope:** factual classroom Observation recording under an active, live Academy appointment; no Evidence conversion.

## Source contract

Academy owns immutable `ClassAssessorObservation` with tenant, ClassOffering, real Session, real Candidate membership, observer, grant ID + grant version, separate observed-at and recorded-at UTC timestamps, human-entered factual note and actor-scoped idempotency. DB uniqueness, immutable UPDATE/DELETE denial, append-only event plus transactional outbox and grant-row locking protect lineage.

Only an authenticated ASSESSOR who is currently a member of that organization and has an ACTIVE, unexpired, unrevoked class mandate can create or read **their own** observations. The original observed-at must fall within the real Session interval **and** the valid mandate interval, may not be in the future, and must precede the actual recorded-at; historical entry while the grant is still currently active is allowed. No generic backdating to create authority. Candidate must be the authoritative CANDIDATE member of the Cohort associated with the ClassOffering. An ended mandate grants no operational read or write; separate historical audit access is not invented.

API:
- `POST /api/v1/class-offerings/{class_offering_id}/observations` (201)
- `GET /api/v1/class-offerings/{class_offering_id}/observations` (current observer, live grant only)

All writes fail closed on missing/grant/tenant/person/session ambiguity, stale class state, invalid timestamp and reused idempotency keys. A successful POST emits `academy.class_observation_recorded.v1` with metadata-only payload; sensitive note text is not placed into the DomainEvent/Outbox payload. No automatic Evidence/Pattern/Profile/Gate mutation or AI learning occurs.

## Explicit limitations and next dependencies

- This slice creates an **observation source**, not an EvidenceCase. P23-09C **remains open** until a separately authorized human review contract verifies source integrity, context, reviewer independence and explicit Evidence submission/acceptance. No automatic converter is permitted.
- The business permits post-class factual entry; however, writing **after the class mandate ends or is revoked** still lacks a separate historical authorization/privacy contract, so this path fails closed in that situation.
- The ClassOffering completion state machine/cutoff remains undefined: only explicitly ACTIVE classes/cohorts pass; no invented terminal time.
- Tests verify API schema, positive capture, time/identity boundaries, replay and audit, and migration append-only trigger declaration. CI PostgreSQL migration plus independent OIDC E2E are required; a targeted browser test for this new POST and actual DB concurrent writes should follow before Sprint acceptance.
- Nothing here approves Academy Knowledge, Dataset, Gemma Trainer or AI Tutor, and nothing here is Stage permission.

**Process:** Business → Technical → Scrum/Product Backlog → Sprint → Code → Code Review → Stage → QA/Testing → Release Approval → Production.
