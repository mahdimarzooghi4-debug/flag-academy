# 35 — Sprint 23 live independent review and classroom Evidence privacy technical self-review

**Date:** 2026-10-09  
**Reviewed live-assessor implementation head:** `f07113b07587a391df9b02375ed020cdd8194764` — [CI #37961479904](https://github.com/mahdimarzooghi4-debug/flag-academy/actions/runs/37961479904), backend/frontend/E2E SUCCESS.  
**Reviewed privacy implementation head:** `4407b9a754635c0c18f5c0379b241994b4561a49` — [CI #37962370405](https://github.com/mahdimarzooghi4-debug/flag-academy/actions/runs/37962370405), backend/frontend/E2E SUCCESS.  
**Verdict:** Scoped technical **self-review** accepted for CI-based identity/immutability acceptance and a private classroom fail-closed Evidence boundary. **Not independent human Code Review, formal Evidence admission, Product/Stage acceptance or Production approval.**

## Reviewed source

- `scripts/ci-seed-independent-assessor.sh`, `backend/scripts/observation_ci_session.py`, `.github/workflows/ci.yml`, `frontend/tests/e2e/class-workspaces.spec.ts`, `backend/scripts/observation_integrity_acceptance.py`, `docs/100-sprint-23-independent-assessor-live-oidc.md`.
- `backend/app/evidence/api.py`, `backend/tests/test_classroom_evidence_privacy.py`, `docs/101-classroom-evidence-confidentiality-gate.md`.

## Verified controls

1. Ephemeral CI Keycloak allocates its own real OIDC subject for an independent reviewer; the backend fixture reads that subject as generated from Keycloak via `GITHUB_ENV`. A guessed/static subject is not allowed. All persons, passwords, appointments, observations and reviews are CI-only.
2. A second real OIDC account lacks class-source read without an independent Admin appointment; first observer cannot review the original source. Newly appointed separate reviewer can inspect the exact source SHA-256 and record an explicit VERIFIED decision; concurrent identical POSTs resolve to one decision, and changed decision/stale hash return 409.
3. Reviewer access is denied again after the accountable Academy Admin revokes the class appointment.
4. Real PostgreSQL verifies only one append-only source-review row/event/outbox, forbids privileged UPDATE or DELETE of **both** recorded Observation and human source decision and excludes private raw facts/rationale from audit event payloads. The same CI also exercises ordinary class/attendance and separate Mission OIDC regressions.
5. A reserved `CLASSROOM_OBSERVATION` Evidence source can no longer be read through general organization-scoped Assessor Evidence list/get/mutation routes; the candidate list and candidate-response case loader also deny it. Source filtering is in SQL for list endpoints and non-disclosing 404 for direct detail/mutation.
6. Legacy non-classroom Evidence source contexts retain their existing routes; negative tests verify the reserved source is denied and positive tests preserve existing detail lookup. The purpose of this guard is confidentiality until dedicated Evidence-owned class-scope authorization is built, not to label protected classroom cases as approved.

## Fixes during CI

- Removed two unused Python imports, sorted CI fixture imports and flushed a new test Person before inserting its foreign-key organization membership.
- Keycloak generated an actual random subject rather than retaining an attempted fixed ID. The CI now verifies its true generated subject and binds precisely that value to the database Person; the browser then successfully authenticated the second Assessor.
- No change bypassed human Evidence review or enlarged a role.

## Remaining gates — do not conflate with this review

- Real operational independent review has not occurred. CI sample accounts are not accountable Academy people.
- The Evidence domain must still define and implement dedicated live-class scoped *Draft creation, read/write, candidate-safe projection and interpretation/reviewer independence*, re-attesting the VERIFIED source digest and original event lineage. No generic EvidenceCase API may receive private class source data via a guessed case ID.
- Formal Evidence lifecycle remains `DRAFT → SUBMITTED → UNDER_REVIEW → ACCEPTED/REJECTED`, with explicit human decision and no automatic Profile/Gate/AI training mutation. `VERIFIED` means only source attestation.
- Domain-specific live OIDC browser coverage for the eventual Draft workflow and its revocation/race conditions remains pending. Figma final reconciliation, independent Code Review and Stage/QA gates remain open.
- PR #19 → #20 → #21 stay Draft/Open/Unmerged; no Stage, QA, release approval or Production action was taken.

**Next technical slice:** Evidence-owned class-source access checks and deliberate human Draft submission, conditioned on the current scoped grant and immutable verified review; no implicit ingestion from the `academy.class_observation_recorded.v1` event.
