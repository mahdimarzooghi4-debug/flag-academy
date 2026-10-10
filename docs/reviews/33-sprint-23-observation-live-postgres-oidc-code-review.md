# 33 — Sprint 23 P23-09C live PostgreSQL/OIDC technical code review

**Date:** 2026-10-09  
**Review SHA:** `39589d6f57bcf576c21e0c60051bbfec0e12f6de`  
**Exact-head CI:** https://github.com/mahdimarzooghi4-debug/flag-academy/actions/runs/37955282256 — Backend / Frontend / E2E SUCCESS.  
**Verdict:** scoped technical **self-review** accepted for authenticated factual Observation capture and PostgreSQL integrity checks. This is *not* independent Human Code Review, an Evidence approval, or a Stage/QA Gate.

## Reviewed

- `frontend/tests/e2e/class-workspaces.spec.ts`: live Keycloak login and independent HTTP requests into FastAPI against real PostgreSQL, before/after a human-administered and then revoked appointment.
- `backend/scripts/observation_ci_session.py`: CI-only, short, synthetic time-valid classroom Session; no operation, production seed, or runtime data authority.
- `backend/scripts/observation_integrity_acceptance.py`: committed record/DomainEvent/Outbox SQL checks and direct privileged SQL UPDATE and DELETE denial via the real PostgreSQL trigger.
- `.github/workflows/ci.yml`: explicit ephemeral fixture and DB integrity gates. Separate unit/schema/migration checks stay in place.
- `docs/98-sprint-23-class-observation-live-acceptance.md`.

## Evidence-backed findings

1. Real OIDC Assessor role is insufficient until Academy Admin grants the exact live class mandate. Instructor POST and unassigned Assessor GET fail; granted Assessor can POST and GET, scoped to exact Class, real Session, Candidate membership and organization.
2. Two concurrent HTTP POSTs with matching actor and idempotency input resolve to the same immutable Observation ID, and the database contains exactly one row and one DomainEvent. Divergent replay is rejected with 409.
3. Other-class, wrong-Candidate, inappropriate-Session and future observed-at attempts are rejected. Observed-at and recorded-at are distinct, and timestamps come from authenticated request + backend clock, not server-invented proof.
4. After explicit human Admin grant revocation, both Observation read and write return 404; no cached grant survives.
5. PostgreSQL rejects both UPDATE and DELETE under the append-only trigger. DomainEvent and Outbox are checked for exactly one emission and absence of the original private observation text.
6. All three GitHub CI jobs succeeded on the exact commit; the initial test failure came from the test-only near-time Session becoming the Admin page's default choice. E2E now explicitly selects the original attendance Session. Product API code was not weakened.

## Residuals and acceptance boundary

- These tests **do not** establish an independent reviewer identity, impartiality, authorization, or human Evidence promotion. A recorded Observation remains factual source data, not an EvidenceCase; no auto promotion to CapabilityClaim/Gate/Profile/AI dataset can occur.
- CI synthetic Session and development OIDC identities are not operational Academy classes, people or learner data; automated credentials and test evidence are not human approval.
- The exact role, independence and review decision contract for the next P23-09C stage must derive from real Evidence/Identity bounded-context policy, not be fabricated. Reviewer-origin independence, stale source attestation and replay idempotency must be checked before any write or promotion.
- A complete lifecycle for terminal ClassOffering status/time remains separately undecided; fail-closed ACTIVE-only current behavior remains.
- PR #19, #20 and #21 remain Draft/Open and unmerged; Figma final sign-off, independent review, Stage, QA, Release and Production are not authorized.

**Next gate:** inspect existing Evidence review contract, implement only source-bound separate human review and explicit Evidence admission with guarded source lineage, tests and CI; no automatic Evidence creation by recording event.
