# Sprint 23 — P23-09B scoped Assessor classroom read access: technical code review

**Review date:** 2026-10-09  
**Reviewed code HEAD:** `8fb7de9b9f6d7e58b3a681c2e0c16ebca4ae55cb`  
**Exact-head CI:** [37914381619](https://github.com/mahdimarzooghi4-debug/flag-academy/actions/runs/37914381619) — **SUCCESS** (Backend, Frontend, browser E2E with live development OIDC, existing AI governance checks).  
**Review scope:** P23-09B **Backend scoped class-read integration**. Technical self-review recorded, not independent human PR approval and not Stage acceptance.

## Contract and changes

The business authority is DEC-643–646, DEC-638 superseded, and `docs/91-sprint-23-approved-governance-decisions.md`. P23-09A's Academy-owned grant model and human-admin commands are the sole source of a class mandate.

- `backend/app/academy/assessor_access.py`: a centralized, fail-closed per-request authorization reader. A real contextual `ASSESSOR` membership, current Identity organization-role check, persisted grant keyed by Assessor and exact ClassOffering, matching Academy and Cohort tenant, explicit effective time interval, non-revocation and ACTIVE ClassOffering + Cohort are **all** required. No cache, inferred class association, or new global role.
- `backend/app/academy/api.py`: eligible scoped Assessor reads the class roster and recorded Session attendance; Attendance POST remains ACADEMY_ADMIN-only. Unauthorized Assessor-only requests fail **before private roster member/instructor reads**.
- `backend/app/academy/class_sessions_api.py`: same-class Session read for an assigned Instructor, authorized Admin, or live scoped Assessor only. Session lookup remains tenant-bound.
- `backend/app/academy/activity_api.py`: Assessor authorization occurs before reading private learner activity; only existing ClassOffering-linked Learning/Feedback/Attendance sources are returned. No inferred Mission association.
- `backend/app/academy/report_card_api.py`: Assessor grant is checked before private Candidate membership/report reads. Only actual class Candidate membership is eligible for a report. Reviewed claims remain Candidate-safe public Flag Profile results; `proof_state` and `next_learning_focus` remain null without authoritative contracts.
- `backend/tests/test_assessor_class_read_access.py`: direct policy and ASGI/TestClient positive/negative cases covering live class mandate, missing grant, expired/not-yet-active/revoked grant, non-ACTIVE class/cohort, missing current Identity role, unrelated class, class Roster, Sessions, Attendance GET vs forbidden Attendance POST, Activity and qualitative ReportCard. Existing denial tests are retained and updated to prove unauthorized users cannot query private source rows.

## Review findings / remediation

1. **Private-row ordering:** Initial implementation verified the mandate before returning private data, but some roster/activity/report paths first queried private member rows. The access check was moved to immediately after tenant-qualified ClassOffering context, before those private reads for Assessor-only requests. Regression tests assert the early denial.
2. **Legacy static test invariant:** An older test incorrectly prohibited any Assessor mention in Roster source. It was revised to require `has_live_assessor_class_access` instead; unassigned Assessor still receives 404.
3. **Multi-role safety:** Existing Admin, assigned Instructor and own Candidate read paths remain permitted by their original independent conditions. A global ASSESSOR membership **alone** confers no class access. Alternate authorized roles do not create an Assessor mandate.
4. **Consequential boundaries:** No Attendance mutation by Assessor; no Evidence/Observation acceptance, Behaviour Pattern, formal Claim/Proof, Gate status mutation, AI learning or auto-promotion. No cross-context FK was introduced.

## Residual requirements — not yet accepted

- **Authenticated positive end-to-end grant journey:** Tests use real FastAPI routes with controlled database doubles, plus existing live-OIDC browser regressions (which verify the unassigned Assessor remains denied). This does **not** yet certify creation of a grant and signed-in Assessor reading another real tenant/class through a real PostgreSQL + Keycloak fixture. Explicit second class/second tenant and concurrent grant/revocation tests remain needed.
- **P23-09B Admin operational UX:** Assigned-grant listing/discovery, UI controls for appoint/extend/revoke, and signed-in positive Assessor class workspace still need separate scoped frontend contracts and E2E.
- **P23-09C classroom observations:** authoritative ClassOffering/Session/Candidate observation source, observed-at versus recorded-at, late-entry permissions and Evidence review bridge are not yet built.
- **Class lifecycle:** no guessed automatic class completion time or end-state transition; only explicitly ACTIVE records can authorize live access. Reappointment after expiry/revocation is a separate contract.
- **Other Sprint 23 decisions:** independent ProofState, Instructor-approved next-learning-focus, Scientific Council knowledge governance, Academy Knowledge retrieval and Attendance finalization/justified correction remain separate slices.

## Gate outcome

**P23-09B Backend = Code/CI Verified (partial product acceptance).** P23-09 overall is still PARTIAL. No full Sprint Code Review sign-off, Stage, QA Gate, Release, Merge or Production has been authorized or executed. PR #21 remains Draft/Open/Unmerged, stacked behind Sprint 22; PRs #19/#20 must not be merged without explicit instruction.
