# 63 — Sprint 13 State-triggered Scheduled Effects

**وضعیت:** ACCEPTED  
**تاریخ شروع:** 2026-10-05  
**تاریخ پذیرش:** 2026-10-05

## Sprint Goal

نیمه دوم قرارداد `ScheduledEffect` را اجرایی کنیم تا consequence فقط با گذر زمان فعال نشود و بتواند با یک تغییر معتبر در Canonical World State نیز به‌صورت deterministic فعال شود.

زنجیره:

**Canonical World Mutation → Trigger Condition Evaluation → ScheduledEffect PENDING → APPLIED → World Mutation → Runtime Event → Factual Observation**

اصل:

> **A consequence may become due because time passed or because the world changed; both triggers must be explicit, deterministic and auditable.**

## Why this Sprint comes next

قرارداد FINAL Runtime از ابتدا برای ScheduledEffect این مدل را تعریف کرده است:

```text
due_at / trigger_condition
```

Sprintهای 10 تا 12:
- due-time execution
- explicit NO_ACTION / TIME_EXPIRED
- deterministic cancellation

را تکمیل کردند.

Gap باقی‌مانده این بود که `trigger_condition` هنوز persistence/execution واقعی نداشت.

## Trigger Contract v1

هر ScheduledEffect دقیقاً یکی از این دو trigger را دارد:

### Timed

```text
due_at != null
trigger_condition = null
```

### State-triggered

```text
due_at = null
trigger_condition != null
```

PostgreSQL با Check Constraint این XOR را enforce می‌کند.

## State Trigger Schema v1

فقط این shape مجاز است:

```json
{
  "type": "WORLD_STATE_EQUALS",
  "path": "mission.decision_status",
  "equals": "COMMITTED"
}
```

در v1:
- فقط `WORLD_STATE_EQUALS`
- path صریح
- literal equality
- بدون script
- بدون expression tree
- بدون LLM decision
- بدون client-supplied trigger

## Persistence

Migration `0013`:
- `ScheduledEffect.due_at` nullable می‌شود.
- `ScheduledEffect.trigger_condition` JSONB nullable اضافه می‌شود.
- constraint:
  `(due_at IS NOT NULL) <> (trigger_condition IS NOT NULL)`

Effect با دو trigger یا بدون trigger در PostgreSQL نامعتبر است.

## State-trigger Execution

پس از World mutation معتبر، Engine:
1. cancellation ruleهای PENDING را evaluate می‌کند.
2. state-triggered effectهای PENDING را با lock می‌خواند.
3. first matching effect را deterministic بر اساس creation order انتخاب می‌کند.
4. effect را روی Canonical World State اعمال می‌کند.
5. world_state_version را افزایش می‌دهد.
6. effect را APPLIED می‌کند.
7. Event و Observation factual می‌سازد.
8. دوباره cancellation و trigger evaluation را اجرا می‌کند تا fixed point برسد.

هر effect فقط یک بار از PENDING خارج می‌شود؛ بنابراین chain قابل audit و finite است.

## Trigger Points

State-trigger evaluation بعد از:
- Escalation World Effect
- Decision World Effect
- Timed ScheduledEffect World Effect
- State-triggered ScheduledEffect World Effect

انجام می‌شود.

## Acceptance Rule

Escalation یک consequence شرطی جدید می‌سازد:

```text
effect_code = RECOVERY_COMMITMENT_BROADCAST
trigger_mode = STATE_TRIGGERED
trigger: mission.decision_status == COMMITTED
effect: stakeholder.recovery_signal = BROADCAST
```

Cancel condition:

```text
mission.decision_status == EXPIRED
reason = DECISION_EXPIRED
```

### Success Path

**ESCALATE → checkpoint → DECIDE(COMMITTED)**

Engine:
- deadline زمانی را CANCEL می‌کند.
- `RECOVERY_COMMITMENT_BROADCAST` را بدون advance clock APPLY می‌کند.
- `stakeholder.recovery_signal = BROADCAST`
- Mission → COMPLETED

### Timeout Path

