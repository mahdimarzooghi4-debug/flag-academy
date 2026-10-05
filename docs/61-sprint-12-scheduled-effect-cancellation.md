# 61 — Sprint 12 ScheduledEffect Cancellation

**وضعیت:** IN PROGRESS  
**تاریخ شروع:** 2026-10-05

## Sprint Goal

`ScheduledEffect.cancellable` و `cancel_condition` را از contract غیرفعال به رفتار deterministic واقعی تبدیل کنیم تا consequenceهای آینده وقتی علت معتبر لغو آن‌ها در World State رخ می‌دهد، به‌صورت صریح و auditable بسته شوند.

زنجیره:

**World State Mutation → Cancel Condition Evaluation → ScheduledEffect PENDING → CANCELLED → Runtime Event → Factual Observation**

اصل:

> **A future consequence must be explicitly cancelled by the engine; it must not silently become unreachable.**

## Why this Sprint comes next

Sprint 11 اثبات کرد که یک Mission موفق می‌تواند بعد از Completion، deadline آینده را به‌صورت `PENDING` باقی بگذارد. این effect دیگر از Runtime قابل اجرا نیست، اما audit trail ناقص می‌ماند.

بنابراین Gap بعدی:
- deterministic cancellation
- audit reason
- no dangling deadline on successful terminal Missions

## Cancellation Contract v1

Candidate هیچ cancel command مستقیمی ندارد.

Mission Version می‌تواند برای effect قابل‌لغو این شرط محدود را تعریف کند:

```json
{
  "type": "WORLD_STATE_EQUALS",
  "path": "mission.decision_status",
  "equals": "COMMITTED",
  "reason_code": "DECISION_COMMITTED"
}
```

در v1:
- فقط `WORLD_STATE_EQUALS` مجاز است.
- `path` باید مشخص باشد.
- `equals` مقدار literal است.
- `reason_code` اجباری است.
- expression دلخواه، script، LLM و client-supplied condition ممنوع است.

## Acceptance Rule

`RECOVERY_DECISION_DEADLINE`:

- due_after_seconds = 1800
- terminal_status = TIME_EXPIRED
- cancellable = true

Cancel condition:

```text
mission.decision_status == COMMITTED
```

### Success Path

**ESCALATE → Executive Checkpoint → DECIDE**

Decision effect:
- mission.decision_status = COMMITTED

Engine:
1. World mutation را commit candidate می‌کند.
2. pending cancellable effects را lock می‌کند.
3. cancel condition را روی canonical World State ارزیابی می‌کند.
4. Recovery deadline را `CANCELLED` می‌کند.
5. `scheduled_effect.cancelled` ثبت می‌کند.
6. `SCHEDULED_EFFECT_CANCELLED_OBSERVED` ثبت می‌کند.
7. Mission به COMPLETED می‌رود.

نتیجه:
- deadline = CANCELLED
- هیچ deadline PENDING روی Mission COMPLETED وجود ندارد.

### Timeout Path

**ESCALATE → NO_ACTION WAIT_30_MINUTES**

چون `decision_status != COMMITTED`:
- cancel condition match نمی‌شود.
- deadline PENDING می‌ماند تا due شود.
- deadline APPLIED می‌شود.
- Mission = TIME_EXPIRED.

## Engine Trigger Points

Cancellation evaluation پس از World mutationهای معتبر اجرا می‌شود:
- Decision effect
- Escalation World effect
- ScheduledEffect-applied World effect

اگر یک applied effect باعث match شدن condition effect دیگری شود، effect دوم قبل از application بعدی CANCELLED می‌شود.

## Events

Candidate-visible:
- `scheduled_effect.cancelled`

Internal payload:
- `cancel_condition_matched`

Candidate payload:
- effect_code
- label
- due_at
- cancelled_at
- reason_code

Internal condition برای Candidate expose نمی‌شود.

Domain event:
- `mission.scheduled_effect_cancelled.v1`

## Observation

`SCHEDULED_EFFECT_CANCELLED_OBSERVED`

فقط facts:
- effect_code
- due_at
- cancelled_at
- reason_code
- world_version

هیچ Judgment، Evidence interpretation یا Capability assessment تولید نمی‌کند.

## Governance Invariants

- Candidate ScheduledEffect را مستقیماً cancel نمی‌کند.
- Candidate cancel condition ارسال نمی‌کند.
- شرط فقط از pinned Mission Version می‌آید.
- v1 فقط equality deterministic روی World State را می‌پذیرد.
- Effect فقط در وضعیت PENDING قابل لغو است.
- Effect APPLIED دوباره CANCELLED نمی‌شود.
- Effect CANCELLED هرگز apply نمی‌شود.
- cancellation و event/observation در همان DB transaction هستند.
- internal cancel condition برای Candidate مخفی است.
- cancellation هیچ Evidence/Proof/Profile/Gate mutation تولید نمی‌کند.

## Stage Acceptance

PostgreSQL + Live OIDC باید اثبات کند:
- success Mission همچنان COMPLETED است.
- timeout Mission همچنان TIME_EXPIRED است.
- حداقل یک `RECOVERY_DECISION_DEADLINE` = CANCELLED وجود دارد.
- حداقل یک `RECOVERY_DECISION_DEADLINE` = APPLIED وجود دارد.
- `scheduled_effect.cancelled` ثبت شده است.
- internal event دارای `cancel_condition_matched` است.
- `SCHEDULED_EFFECT_CANCELLED_OBSERVED` ثبت شده است.
- روی Missionهای COMPLETED هیچ deadline PENDING باقی نمانده است.
- Candidate internal condition را نمی‌بیند.
- Candidate همچنان UNPROVEN است.

## Out of Scope

- Candidate/operator manual cancellation
- OR/AND expression trees
- inequality/range conditions
- cancellation caused by external event adapters
- probabilistic cancellation
- Temporal automatic wake-up
- Evidence Engine

## Definition of Done

- deterministic cancellation evaluator
- strict cancellation schema
- cancellation after canonical World mutations
- event/observation audit
- candidate-safe visibility
- success-vs-timeout E2E
- Stage DB evidence
- CI Green
- Code Review PASS
- merge main
- Ephemeral Stage PASS
- acceptance evidence in GitHub

> **Pending means still possible; cancelled means explicitly made impossible by a recorded state transition.**
