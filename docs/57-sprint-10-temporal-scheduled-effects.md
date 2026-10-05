# 57 — Sprint 10 Temporal Scheduled Effects

**وضعیت:** IN PROGRESS  
**تاریخ شروع:** 2026-10-05

## Sprint Goal

Mission Runtime را از «فقط consequence فوری» به Runtime دارای consequence تأخیری و replayable ارتقا دهیم و Temporal را مطابق معماری FINAL به مسیر production اضافه کنیم.

Vertical Slice:

**ESCALATE → transactional ScheduledEffect → Outbox → NATS → Temporal starter → Workflow timer → Activity → deterministic World Effect → Runtime Event → factual Observation**

اصل:

> **API زمان را نگه نمی‌دارد و sleep نمی‌کند؛ Temporal زمان را orchestration می‌کند و Mission Engine فقط effect معتبر را commit می‌کند.**

## Gap بسته‌شونده

تا Sprint 9:
- همه consequenceها synchronous و فوری بودند؛
- `ScheduledEffect` از قرارداد FINAL وجود نداشت؛
- `WAITING_FOR_WORLD` رفتار اجرایی نداشت؛
- Temporal در Architecture FINAL بود اما در repo/runtime wiring نداشت.

Sprint 10 این چهار Gap را در یک Slice می‌بندد.

## Temporal Infrastructure

Runtime:
- Temporal Server `1.32.0`
- Python SDK `1.30+`
- Namespace: `default`
- Task Queue: `parcham-mission-runtime-v1`

Processes:
- `app.mission_runtime.scheduler`
- `app.mission_runtime.temporal_worker`

Ephemeral CI/Stage از صفر Temporal را کنار PostgreSQL/NATS/Keycloak بالا می‌آورد.

## ScheduledEffect Entity

Fields:
- scheduled_effect_id
- mission_instance_id
- origin_event_id
- effect_code
- status
- due_at
- world_effect
- candidate_message
- cancellable
- cancel_condition
- workflow_id
- created_at
- scheduled_at
- applied_at
- cancelled_at

Lifecycle:

**PENDING → SCHEDULED → APPLIED**

یا در صورت شرط cancellation:

**PENDING/SCHEDULED → CANCELLED**

## Transactional Scheduling

هنگام ESCALATE:
1. canonical immediate World/Actor effects اجرا می‌شوند.
2. `ScheduledEffect` با status=PENDING در همان transaction ساخته می‌شود.
3. Domain Event `mission.scheduled_effect_created.v1` با Transactional Outbox ثبت می‌شود.
4. فقط بعد از commit، Outbox event روی NATS منتشر می‌شود.
5. Scheduler consumer با Inbox idempotency event را می‌گیرد.
6. Temporal Workflow ID از ScheduledEffect ID مشتق می‌شود.
7. Workflow تا due_at با Temporal timer صبر می‌کند.
8. Activity اثر delayed را با DB lock و idempotency commit می‌کند.

## Acceptance Delayed Consequence

Effect:
`EXECUTIVE_RECOVERY_CHECKPOINT`

Delay:
`2 seconds` در acceptance mission.

Canonical delayed World Effect:

```json
{
  "stakeholder": {
    "checkpoint_status": "ARRIVED"
  },
  "mission": {
    "delayed_consequence_status": "CHECKPOINT_READY"
  }
}
```

Candidate message:

> Executive checkpoint فرا رسید؛ recovery status باید اکنون با داده جدید بازبینی شود.

## WAITING_FOR_WORLD

اگر Mission RUNNING باشد و ScheduledEffect با status `PENDING` یا `SCHEDULED` وجود داشته باشد:

```text
runtime_phase = WAITING_FOR_WORLD
```

بعد از APPLIED/CANCELLED:

```text
runtime_phase = ACTIVE
```

Final DECIDE در `WAITING_FOR_WORLD` از backend با `MISSION_WAITING_FOR_WORLD` رد می‌شود.

Frontend نیز Decision را در این phase غیرفعال می‌کند.

## Temporal Activity Commit Rules

