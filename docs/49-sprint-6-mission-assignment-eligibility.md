# 49 — Sprint 6 Mission Assignment & Eligibility

**وضعیت:** IN PROGRESS  
**تاریخ شروع:** 2026-10-05

## Sprint Goal

Gap حاکمیتی Mission Runtime را ببندیم تا Active بودن Mission به‌تنهایی مجوز اجرا نباشد.

زنجیره معتبر v1:

**Active Mission Version → Academy Admin Assignment → Candidate Eligibility Check → Mission Instance → Runtime**

اصل:

> **ACTIVE Mission ≠ Candidate Eligible Mission**

و:

> **Mission Runtime فقط از Assignment معتبر و Eligibility موفق شروع می‌شود.**

## مسئله‌ای که Sprint می‌بندد

در Sprint 5، Candidate می‌توانست هر Mission Version فعال در Organization را در catalog ببیند و Start کند. State `ELIGIBILITY_CHECK` وجود داشت اما check واقعی نداشت.

این با اولویت FINAL Backlog ناسازگار بود:

**Safety / Governance dependency → Architectural dependency → Learning Journey continuity**

## Scope

### Mission Assignment

Entity جدید:
- assignment_id
- organization_context_id
- candidate_id
- mission_version_id
- status
- assignment_reason
- assigned_by
- idempotency_key
- created_at
- started_at
- completed_at
- cancelled_at

Lifecycle:
**ASSIGNED → STARTED → COMPLETED**

و:
**ASSIGNED/STARTED → CANCELLED**

### Assignment APIs

Admin:
- `GET /api/v1/studio/mission-assignment-candidates`
- `GET /api/v1/studio/mission-assignments`
- `POST /api/v1/mission-assignments`

Candidate:
- `GET /api/v1/missions/active` فقط Assignmentهای خود Candidate را برمی‌گرداند.
- `POST /api/v1/missions/{version_id}/instances` بدون `assignment_id` معتبر قابل اجرا نیست.

### Eligibility v1

در زمان Assignment و دوباره در زمان Mission Start:
1. Candidate باید Membership با Role = CANDIDATE در همان Organization داشته باشد.
2. Candidate باید Candidate Journey فعال در همان Organization داشته باشد.
3. Assignment باید متعلق به همان Candidate، Organization و exact Mission Version باشد.
4. Mission Version برای Start باید ACTIVE باشد.
5. هر Assignment فقط به یک Mission Instance متصل می‌شود.

نتیجه Eligibility در Runtime Audit به‌صورت `mission.eligibility_passed` ثبت می‌شود.

## Product UX

Academy Admin:
1. Mission را فعال می‌کند.
2. Candidate واقعی Organization را انتخاب می‌کند.
3. Mission را Assign می‌کند.
4. وضعیت Assignment را می‌بیند.

Candidate:
1. Mission فعال ولی Unassigned را نمی‌بیند.
2. بعد از Assignment، Mission را در Runtime Workspace می‌بیند.
3. Start فقط با Assignment معتبر انجام می‌شود.
4. Assignment با Start به STARTED و با Mission completion به COMPLETED می‌رود.

## Events

Domain events:
- `mission.assigned.v1`
- `mission.started.v1`
- `mission.completed.v1`

Runtime audit:
- `mission.status_changed`
- `mission.eligibility_passed`
- `mission.started`
- existing action/consequence events

## Invariants

- Active بودن Mission به‌تنهایی مجوز اجرا نیست.
- Candidate هیچ Mission unassigned را از Candidate catalog دریافت نمی‌کند.
- Client-supplied assignment_id بدون ownership معتبر قابل استفاده نیست.
- Assignment cross-organization قابل استفاده نیست.
- Assignment برای Candidate دیگر قابل استفاده نیست.
- Assignment برای Mission Version دیگر قابل استفاده نیست.
- Eligibility در Start دوباره بررسی می‌شود؛ Assignment قدیمی به‌تنهایی کافی نیست.
- Mission Instance به exact assignment_id و mission_version_id Pin می‌شود.
- Mission completion همچنان Capability را Proven نمی‌کند.
- Assignment/Eligibility هیچ مسیر write به Evidence/Profile ندارد.

## Stage Acceptance

Live OIDC + PostgreSQL باید اثبات کند:
1. Admin Mission را Draft → Pilot → Validated → ACTIVE می‌کند.
2. Candidate قبل از Assignment Mission را نمی‌بیند.
3. Admin Mission را به Candidate Demo Assign می‌کند.
4. Candidate بعد از Assignment Mission را می‌بیند.
5. Candidate Mission را Start می‌کند و Eligibility PASS در Runtime ثبت می‌شود.
6. Candidate Runtime را تا COMPLETED پیش می‌برد.
7. Assignment در PostgreSQL به COMPLETED می‌رسد.
8. Mission Instance به همان Assignment/Candidate/Version متصل است.
9. هیچ Mission Instance بدون assignment_id وجود ندارد.
10. Proof State همچنان UNPROVEN است.

## Out of Scope

- Capability prerequisite policy در Eligibility
- Gate-based eligibility
- Assignment expiry/start windows
- Assignment cancellation UX
- Replay assignment policy
- Actor State
- COMMUNICATE / ESCALATE / DELEGATE / CHANGE_SCOPE / ALLOCATE_RESOURCE / RUN_EXPERIMENT / NO_ACTION execution
- ScheduledEffect
- Evidence Engine

## Definition of Done

- migration 0009
- backend contract + domain tests
- Admin Assignment UX
- Candidate assignment-gated Runtime UX
- Live OIDC E2E
- CI Green
- Code Review PASS
- merge main
- Ephemeral Stage PASS
- Stage evidence recorded in GitHub

> **Assignment authorizes an opportunity to run a Mission; it does not create Evidence or Proven Capability.**
