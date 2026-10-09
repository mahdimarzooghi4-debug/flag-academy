# Sprint 23 — P23-09B Assessor classroom: scoped technical Code Review

**Review date:** 2026-10-09
**Reviewed implementation HEAD:** `49bc67ec47af3fbf5f27e114ec65fe817db20577`
**Exact-head CI:** [37923369454](https://github.com/mahdimarzooghi4-debug/flag-academy/actions/runs/37923369454) — **SUCCESS** Backend, Frontend, live Keycloak/OIDC E2E and AI governance regression checks.
**Scope finding:** Read-only Assessor classroom experience **Code/CI Verified**. This is a technical self-review and **does not constitute independent human PR approval**, Sprint Acceptance, Stage or Production admission.

## Contract and changes reviewed

- `backend/app/academy/assessor_classes_api.py` and `backend/app/main.py`: new `GET /api/v1/me/academy/assessor-classes`, available only through current authenticated `ASSESSOR` organization role. It returns bounded (limit 1–100), stable-paginated current **live** class mandates for exactly the caller's person + selected organization. Joins Academy-owned Grant → ClassOffering → Cohort; filters grant interval, non-revocation, and explicit ACTIVE ClassOffering/Cohort. No global class catalog, other actors' assignment, historical audit grants or cross-context identity foreign key.
- The existing Identity public role reader verifies current same-organization ASSESSOR membership before any class discovery query. An unknown/removed membership returns an empty list rather than privileged classroom details.
- Each existing Academy private endpoint (Roster, Sessions, recorded Attendance, Activity and qualitative ReportCard) independently re-checks current appointment through `has_live_assessor_class_access`. Discovery is **not** treated as a bearer permission token, an Evidence assignment or a Gate authorization.
- `frontend/src/components/AssessorClassWorkspace.tsx` and `frontend/src/App.tsx`: new read-only role-gated classroom view; discovers real appointments rather than accepting manually invented class IDs. React Query keys include organization/person/class (plus pagination/session/learner where relevant); refetches live mandates on an interval or window focus. An unavailable/failed grant read fails closed and hides private results. Display is limited to matching class + Cohort + Session/Person read-model identities. No mutation command, instructor-private reviewer notes, score/rank, AI grade, ProofState inference or auto-learning.
- Learning completion and reviewed CapabilityClaim are shown independently from authoritative ProofState; absent ProofState remains null, and unapproved next focus remains absent. Historical admission and Observation remain separate.

## Tests and evidence

- `backend/tests/test_assessor_class_discovery.py`: verify role-scoped OpenAPI, bounds, membership check before lookup, org/person filter and time/revocation/ACTIVE SQL guards, empty results for non-appointment and revoked identity membership.
- `frontend/src/components/AssessorClassWorkspace.test.tsx`: verify authorized read-only context, missing attendance not treated as absence, ProofState unknown, no auto-focus, cross-cohort mismatch non-disclosure, loading/error fail-close, no resurrection after grant disappears, and navigation only through assigned class page.
- `frontend/tests/e2e/class-workspaces.spec.ts`: full live OIDC + PostgreSQL test now confirms the Assessor **React classroom view** is empty before admin appointment, shows the actual selected ClassOffering and Candidate report after appointment, then hides all private Candidate/class details after Admin revocation. Existing real API 404/200/404 and forbidden admin 403 proofs remain in the same flow.
- First Type Check failures were confined to test fixture SQL query typing and an optional attendance TypeScript narrowing; both corrected. The exact-head Backend/Frontend/E2E run is green.

## Security, acceptance boundaries and residual risk

- All class/tenant/person filters are applied by the backend, not trusted from frontend class selectors. The frontend is a read-only presentation of current grants and validated owned projections; revocation enforcement by each API is immediate; frontend private state is revalidated on its polling/window-focus cycle. No claim of synchronous push-based client invalidation is made.
- No Assessor access expands to Evidence, Profile, Gate, AI model internals, Admin operations, attendance mutation or Instructor-only workflows.
- No cross-org, second-class OIDC positive/negative fixture has yet been added to this browser suite. Those hardening tests and simultaneous multi-admin/Assessor request race checks remain for P23-11/12; DB filters and unit/contract tests do **not** replace exhaustive multi-tenant integration coverage.
- **P23-09C remains separate:** authoritative Academy class/session/person factual Observation with `observed_at`, `recorded_at`, late-entry review scope, immutable provenance and a human-reviewed Evidence bridge. Never infer Mission-to-ClassOffering linkage, automatically accept Evidence or change Profile/Gate.
- Other Sprint 23 blocked contracts persist: class completion lifecycle, reappointment after expired/revoked mandate, Council workflow quorum, approved knowledge access, independent ProofState and Instructor focus, and attendance-finalization trigger.
- PR #21 remains **Draft/Open/Unmerged** on Sprint 22 base. No Ready for Review, merge, Stage, QA Gate, Release or Production occurred.
