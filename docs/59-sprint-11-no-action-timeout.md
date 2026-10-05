# 59 — Sprint 11 Explicit NO_ACTION & Timeout

**وضعیت:** IN PROGRESS  
**تاریخ شروع:** 2026-10-05

## Sprint Goal

`NO_ACTION` را از یک مقدار صرف در Action enum به یک رفتار واقعی، auditable و دارای consequence زمانی تبدیل کنیم و اولین terminal timeout policy را با `TIME_EXPIRED` اجرا کنیم.

زنجیره:

**Candidate NO_ACTION → Canonical Wait Policy → Simulation Time Advance → Due Consequences → Deadline ScheduledEffect → TIME_EXPIRED → Factual Observations**

اصل:

> **No Action is still an Action. Absence of action must never be inferred from absence of logs.**

## Why this Sprint comes next

Sprint 10 temporal foundation را ساخت:
- simulation clock
- ScheduledEffect persistence
- deterministic due processing
- delayed consequence audit

بدون این foundation، `NO_ACTION` فقط یک دکمه نمایشی بود.

Sprint 11 از همان engine استفاده می‌کند تا cost of delay واقعی باشد.

## NO_ACTION Contract

Candidate Action:

```text
action_type = NO_ACTION
payload.no_action_code
payload.rationale
expected_world_version
idempotency_key
```

Candidate:
- arbitrary duration ارسال نمی‌کند؛
- arbitrary deadline ارسال نمی‌کند؛
- arbitrary effect ارسال نمی‌کند.

Mission Version option:

```json
{
  "code": "WAIT_30_MINUTES",
  "label": "۳۰ دقیقه بدون اقدام جدید صبر می‌کنم",
  "wait_seconds": 1800
}
```

Engine فقط همین canonical duration را اجرا می‌کند.

## Deadline ScheduledEffect

Escalation اکنون دو delayed effect می‌سازد:

### 1. Executive Checkpoint
```text
effect_code = EXECUTIVE_CHECKPOINT_DUE
due_after_seconds = 900
terminal_status = null
```

### 2. Recovery Decision Deadline
```text
effect_code = RECOVERY_DECISION_DEADLINE
due_after_seconds = 1800
terminal_status = TIME_EXPIRED
```

Deadline effect:

```json
{
  "risk": { "level": "CRITICAL" },
  "mission": {
    "decision_status": "EXPIRED",
    "escalation_status": "DEADLINE_MISSED"
  }
}
```

## Scheduled Terminal Status

Migration `0012` به `ScheduledEffect` فیلد زیر را اضافه می‌کند:

- `terminal_status` nullable

در v1 تنها terminal status مجاز برای ScheduledEffect:

- `TIME_EXPIRED`

Engine پس از اعمال effect:
1. World State را mutate می‌کند.
2. world_state_version را افزایش می‌دهد.
3. ScheduledEffect را APPLIED می‌کند.
4. Mission را از RUNNING به TIME_EXPIRED می‌برد.
5. Assignment را COMPLETED می‌کند.
6. Runtime Event و Observation factual می‌سازد.

## Shared Time Engine

`advance-to-next-event` و `NO_ACTION` هر دو از یک shared scheduled-effect execution path استفاده می‌کنند.

تفاوت:
- `advance-to-next-event`: فقط تا نزدیک‌ترین due event می‌رود.
- `NO_ACTION`: تا target time تعریف‌شده در canonical no-action option می‌رود و تمام effectهای due تا آن لحظه را به ترتیب deterministic اعمال می‌کند.

Client هیچ clock time دلخواهی تعیین نمی‌کند.

## Events

Candidate-visible:
- `no_action.committed`
- `simulation.time_advanced`
- `scheduled_effect.applied`
- `mission.time_expired`

Domain event:
- `mission.time_expired.v1`

## Observations

- `NO_ACTION_OBSERVED`
- `SCHEDULED_EFFECT_OBSERVED`
- `MISSION_TIME_EXPIRED`

Observationها فقط facts را ثبت می‌کنند:
- no_action_code
- simulation time before/after
- effect_code
- deadline time
- world version before/after

هیچ Judgment یا Capability interpretation تولید نمی‌شود.

## Acceptance Design

برای جلوگیری از regression، Stage دو Mission Instance واقعی می‌سازد.

### Instance A — success regression
**Start → COMMUNICATE → ESCALATE → next checkpoint → Information Request → DECIDE → COMPLETED**

این مسیر Sprintهای 5–10 را حفظ می‌کند.

### Instance B — cost-of-delay
**Start → ESCALATE → NO_ACTION WAIT_30_MINUTES → Checkpoint due → Deadline due → TIME_EXPIRED**

Result:
- risk = CRITICAL
- mission.decision_status = EXPIRED
- mission.escalation_status = DEADLINE_MISSED
- Mission status = TIME_EXPIRED
- Assignment status = COMPLETED
- Proof remains UNPROVEN

## Governance Invariants

- NO_ACTION explicit CandidateAction است.
- rationale برای NO_ACTION اجباری است.
- Candidate duration دلخواه ارسال نمی‌کند.
- Candidate deadline دلخواه ارسال نمی‌کند.
- Candidate effect دلخواه ارسال نمی‌کند.
- wait duration فقط از pinned Mission Version می‌آید.
- timeout فقط از Engine-owned ScheduledEffect می‌آید.
- stale world version با 409 رد می‌شود.
- command retry idempotent است.
- TIME_EXPIRED یک World/Mission outcome است؛ Candidate Failure نیست.
- Mission TIME_EXPIRED هیچ Evidence یا Proof State تولید نمی‌کند.
- Runtime همچنان Profile/Evidence/Competency/Gate را مستقیم mutate نمی‌کند.
- Candidate بعد از timeout همچنان UNPROVEN است.

## Stage Acceptance

PostgreSQL + Live OIDC باید اثبات کند:
- حداقل دو Mission Instance وجود دارد.
- حداقل یک Mission `COMPLETED` است.
- حداقل یک Mission `TIME_EXPIRED` است.
- حداقل یک CandidateAction با `NO_ACTION` وجود دارد.
- `no_action.committed` ثبت شده است.
- `NO_ACTION_OBSERVED` ثبت شده است.
- `RECOVERY_DECISION_DEADLINE` با `terminal_status=TIME_EXPIRED` به APPLIED رسیده است.
- `mission.time_expired` ثبت شده است.
- `MISSION_TIME_EXPIRED` ثبت شده است.
- timeout World State دارای `risk.level=CRITICAL` است.
- timeout World State دارای `decision_status=EXPIRED` است.
- timeout World State دارای `escalation_status=DEADLINE_MISSED` است.
- هر دو Assignment بسته می‌شوند.
- Candidate Proof همچنان UNPROVEN است.

## Out of Scope

- ScheduledEffect cancellation
- trigger_condition-only effects
- DELEGATE
- CHANGE_SCOPE
- ALLOCATE_RESOURCE
- RUN_EXPERIMENT
- probabilistic runtime
- automatic Temporal wake-up
- Evidence Engine

## Definition of Done

- migration `0012`
- ScheduledEffect terminal status
- shared deterministic clock/effect execution
- executable NO_ACTION
- timeout lifecycle
- Candidate UX
- API/domain tests
- dual-path Live OIDC E2E
- Stage SQL evidence
- CI Green
- Code Review PASS
- merge main
- Ephemeral Stage PASS
- acceptance evidence in GitHub

> **Waiting is a choice only when the system records what was known, how long was waited, and what consequence became due.**
