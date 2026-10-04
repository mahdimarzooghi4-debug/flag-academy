# Sprint 1 — Code Review 01

**Date:** 2026-10-04  
**Scope:** Academy Foundation vertical slice through commit `a3079d1bd64921476c1a6e3b7180e4cb4ba92416`

## Review result

Initial implementation is structurally aligned with the approved Modular Monolith and Blended Learning model. The first CI-green slice established Candidate/Instructor workspaces, Curriculum/Cohort/Class foundations, OIDC, migrations, read models, and the event platform.

## Blocking findings fixed during review

1. **Outbox payload was not the canonical versioned Event Envelope.**
   Fixed by introducing a typed `EventEnvelope`, atomic `record_event`, durable DomainEvent record, and full-envelope Outbox payload.

2. **Outbox publisher used core NATS rather than JetStream.**
   Fixed by using JetStream and ensuring the `PARCHAM_EVENTS` stream exists.

3. **Contextual authorization could inherit realm roles across organization contexts.**
   Fixed by making OrganizationMembership roles authoritative for product permissions in the selected organization.

4. **Cohort schedule exposed organization-wide schedule to any authenticated member.**
   Fixed by requiring Cohort membership, except Academy Admin.

5. **JWKS retrieval blocked the async event loop.**
   Fixed by moving synchronous PyJWKClient retrieval to a worker thread.

6. **Request trace was not propagated into ActorContext.**
   Fixed by attaching request trace_id to ActorContext.

7. **Development credentials were committed in the Keycloak realm.**
   Fixed by removing user passwords from realm JSON and seeding local passwords from ignored `.env` variables.

## Remaining Sprint-level gaps

These are not accepted as completed yet:
- true E2E browser test with Keycloak for Candidate and Instructor;
- event-driven projection rebuild/update rather than development-seed-only projections;
- Stage deployment and Stage acceptance;
- full OIDC integration test against a live Keycloak instance;
- explicit architecture-boundary automated test.

Sprint 1 therefore remains **IN PROGRESS**. Code Review for the implemented slice passes after the blocking fixes, but Sprint Acceptance does not pass until the remaining gates are closed.
