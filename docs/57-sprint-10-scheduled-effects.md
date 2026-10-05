# 57 — Sprint 10 Scheduled Effects & Simulation Clock

**وضعیت:** ACCEPTED  
**تاریخ شروع:** 2026-10-05  
**تاریخ پذیرش:** 2026-10-05

## Sprint Goal

Mission Runtime را از consequenceهای صرفاً immediate عبور دهیم و اولین delayed consequence واقعی را با `ScheduledEffect` و simulation clock deterministic اجرا کنیم.

زنجیره:

**Candidate Action → Immediate Consequence → ScheduledEffect → Simulation Time Advance → Due Effect → World State Transition → Factual Observation**

اصل FINAL:

> **Delayed consequence must be a first-class runtime object, not a frontend timer or hidden score.**

## Why this Sprint comes next

Action `NO_ACTION`، latency، waiting، cost-of-delay و delayed/latent consequences بدون هسته زمانی معتبر معنای runtime واقعی ندارند.

بنابراین قبل از `NO_ACTION`:
1. simulation clock
2. ScheduledEffect persistence
3. due-time processing
4. causal audit
5. deterministic state mutation

باید ساخته شوند.

## Data Model

### MissionInstance
Field جدید:
- `simulation_time`

در شروع Mission:
- `simulation_time = started_at`

### ScheduledEffect
- id
- mission_instance_id
- origin_event_id
- effect_code
- label
- due_at
- effect_payload
- cancellable
- cancel_condition
- visibility
- status
- created_at
- applied_at
- cancelled_at
- idempotency_key

Status v1:
- PENDING
- APPLIED
- CANCELLED

در این Slice cancellation اجرا نمی‌شود؛ contract آن حفظ شده ولی acceptance effect غیرقابل‌لغو است.

## Scheduling Rule

Acceptance Mission هنگام:

`EXECUTIVE_RECOVERY_ESCALATION`

علاوه بر immediate escalation effect، این delayed effect را می‌سازد:

```text
effect_code = EXECUTIVE_CHECKPOINT_DUE
due_after_seconds = 900
visibility = CANDIDATE
```

Effect:

```json
{
  "stakeholder": { "executive_checkpoint": "DUE" },
  "mission": { "escalation_status": "CHECKPOINT_DUE" }
}
```

## Simulation Time Advance

Endpoint:

`POST /api/v1/mission-instances/{instance_id}/advance-to-next-event`

Input:
- expected_world_version
- idempotency_key

Candidate زمان دلخواه انتخاب نمی‌کند.

Engine:
1. نزدیک‌ترین ScheduledEffect در وضعیت PENDING را پیدا می‌کند.
2. simulation clock را دقیقاً تا همان `due_at` جلو می‌برد.
3. همه effectهای due در همان زمان را با lock پردازش می‌کند.
4. هر World mutation، world_state_version را افزایش می‌دهد.
5. Runtime Event و Observation append-only می‌سازد.

اصل:

> **Simulation clock advances to the next canonical due event, not to arbitrary client time.**

## Runtime Events

Candidate-visible:
- `scheduled_effect.created`
- `simulation.time_advanced`
- `scheduled_effect.applied`

Internal audit روی applied event:
- `effect_applied`

این payload داخلی برای Candidate expose نمی‌شود.

## Observation

`SCHEDULED_EFFECT_OBSERVED`

فقط facts:
- effect_code
- due_at
- world_version_before
- world_version_after

هیچ Judgment یا Capability interpretation ثبت نمی‌شود.

## Acceptance Timeline

1. Mission starts — World v1.
2. COMMUNICATE — Actor v1→v2.
3. ESCALATE — World v1→v2, Actor v2→v3.
4. ScheduledEffect created — status PENDING.
5. Candidate-visible World هنوز:
   - executive_checkpoint = NOT_SCHEDULED
6. Candidate advances to next world event.
7. simulation clock → exact due_at.
8. ScheduledEffect applied — World v2→v3.
9. Candidate-visible World:
   - executive_checkpoint = DUE
   - escalation_status = CHECKPOINT_DUE
10. Decision — World v3→v4.
11. Mission COMPLETED.
12. Proof remains UNPROVEN.

## Governance Invariants

- Client arbitrary due_at ارسال نمی‌کند.
- Client arbitrary delayed effect ارسال نمی‌کند.
- due_at و effect فقط از exact pinned Mission Version می‌آیند.
- simulation clock فقط به next canonical due event جلو می‌رود.
- ScheduledEffect mutation فقط Engine-owned است.
- stale world version با 409 رد می‌شود.
- command retry idempotent است.
- internal `effect_applied` برای Candidate مخفی است.
- reserved Profile/Evidence/Competency/Gate namespaces همچنان ممنوع‌اند.
- INTERNAL ScheduledEffect به Candidate Observation تبدیل نمی‌شود.
- ScheduledEffect هیچ Evidence یا Proof State تولید نمی‌کند.

## Stage Acceptance

PostgreSQL + Live OIDC باید اثبات کند:
- حداقل یک ScheduledEffect وجود دارد.
- `EXECUTIVE_CHECKPOINT_DUE` به APPLIED می‌رسد.
- `scheduled_effect.created` ثبت می‌شود.
- `simulation.time_advanced` ثبت می‌شود.
- `scheduled_effect.applied` internal applied effect را نگه می‌دارد.
- `SCHEDULED_EFFECT_OBSERVED` ثبت می‌شود.
- simulation_time از started_at جلوتر می‌رود.
- World State delayed effect را دارد.
- final Decision World v3→v4 است.
- Candidate Proof همچنان UNPROVEN است.

## Out of Scope

- ScheduledEffect cancellation execution
- trigger_condition بدون due_at
- NO_ACTION
- TIME_EXPIRED
- WAITING_FOR_WORLD substate
- probabilistic effects
- Temporal/worker-based automatic wake-up
- Evidence Engine

## Definition of Done

- migration `0011`
- ScheduledEffect model
- simulation_time on MissionInstance
- deterministic schedule creation
- advance-to-next-event API
- candidate UI
- API/domain tests
- Live OIDC E2E
- Stage SQL evidence
- CI Green
- Code Review PASS
- merge main
- Ephemeral Stage PASS
- acceptance evidence in GitHub

> **Time is part of the simulation state and must be auditable.**


## Acceptance Record

- Accepted implementation commit: `aede788ff254b2654afef28dd2a59451b3fd0663`
- Main CI Run: `37281951655` — PASS
- Ephemeral Stage Run: `37281951536` — PASS
- Code Review: `docs/reviews/10-sprint-10-scheduled-effects-code-review.md` — PASS
- Stage evidence: `docs/58-sprint-10-stage-acceptance.md`
