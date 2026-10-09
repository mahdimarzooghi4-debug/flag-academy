# Sprint 23 — P23-09A Assessor Class Grant Foundation: scoped technical code review

**Review date:** 2026-10-09
**Reviewed implementation HEAD:** `6f7c82bf62b232560fb365edde462981ed86e6f9`
**Exact-head CI:** [37911369651](https://github.com/mahdimarzooghi4-debug/flag-academy/actions/runs/37911369651) — SUCCESS (Backend, Frontend, Live OIDC E2E)
**Scope verdict:** CODE/CI VERIFIED **for the administrative grant foundation only**. This is a technical self-review, **not independent human PR approval**, Stage Acceptance or full Sprint sign-off.

## Reviewed files / owner boundaries

- `docs/91-sprint-23-approved-governance-decisions.md` and DEC-643..652: the ten explicitly approved business decisions and outstanding contracts.
- `backend/app/academy/models.py`: Academy `AssessorClassGrant` and append-only `AssessorClassGrantRevision`, scoped to organization and `ClassOffering`. Only intra-Academy FK; Assessor person identity remains an ID reference, not a cross-context FK.
- `backend/alembic/versions/0031_assessor_class_grants.py`: matching relational constraints, unique class-person grant identity, actor/org/idempotency key, immutable-revision DB trigger.
- `backend/app/identity/public_reader.py`: Identity-owned authoritative organization-role read. No relying on global realm ASSESSOR role or unverified person ID.
- `backend/app/academy/assessor_grants_policy.py`: pure time-window + revoked + ACTIVE ClassOffering/Cohort validity value-object rule; fails closed for missing/invalid window.
- `backend/app/academy/assessor_grants_api.py`: ACADEMY_ADMIN-only grant create, extend and revoke; organization-scoped class/assessor validation; optimistic version checks; idempotency; source/audit event and transactional outbox. All timestamps require timezone-aware input and explicit start/end.
- `backend/tests/test_assessor_class_grants.py`: negative tenant/membership access, interval and version rejection; positive create, extend and revoke; audit/event atomic-command assertions; original-result idempotency replay; migration and OpenAPI contract guards.
- `backend/app/main.py`: new admin router only. No automatic modification to Academy class read, Evidence, Gate, Profile or AI routes.

## Security findings and remediation

1. **Historical idempotency reply:** The first implementation could return the current mutable grant on a retry after a later update. Fixed by `_response_from_revision` returning the immutable result pinned to the accepted revision, with regression test. Do not remove this defense.
2. **Time, revocation, class status:** Expired/revoked grants do not regain validity through extend; class/cohort must be operationally ACTIVE for new/extended grants. No auto-assumption about class completion timestamp or Cohort end date.
3. **Tenant and identity isolation:** Admin class context resolves via real Cohort organization; Identity membership is explicitly checked for same-organization ASSESSOR. Unauthorized class/person fails without granting access.
4. **Audit and concurrency:** Current grant mutations use row locking and optimistic versions; append-only revisions are protected by DB trigger and stored in the same transaction as DomainEvent/Outbox.
5. **Privacy and governance:** No automatic Assessor class read is introduced. Existing globally-scoped Assessor role cannot see class roster, activity or report card; Evidence/Observation acceptance, human Profile Apply and Gate review paths are untouched.

## Explicit residual gaps — must stay open

- **P23-09B — Live class read authorization:** must add context-level active grant verification to each roster/session/recorded attendance/activity/report-card API, and independently verify current Identity role. No positive Assessor classroom views yet; neither the data nor private reviewer rationale may bypass source-domain policy.
- **Admin grant discovery / operational UI:** no grant listing workspace yet; create returns its identifier but an Admin list/search and complete Browser journey remain outstanding.
- **Re-appointment lifecycle:** a class-person record is unique; creating a new grant for the same pair after expiry/revocation is intentionally denied rather than inferred. A governed reappointment transition, if required, needs an explicit contract.
- **Class completion:** `ClassOffering.status` has no formally approved terminal lifecycle transition here. The policy fails closed outside ACTIVE; do not infer completion from last Session or Cohort end date.
- **P23-09C — Classroom Observation:** independent factual observation ingestion, class/session/person source validation, human Evidence review bridge and post-mandate historical-entry authorization remain unimplemented.
- **Approval/knowledge/focus/attendance finalization:** subsequent separate contracts from DEC-647..651 remain pending; neither `ProofState` nor `next_learning_focus` should be synthesized.
- Positive API flows were exercised via typed application tests with controlled database doubles; **a dedicated authenticated HTTP + real PostgreSQL positive grant command E2E test** and concurrent cross-tenant/duplicate-grant stress tests remain for P23-11/12. A successful existing E2E suite is not evidence that the positive Assessor grant UI journey has been accepted.

## Gates

P23-09A Code/CI Verified **only**. P23-09 overall remains PARTIAL; PR #21 stays **Draft/Open/Unmerged**; PRs #19/#20 remain unmerged unless explicitly instructed. No Stage/QA Gate, Release, Production, or human PR approval occurred.
