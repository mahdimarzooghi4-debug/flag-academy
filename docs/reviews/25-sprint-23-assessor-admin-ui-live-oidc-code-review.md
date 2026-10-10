# Sprint 23 — P23-09B Admin grant workspace + live OIDC acceptance: scoped technical review

**Date:** 2026-10-09
**Reviewed code HEAD:** `ddd4520d1565742e948d761e8553f2a9727d2155`
**Exact-head CI:** [37921260738](https://github.com/mahdimarzooghi4-debug/flag-academy/actions/runs/37921260738) — **SUCCESS**, Backend, Frontend and live-OIDC browser E2E with AI governance regressions.
**Review scope verdict:** Implementation and CI verified for this **bounded Academy Admin mandate-management UI and positive Assessor read acceptance**. This is a technical self-review, **not independent human Code Review approval**, full Sprint 23 acceptance, Stage or a release approval.

## Reviewed behavior and authorization boundary

1. The existing Academy Admin class workspace mounts `AssessorGrantAdminWorkspace` only when its selected ClassOffering was returned by the same tenant's verified Cohort/Class catalog. A class-context change changes the component's key and resets local grant form/selection state. An unassigned or global-only ASSESSOR role has no access to this Admin component or its APIs.
2. The workspace uses real `GET /api/v1/admin/academy/classes/{class_offering_id}/assessor-grants` plus the already contracted POST grant create / extend / revoke APIs. The response is validated against the selected `organization_context_id` and exact ClassOffering; the React Query cache includes organization, actor, class and page. Failed grant reads fail closed and disable mutation rather than continuing to show stale cached data.
3. A new appointment requires an explicitly entered valid Assessor person UUID (not an inferred class learner, instructor or global role), a timezone-aware start/end, and an explicit Admin action. The backend independently verifies the candidate has current same-org ASSESSOR membership, valid class and operational status. No Assessor listing/identity discovery was fabricated.
4. Extension requires a strictly later end and reason, and revocation requires both reason and separately checked confirmation. Commands pin the exact current grant version and send unique idempotency keys. Responses are checked against current org/class. A newly observed version resets revocation confirmation, extension input and rationale. The backend remains the authoritative validator for race, version, current grant status and human actor.
5. The real OIDC browser scenario first proves global-only Assessor class reads are 404, then Admin creates a live class mandate via the real browser, then Assessor reads exactly the approved class's Roster, Sessions, recorded Attendance, Activity and qualitative Candidate ReportCard from FastAPI/PostgreSQL (HTTP 200). The assigned Assessor still cannot call Admin discovery (403). Following explicit Admin revocation the same private Roster returns 404 again. No UI observation is converted to Evidence, Profile or Gate.
6. Development `seed.py` deletion order now removes append-only grant revisions then grants before ClassOffering to allow repeatable development reseeding after browser-created mandates. Regression tests preserve this ordering and forbid implicitly creating fake grants.

## Test and review evidence

- React form tests cover valid/invalid explicit UTC timestamps, no inferred timezone, known person UUID format, explicit create, reasoned extend/revoke, revoked read-only history, pagination, disabled/error states and reset of human confirmation when another Admin changes the grant version.
- Existing backend P23-09A/B tests cover identity/tenant/class/interval/role/revocation denial and fail-closed read APIs; code continued to pass without modifying the Evidence, Profile, Gate or AI bounded contexts.
- The first new browser run found a pre-existing intermittent OIDC test storage-read race before reaching grant creation. The token helper now waits for real persisted OIDC storage rather than sampling only once, without mocking authentication or bypassing JWT verification. The final exact-head E2E run passed.
- Technical review found no blocker in the bounded Admin UI + positive signed-in grant/read/revoke package **at the reviewed code HEAD**. This does not establish independent human review approval.

## Remaining acceptance gaps and prohibited assumptions

- P23-09C: independently sourced Academy ClassOffering / Session / Candidate classroom Observation, truthful `observed_at` versus `recorded_at`, late-entry authorization after mandate end, reviewable bridge to Evidence. Do **not** infer lineage from Candidate/Cohort/CapabilityVersion/Mission identity or auto-accept Evidence.
- Assessor's own class-context **frontend workspace** is not included: the positive journey proves real bearer-token backend reads, not an accepted Assessor React classroom workspace. Further role-aware, permission-filtered UI must preserve reviewer-private data boundaries.
- Multi-tenant/second-class live OIDC browser fixtures, concurrent human mutation against real PostgreSQL, and exhaustive cross-class browser navigation remain open for P23-11/P23-12.
- Actual class-completion transition/time source, authorized reappointment after expiry/revocation, Scientific Council role/quorum, authoritative ProofState public reader, Instructor-approved next focus, Knowledge retrieval/AI permissions and attendance-finalization contract are unresolved. Do not infer product rules.
- This PR is stacked on Sprint 22 and remains Draft/Open/Unmerged. No Stage, QA Gate, Release, Production or full Sprint 23 independent Code Review approval was performed.
