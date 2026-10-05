# 55 — Sprint 9 Deterministic Escalation

**وضعیت:** ACCEPTED  
**تاریخ شروع:** 2026-10-05  
**تاریخ پذیرش:** 2026-10-05

## Sprint Goal

Action پایه‌ی **ESCALATE** را به Mission Runtime واقعی تبدیل کنیم تا Candidate بتواند یک Escalation تعریف‌شده را به Actor مشخص اجرا کند و Engine به‌صورت deterministic هم World State و هم Actor State را تغییر دهد.

زنجیره:

**Candidate ESCALATE → Engine Validation → Canonical Rule → World Effect + Actor Effect → Runtime Events → Factual Observation**

اصل:

> **Candidate chooses the escalation; Mission Engine owns its consequences.**

## Runtime Contract

Action:
- `action_type = ESCALATE`
- `target = actor_key`
- `payload.escalation_code`
- `payload.rationale`
- `expected_world_version`
- `expected_actor_version`
- `idempotency_key`

Validation:
1. Mission Instance باید RUNNING باشد.
2. World State version باید match باشد.
3. Actor target باید روی همان Mission Instance وجود داشته باشد.
4. Actor State version باید match باشد.
5. escalation_code باید برای همان actor_key در Mission Version تعریف شده باشد.
6. Candidate حق ارسال world_effect یا actor_effect ندارد.
7. Engine effectها را از pinned Mission Version می‌خواند.

## Canonical Escalation Rule

Acceptance Mission:

```text
code = EXECUTIVE_RECOVERY_ESCALATION
actor_key = business_sponsor
```

World effect:

```json
{
  "stakeholder": { "executive_attention": "ENGAGED" },
  "mission": { "escalation_status": "EXECUTIVE_REVIEW" }
}
```

Actor effect:

```json
{
  "commitment": "EXECUTIVE_SPONSORSHIP"
}
```

Canonical response:
> Escalation پذیرفته شد. Executive attention فعال است و تصمیم بازیابی در checkpoint بعدی بازبینی می‌شود.

## State Changes

Before escalation:
- World v1
- Actor v2
- commitment = SUPPORTIVE

After escalation:
- World v2
- Actor v3
- stakeholder.executive_attention = ENGAGED
- mission.escalation_status = EXECUTIVE_REVIEW
- commitment = EXECUTIVE_SPONSORSHIP

بعد از Decision نهایی:
- World v3
- Mission COMPLETED

## Events

Candidate-visible:
- `escalation.requested`
- `escalation.accepted`

Internal audit payload روی `escalation.accepted`:
- `world_effect_applied`
- `actor_effect_applied`

این دو effect برای Candidate expose نمی‌شوند.

Domain event:
- `mission.escalation_processed.v1`

Observation:
- `ESCALATION_OBSERVED`

Observation فقط factهای version transition و escalation identity را نگه می‌دارد؛ Judgment یا Capability interpretation تولید نمی‌کند.

## Governance Invariants

- Candidate arbitrary World Effect ارسال نمی‌کند.
- Candidate arbitrary Actor Effect ارسال نمی‌کند.
- World/Actor mutation فقط Engine-owned rule است.
- stale World version با 409 رد می‌شود.
- stale Actor version با 409 رد می‌شود.
- Action idempotency از double mutation جلوگیری می‌کند.
- effectهای reserved برای Profile/Evidence/Competency/Gate همچنان ممنوع هستند.
- escalation event payload برای Candidate fail-closed است.
- internal applied effects در Candidate response دیده نمی‌شوند.
- ESCALATE هیچ Evidence یا Proof State تولید نمی‌کند.
- Candidate پس از Mission همچنان UNPROVEN است.

## Product UX

Candidate:
1. بعد از تعامل با Business Sponsor می‌تواند دلیل Escalation واقعی بنویسد.
2. Escalation strategy تعریف‌شده را انتخاب می‌کند.
3. World State جدید را می‌بیند.
4. Actor State جدید را می‌بیند.
5. canonical response را می‌بیند.
6. `ESCALATION_OBSERVED` را در Timeline می‌بیند.
7. سپس Decision نهایی Mission را انجام می‌دهد.

## Stage Acceptance

Ephemeral Stage باید با Live OIDC و PostgreSQL اثبات کند:
- حداقل یک CandidateAction با `ESCALATE`
- حداقل یک `escalation.accepted`
- internal event دارای هر دو applied effect
- حداقل یک `ESCALATION_OBSERVED`
- World State دارای `executive_attention=ENGAGED`
- World State دارای `escalation_status=EXECUTIVE_REVIEW`
- Actor State v3 یا بالاتر
- Actor commitment = `EXECUTIVE_SPONSORSHIP`
- Mission همچنان تا COMPLETED می‌رود
- Candidate Proof همچنان UNPROVEN است

## Out of Scope

- DELEGATE
- CHANGE_SCOPE
- ALLOCATE_RESOURCE
- RUN_EXPERIMENT
- NO_ACTION
- ScheduledEffect
- probabilistic runtime
- LLM-driven escalation
- Evidence Engine

## Definition of Done

- backend ESCALATE path
- deterministic world + actor mutation
- optimistic concurrency
- candidate-visible audit contract
- frontend escalation UX
- Live OIDC E2E
- Stage DB evidence
- CI Green
- Code Review PASS
- merge main
- Ephemeral Stage PASS
- acceptance record in GitHub

> **Escalation changes the simulated situation; it does not prove the Candidate.**


## Acceptance Record

- Accepted implementation commit: `f6fbc0ca5ec2f1613da48398776dd060160a3428`
- Main CI Run: `37274740428` — PASS
- Ephemeral Stage Run: `37274740391` — PASS
- Code Review: `docs/reviews/09-sprint-9-deterministic-escalation-code-review.md` — PASS
- Stage evidence: `docs/56-sprint-9-stage-acceptance.md`