**ESCALATE → NO_ACTION → deadline → decision_status=EXPIRED**

Engine:
- state-triggered broadcast condition match نمی‌شود.
- cancel condition `EXPIRED` match می‌شود.
- broadcast effect → CANCELLED
- `recovery_signal = NOT_BROADCAST`
- Mission → TIME_EXPIRED

## Candidate Boundary

Candidate می‌بیند:
- effect_code
- label
- status
- trigger_mode = DUE_AT | STATE_TRIGGERED
- due_at برای timed effect

Candidate نمی‌بیند:
- `trigger_condition`
- `trigger_condition_matched`
- `effect_applied`
- internal cancellation condition

> **Candidate can observe that a consequence was state-triggered without seeing the hidden rule that triggered it.**

## Events

`scheduled_effect.created`:
- Candidate-visible: effect identity, due_at, trigger_mode
- Internal: trigger definition retained

`scheduled_effect.applied`:
- `trigger_type = STATE_TRIGGERED` for state effects
- Internal: `trigger_condition_matched`
- Candidate-safe payload omits rule internals

Domain event:
- `mission.scheduled_effect_applied.v1`

## Observation

Existing `SCHEDULED_EFFECT_OBSERVED` remains factual and now includes `trigger_mode`.

No judgment, Evidence interpretation or Capability score is created.

## Governance Invariants

- Every ScheduledEffect has exactly one trigger source.
- Candidate cannot author or mutate trigger condition.
- Trigger comes from exact pinned Mission Version.
- state trigger schema is bounded and deterministic.
- state-triggered effect does not advance simulation clock.
- clock advance endpoints ignore state-triggered effects.
- NO_ACTION only reasons over timed effects.
- cancellation is evaluated before state-trigger application after the causing mutation.
- terminal status remains timed-only in v1; state-triggered `TIME_EXPIRED` is rejected.
- internal rule/effect payloads remain hidden from Candidate.
- state-triggered consequences never mutate Evidence/Profile/Competency/Gate namespaces.

## Stage Acceptance

PostgreSQL + Live OIDC must prove:
- at least two `RECOVERY_COMMITMENT_BROADCAST` effects exist.
- their `due_at IS NULL` and `trigger_condition IS NOT NULL`.
- success path has one broadcast effect APPLIED.
- timeout path has one broadcast effect CANCELLED.
- state-triggered apply RuntimeEvent exists with internal `trigger_condition_matched`.
- Candidate Observation exists with `trigger_mode=STATE_TRIGGERED`.
- COMPLETED Mission has `recovery_signal=BROADCAST`.
- TIME_EXPIRED Mission has `recovery_signal=NOT_BROADCAST`.
- no state-trigger effect remains PENDING on terminal Missions.
- zero ScheduledEffect rows violate exactly-one-trigger invariant.
- Candidate does not see trigger rule internals.
- Candidate remains UNPROVEN.

## Out of Scope

- OR/AND trigger expression trees
- inequality/range conditions
- Actor-state triggers
- external event triggers
- probabilistic triggers
- Temporal automatic wake-up
- DELEGATE / CHANGE_SCOPE / ALLOCATE_RESOURCE / RUN_EXPERIMENT
- Evidence Engine

## Definition of Done

- migration `0013`
- DB trigger XOR invariant
- strict state-trigger schema
- deterministic fixed-point execution
- timed/state trigger isolation
- candidate-safe trigger-mode contract
- dual-path E2E
- Stage SQL evidence
- CI Green
- Code Review PASS
- merge main
- Ephemeral Stage PASS
- acceptance evidence in GitHub

> **Time is one trigger; state is another. Neither may become an implicit source of truth.**


## Acceptance Record

- Accepted implementation commit: `c3bb447dec3e1c2c5c8968a78075bd171fd8976e`
- Main CI Run: `37304079338` — PASS
- Ephemeral Stage Run: `37304079367` — PASS
- Code Review: `docs/reviews/13-sprint-13-state-triggered-effects-code-review.md` — PASS
- Stage evidence: `docs/64-sprint-13-stage-acceptance.md`
