# 53 — Sprint 8 Actor State & COMMUNICATE

**وضعیت:** ACCEPTED  
**تاریخ شروع:** 2026-10-05  
**تاریخ پذیرش:** 2026-10-05

## Sprint Goal

اولین Actor Runtime واقعی را بسازیم تا Candidate بتواند با Actor تعریف‌شده در Mission تعامل کند و Actor State معتبر، versioned و audit-friendly تغییر کند.

زنجیره v1:

**Mission Actor Definition → ActorInstance → Candidate COMMUNICATE → Engine Validation → Deterministic Actor Effect → Actor Response → Observation**

اصل FINAL:

> **LLM may propose language later; only Mission Engine validates and mutates Actor State.**

## Scope

### ActorInstance

Entity runtime جدید:
- id
- mission_instance_id
- actor_key
- definition_name
- state
- state_version
- created_at
- updated_at

هر Actor Runtime Config در Mission Version یک ActorInstance مستقل در Start ایجاد می‌کند.

### Actor Runtime Definition

در `world_context.runtime_v1.actor_runtime` برای هر Actor:
- definition_name
- initial_state
- candidate_visible_paths
- communication_options

هر communication option:
- code
- label
- deterministic reply
- deterministic effect

### Candidate-visible Actor State

Canonical Actor State می‌تواند private field داشته باشد.

Acceptance Actor:
- trust_toward_candidate
- current_frustration
- commitment
- private_escalation_threshold

Candidate فقط allowlist زیر را می‌بیند:
- trust_toward_candidate
- current_frustration
- commitment

بنابراین:

> **Private Actor State remains canonical but is not Candidate-visible.**

### COMMUNICATE Action

Contract:
- action_type = COMMUNICATE
- target = actor_key
- payload.communication_code
- payload.utterance
- expected_world_version
- expected_actor_version
- idempotency_key

Runtime:
1. Mission Instance باید RUNNING باشد.
2. World State version باید stale نباشد.
3. ActorInstance با `FOR UPDATE` lock می‌شود.
4. expected_actor_version باید match باشد.
5. communication_code باید در Mission Version تعریف شده باشد.
6. reply/effect فقط از rule canonical خوانده می‌شود.
7. Engine Actor State را mutation می‌دهد.
8. actor state_version افزایش می‌یابد.
9. audit events و factual Observation ثبت می‌شوند.

## Events

Candidate-visible:
- `communication.sent`
- `actor.responded`

Internal domain event:
- `mission.actor_state_changed.v1`

Observation:
- `ACTOR_RESPONSE_OBSERVED`

## Acceptance Rule Example

Initial Actor State:
```json
{
  "trust_toward_candidate": 35,
  "current_frustration": 70,
  "commitment": "CONDITIONAL",
  "private_escalation_threshold": "LOW"
}
```

Communication:
`OWN_AND_ALIGN_RECOVERY`

Deterministic effect:
```json
{
  "trust_toward_candidate": 60,
  "current_frustration": 40,
  "commitment": "SUPPORTIVE"
}
```

Canonical reply:
«مالکیت روشن شد. برنامه بازیابی را با checkpoint مشخص جلو ببرید؛ من rollout را تا ارزیابی بعدی متوقف نگه می‌دارم.»

## Governance Invariants

- Actor State mutation فقط توسط Engine انجام می‌شود.
- Client نمی‌تواند arbitrary actor effect بفرستد.
- LLM هیچ write path مستقیم به ActorInstance ندارد.
- Actor effect اجازه mutation کلیدهای reserved را ندارد:
  - profile
  - evidence
  - competency
  - gate
  - world_state
- Actor State concurrency مستقل از World State concurrency کنترل می‌شود.
- stale expected_actor_version با 409 رد می‌شود.
- Candidate فقط Actor State allowlisted را می‌بیند.
- private actor state در DB می‌ماند ولی در Candidate response ظاهر نمی‌شود.
- internal `actor_effect_applied` برای audit در DB می‌ماند ولی Candidate event payload آن را expose نمی‌کند.
- COMMUNICATE هیچ Evidence یا Proof State تولید نمی‌کند.
- Observation factual است، Judgment نیست.
- Candidate بعد از Actor interaction همچنان UNPROVEN است.

## Product UX

Candidate:
1. Actorهای Mission را می‌بیند.
2. candidate-visible Actor State را می‌بیند.
3. پیام واقعی خودش را می‌نویسد.
4. communication strategy تعریف‌شده را انتخاب می‌کند.
5. response canonical را می‌بیند.
6. state version جدید Actor را می‌بیند.
7. Observation timeline interaction را می‌بیند.

## Stage Acceptance

Live OIDC + PostgreSQL باید اثبات کند:
1. ActorInstance در Mission Start ساخته شده است.
2. private actor state در PostgreSQL وجود دارد.
3. private actor state در Candidate UI دیده نمی‌شود.
4. Candidate COMMUNICATE واقعی ثبت می‌کند.
5. Actor state از v1 به v2 می‌رود.
6. trust = 60، frustration = 40، commitment = SUPPORTIVE می‌شود.
7. `communication.sent` و `actor.responded` ثبت می‌شوند.
8. internal event payload دارای `actor_effect_applied` است.
9. Candidate response `actor_effect_applied` را expose نمی‌کند.
10. `ACTOR_RESPONSE_OBSERVED` ثبت می‌شود.
11. Mission سپس با Decision کامل می‌شود.
12. Candidate Proof همچنان UNPROVEN باقی می‌ماند.

## Out of Scope

- LLM-generated Actor dialogue
- probabilistic Actor behavior
- multiple-turn freeform dialogue policy
- Actor-to-Actor interaction
- ESCALATE
- DELEGATE
- CHANGE_SCOPE
- ALLOCATE_RESOURCE
- RUN_EXPERIMENT
- NO_ACTION
- ScheduledEffect
- Evidence Engine

## Definition of Done

- migration 0010
- ActorInstance model
- deterministic actor effect domain rule
- COMMUNICATE backend path
- actor optimistic concurrency
- candidate-visible Actor projection
- Candidate UI
- domain/API tests
- Live OIDC E2E
- Stage DB evidence
- CI Green
- Code Review PASS
- merge main
- Ephemeral Stage PASS
- acceptance record in GitHub

> **Actor dialogue can be expressive; Actor State authority remains deterministic and engine-owned.**


## Acceptance Record

- Accepted implementation commit: `71337f351214aa1f12debf486b85fe7cd9552744`
- Main CI Run: `37271987906` — PASS
- Ephemeral Stage Run: `37271987912` — PASS
- Code Review: `docs/reviews/08-sprint-8-actor-state-communicate-code-review.md` — PASS
- Stage evidence: `docs/54-sprint-8-stage-acceptance.md`
