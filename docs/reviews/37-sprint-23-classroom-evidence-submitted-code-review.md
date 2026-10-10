# 37 — Sprint 23 classroom Evidence human submission technical self-review

**Date:** 2026-10-10  
**Reviewed code SHA:** `20a758db1301875b05b456462e4b87913ad24fe9`  
**Exact-head CI:** https://github.com/mahdimarzooghi4-debug/flag-academy/actions/runs/38036533931 — Backend, Frontend and Keycloak/PostgreSQL/browser E2E SUCCESS.

**Disposition:** Scoped technical self-review ACCEPTED **only for human Interpretation v1 and classroom DRAFT → SUBMITTED**. This is not independent reviewer approval, formal Evidence acceptance, Figma sign-off, Stage or Production.

## Implemented and inspected

- `backend/app/evidence/classroom_evidence_submission_api.py` implements dedicated tenant/class-scoped submission, using existing `EvidenceSubmitRequest`, `EvidenceInterpretation`, `EvidenceLink`, `EvidenceCaseStatus` and strict expected_version contract.
- Current source Observation, original authorization at observed-at, immutable independent VERIFIED source-review and live reviewer mandate are re-attested under the source/grant and EvidenceCase locks, in the same lock order as Draft creation. The original observer cannot submit as the reviewer.
- Existing `_lineage_matches` remains DRAFT-only for Draft-create/replay, while creator-scoped read explicitly allows later statuses (including SUBMITTED) without exposing the case through generic Evidence routes.
- `DRAFT → SUBMITTED` atomically persists one human Interpretation v1, target-scoped links, updated status/version, and one confidential DomainEvent/Outbox with metadata only. `ai_contribution` is restricted by the existing contract to `NONE`. Interpretation does not change a CapabilityClaim or Gate.
- New backend tests cover accepted human fields, no unauthorized/revoked submission, no rationale or raw fact in events, and access by creator only. Keycloak/Chromium E2E verifies actual POST, version 2 and SUBMITTED, private GET, stale second submission and public Evidence denial. PostgreSQL checks exactly one Interpretation/Link and one submitted event with no raw text/rationale. Full CI passed.
- Original classroom Audit/SourceReview/Draft invariants, Mission Evidence and Academy scenarios remained intact.

## Unresolved consequences — do not bypass

- Formal `SUBMITTED → UNDER_REVIEW → ACCEPTED/REJECTED` for private classroom cases has **not been enabled**. A distinct, currently appointed, accountable human Evidence reviewer and an approved independence/governance policy are required; the creating/source-reviewing Assessor must not be silently treated as the formal consequential reviewer.
- Candidate visibility remains false, including SUBMITTED. No inferred visibility, Candidate context or claim promotion.
- Opaque Interpretation target refs are human-supplied links, not validated Capability acceptance, readiness metrics, approval of a product threshold, or proof of independent data.
- Generic Evidence API remains fail-closed to all `CLASSROOM_OBSERVATION` cases. No event-based auto Evidence admission, Profile/Pattern/Gate update, or AI learning.
- Synthetic CI identities are not real human Academy approvals. This technical self-review does not satisfy independent Human Code Review, Stage QA/Testing, release or any production deployment.
- PR #19, #20 and #21 remain Draft/Open/unmerged. Next slice must implement separate Evidence-owned live class-scoped formal reviewer authorization and decision audit, with real OIDC/PostgreSQL separation-of-duties checks. If the actual reviewer appointment policy is not explicitly contracted, fail closed rather than invent one.
