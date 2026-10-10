# 106 — Classroom Evidence Final Human Review: Authorized Contract

**Status:** APPROVED issuer contract / DRAFT software / CI verified, not Human QA, Stage or Production.

## Business authority approved on 2026-10-10

Only an accountable Academy Admin (`ACADEMY_ADMIN`) may issue or revoke an **Evidence-owned, case-scoped** mandate naming a different human final reviewer. This authority does not inherit from a general ASSESSOR role, an Academy class grant or source-review attestation. Each final reviewer separately needs an active, non-revoked Academy class grant in the same organization/class, live organization ASSESSOR membership, identity verified by OIDC, and independence from the source observer, source reviewer, Interpretation author and learner.

## Evidence decision state machine

`DRAFT → SUBMITTED → UNDER_REVIEW → ACCEPTED / REJECTED`.

- Human Interpretation submission alone never accepts Evidence.
- Final reviewer start and decision are separate, accountable commands requiring expected EvidenceCase version, live mandate/revocation check, immutable source SHA-256, class/cohort operational check, human rationale, and transaction locks.
- A reviewer who has not started the case cannot decide it. An expired/revoked mandate cannot authorize a new private workspace/read/start/decision.
- Accepted/Rejected decisions are versioned and immutable, with separate EvidenceReview rows, restricted event payloads and transactional outbox. SQL checks enforce permitted state transitions; raw case/source/interpretation/decision history remains immutable.
- The final mandate is unique per case in this slice and has immutable issuer/reviewer/class/case/time window. Revocation only transitions it irreversibly with version increment; no implicit reassignment or automatic regeneration. A future replacement workflow requires an explicit separate lifecycle contract.
- Actor+tenant scoped idempotency: exact replay is allowed; changed reason, case, reviewer, time window, expected version or pinned source digest is rejected.
- Even classroom `ACCEPTED` cannot be made candidate visible through this flow or directly feed Pattern/Profile/Gate/CapabilityClaim. No AI, score, gate pass or appointment is automatically produced.

## Verification boundary

Real isolated CI: three distinct Keycloak OIDC identities; Academy Admin issuance; active class grant; source review; Interpretation v1; independent human-identity review start; stale/concurrent duplicate rejection; acceptance; Admin revocation; PostgreSQL rejected direct mutation of private history/mandates and append-only records; event/outbox content privacy; downstream accepted snapshot exclusion.

Synthetic test identity and decisions are NOT operational approvals. This is a Technical self-review scope, not independent Human Code Review. All Sprint 21–23 PRs remain Draft/Open/Unmerged. No Stage/QA Gate/Release/Production activity is authorized.
