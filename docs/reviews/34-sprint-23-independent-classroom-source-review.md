# 34 — Sprint 23 Independent Classroom Source Review technical self-review

**Date:** 2026-10-09
**Reviewed code:** `a031efc1d5e2e0f65adab9e769aa95904c5d47d2`
**Exact-head CI:** https://github.com/mahdimarzooghi4-debug/flag-academy/actions/runs/37957957447 — Backend / Frontend / E2E all SUCCESS.
**Outcome:** Scoped technical self-review completed for the **source-attestation foundation only**; NOT independent human approval, final Evidence admission, Stage or Production.

## Inspected

- `backend/app/evidence/classroom_source_review_api.py`: independent class-appointed Assessor source reader and review command.
- `backend/app/evidence/models.py`: Evidence-owned `ClassroomObservationSourceReview` without cross-context FK.
- `backend/alembic/versions/0034_classroom_source_review.py`: immutable single-decision DB schema, uniqueness, decision/rationale constraints, UPDATE/DELETE-denying PostgreSQL trigger.
- `backend/tests/test_classroom_source_review.py`: fail-closed role/mandate/authorship/source-time/digest checks, successful/rejected decisions, replay/conflict, audit privacy and non-creation of formal evidence.
- `docs/99-classroom-source-independent-review.md` and route registration in `backend/app/main.py`.

## Positive findings

1. Only a currently member `ASSESSOR` independently appointed to the **same** ACTIVE class/cohort may read an observation for review or decide its factual integrity; the original observer and subject cannot review their own source. Current grant, tenant and role are rechecked and mandate row is locked during review.
2. Source provenance is verified from Academy-owned original grant revision and real Session interval; a later updated or revoked original grant does not retroactively invent the original observation window.
3. The client must attest the SHA-256 of the exact immutable source content including observer, subject, grant version and observed/recorded timestamps. Changed/stale source is rejected with 409.
4. The decision is explicit and person-attributed. A single source can have one durable review, with replay only for the same reviewer, digest, outcome and rationale. Conflicting submissions fail with 409. The source row lock serializes review races; PostgreSQL uniqueness is the final invariant.
5. Decision rationale and original private observation text are deliberately **excluded** from DomainEvent and Outbox metadata. Review history is protected by database UPDATE/DELETE trigger.
6. Even a `VERIFIED` source review does not create an `EvidenceCase`, submit/accept Evidence, alter CapabilityClaim/Profile/Gate, or select a training source.

## Open security and product gates

- A source-reviewer **assignment/discovery** UI and authorized pending-review list are not provided in this foundation. Existing Academy Assessor grant is the minimum safe scope; more detailed reviewer appointment policy must be explicitly approved rather than inferred.
- Tests for the new review command are controlled AsyncSession contract tests; CI additionally validates the actual migration and pre-existing live OIDC E2E, **not a live OIDC positive source-review request with two independent Assessor identities**. That must be added before the complete feature is accepted.
- Existing EvidenceCase list/read/write APIs have broader organization-level `ASSESSOR` scope. Passing a classroom source directly into EvidenceCase would leak class-private content; Evidence-owned class-source access rules are required before an explicitly human-submitted Draft EvidenceCase can be created.
- `VERIFIED` means only that one independent human attests the factual source; never that the behaviour interpretation, formal Evidence, or CapabilityClaim has been accepted. The existing Evidence `DRAFT → SUBMITTED → UNDER_REVIEW → ACCEPTED/REJECTED` workflow remains authoritative.
- Authoritative source-review outcomes in a **real Academy** have not been recorded. CI synthetic fixtures are not human decisions or Academy operational data.
- PR #19, #20 and #21 remain stacked Draft/Open/Unmerged. No independent review, Stage/QA, Figma final sign-off, Release or Production approval was performed.

**Next:** test live PostgreSQL/OIDC with distinct organization-appointed Assessors and actual review/revoke race; then harden Evidence-owned classroom case visibility and explicit human Draft submission, without automatic formal Evidence acceptance.
