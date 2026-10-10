# 105 — Classroom Evidence final-review mandate technical foundation

**Date:** 2026-10-10. **Status:** TECHNICAL FOUNDATION ONLY — issuer/revocation governance PENDING.

## What exists
- Evidence-owned `ClassroomFinalEvidenceReviewMandate` inert relational record with case, organization, class, named reviewer, human issuer identity, version, issue/start/end/revoke timestamps. The case is referenced within the Evidence context; no cross-context foreign key to Academy is added.
- A *necessary-only* precondition check of same-case/same-class/same-tenant reviewer identity, live time window, non-revoked mandate, authoritative-current-membership input, current Academy class mandate and class/cohort state, source digest, version, and separation from source observer, human source reviewer, Interpretation author and learner.
- PostgreSQL migration 0036 closes additional tampering gaps on DRAFT → SUBMITTED: aside from status, incremented version and updated_at, no EvidenceCase column may change. SUBMITTED remains immutable; migration 0035 still rejects formal decision states.
- Real PostgreSQL negative integrity probes for private lineage, source metadata, and review history; an E2E assertion that no mandate is ever auto-created.

## What this does NOT authorize
No human Evidence final-review mandate can be issued or revoked through API. No list/view granting private source access to a would-be final reviewer. No transition to UNDER_REVIEW / ACCEPTED / REJECTED. The type/predicate is a technical prerequisite, **not permission**, and must never be called as a complete runtime guard. Existing SQL decision barrier remains active. No Profile, Gate, Pattern or CapabilityClaim update; no AI role.

## Governance still requiring explicit decision
1. Which accountable human role is allowed to issue/revoke the Evidence-owned final-review mandate? `ACADEMY_ADMIN` can currently appoint ordinary class Assessors, **not** final Evidence reviewers.
2. Is the mandate per-case or class-wide (this first inert schema only records a case-bound assertion; no policy has been inferred or enabled)?
3. Is the same final reviewer responsible for review start and final decision, and what authorized replacement path exists?
4. Exact issuance, extension, revocation, idempotency, immutable history and stale-version review policies.

After these are approved, the next slice must implement locked Evidence-owned mandate commands, exact issuer policy, delegated read protection, reviewer-scoped UNDER_REVIEW and human ACCEPTED/REJECTED commands, decision event/outbox/audit and real OIDC/PostgreSQL concurrent/revoked/guessed-ID tests. The migration safety barrier must be deliberately updated only alongside those passing tests.

Sprint 23 PR #21 remains Draft/Open. Technical self-review is not independent Human Code Review or production admission.