Activity:
- ScheduledEffect را lock می‌کند.
- MissionInstance را lock می‌کند.
- APPLIED/CANCELLED را idempotent می‌بیند و دوباره mutation نمی‌کند.
- اگر cancel condition بگوید Mission باید RUNNING باشد و Mission terminal شده باشد، effect را CANCELLED می‌کند.
- World Effect فقط با `apply_world_effect` اجرا می‌شود.
- هر mutation معتبر world_state_version را افزایش می‌دهد.
- Runtime Event و Observation در همان transaction ثبت می‌شوند.

## Events

Outbox:
- `mission.scheduled_effect_created.v1`
- `mission.scheduled_effect_applied.v1`

Candidate-visible Runtime Event:
- `scheduled_effect.applied`

Internal-only field:
- `effect_applied`

Candidate serialization آن را حذف می‌کند.

Observation:
- `SCHEDULED_EFFECT_OBSERVED`

Observation فقط fact زمان‌بندی‌شده و World version transition را ثبت می‌کند؛ Capability judgment ندارد.

## Candidate UX

بعد از Escalation:
1. Candidate `RUNNING · WAITING_FOR_WORLD` را می‌بیند.
2. ScheduledEffect با status PENDING/SCHEDULED دیده می‌شود.
3. frontend فقط تا resolution effect به‌صورت semantic poll می‌کند.
4. Temporal effect را apply می‌کند.
5. ScheduledEffect به APPLIED می‌رسد.
6. Candidate `RUNNING · ACTIVE` را می‌بیند.
7. checkpoint جدید در Candidate-visible World State ظاهر می‌شود.
8. `SCHEDULED_EFFECT_OBSERVED` دیده می‌شود.
9. سپس Candidate می‌تواند Decision نهایی را commit کند.

## Governance Invariants

- API هیچ fixed sleep برای consequence ندارد.
- Candidate due_at یا world_effect arbitrary ارسال نمی‌کند.
- ScheduledEffect فقط از pinned Mission Version ساخته می‌شود.
- Scheduling از Transactional Outbox عبور می‌کند.
- NATS starter Inbox idempotent است.
- Temporal Workflow ID deterministic است.
- Activity DB mutation idempotent است.
- World mutation فقط Engine-owned rule است.
- Candidate internal `effect_applied` را نمی‌بیند.
- Temporal/LLM هیچ Profile/Evidence/Competency/Gate mutation ندارد.
- Scheduled consequence فقط Observation تولید می‌کند، نه Evidence.
- Candidate بعد از Mission همچنان UNPROVEN است.

## Stage Acceptance

Ephemeral Stage باید با Temporal واقعی اثبات کند:
1. Temporal service روی port 7233 آماده است.
2. scheduler و Temporal worker واقعی اجرا می‌شوند.
3. حداقل یک ScheduledEffect ساخته می‌شود.
4. workflow_id و scheduled_at ثبت می‌شوند.
5. ScheduledEffect به APPLIED می‌رسد.
6. `scheduled_effect.applied` وجود دارد.
7. Internal event دارای `effect_applied` است.
8. Candidate payload آن field را expose نمی‌کند.
9. `SCHEDULED_EFFECT_OBSERVED` وجود دارد.
10. World State delayed checkpoint را دارد.
11. scheduler Inbox event ثبت شده است.
12. Browser مسیر `WAITING_FOR_WORLD → ACTIVE` را مشاهده می‌کند.
13. Decision بعد از delayed effect، World State را از v3 به v4 می‌برد.
14. Mission COMPLETED می‌شود.
15. Candidate Proof همچنان UNPROVEN می‌ماند.

## Out of Scope

- ScheduledEffect manual cancellation UX
- trigger_condition به‌جای due_at
- multiple concurrent delayed effects
- probabilistic delayed effects
- DELEGATE
- CHANGE_SCOPE
- ALLOCATE_RESOURCE
- RUN_EXPERIMENT
- NO_ACTION
- Evidence Engine

## Definition of Done

- migration 0011
- Temporal infra/config
- transactional ScheduledEffect creation
- Outbox/NATS Temporal starter
- Temporal Workflow + Activity
- WAITING_FOR_WORLD enforcement
- candidate-safe ScheduledEffect response
- frontend semantic polling
- unit/API contract tests
- Live OIDC E2E
- CI Green
- Code Review PASS
- merge main
- Ephemeral Stage PASS
- Stage evidence recorded

> **Delayed consequence is part of the simulated world, not an assessment judgment.**
