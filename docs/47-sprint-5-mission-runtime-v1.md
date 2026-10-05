# 47 — Sprint 5 Mission Runtime v1

**وضعیت:** ACCEPTED  
**تاریخ شروع:** 2026-10-05  
**تاریخ پذیرش:** 2026-10-05

## Sprint Goal

اولین Vertical Slice اجرایی Mission Runtime را بسازیم تا یک Candidate بتواند یک Mission Version فعال را با هسته deterministic اجرا کند و حاصل رفتار او به‌صورت Runtime Event و Observation factual ثبت شود، بدون اینکه Runtime مستقیماً Evidence، Proof State یا Flag Profile را تغییر دهد.

## Product Slice

**Active Mission Version → Mission Instance → Information Request → Candidate Decision → Deterministic Consequence → World State Transition → Observation → Replayable Audit**

این Sprint جای Evidence Engine را نمی‌گیرد.

## Scope v1

### Backend
- Mission Instance pinned to exact Mission Version
- Runtime lifecycle: CREATED → ELIGIBILITY_CHECK → READY → RUNNING → COMPLETED
- persistent simulation seed
- world_state + world_state_version
- optimistic World State conflict protection
- Candidate Action idempotency
- immutable Decision Record
- ordered Runtime Event stream
- factual Observation stream
- deterministic World Effect application
- explicit protection against direct mutation of:
  - Profile
  - Evidence
  - Competency
  - Gate

### Executable Action Types
در قرارداد Runtime همه Action Typeهای FINAL حفظ می‌شوند، اما Vertical Slice نخست فقط این دو رفتار را end-to-end اجرا می‌کند:
- REQUEST_INFORMATION
- DECIDE

سایر Action Typeها فعلاً contract-visible هستند و تا Vertical Slice بعدی executable نیستند.

### Frontend
Candidate:
1. Mission فعال را می‌بیند.
2. Mission Instance را شروع می‌کند.
3. Information قابل کشف را با Action صریح درخواست می‌کند.
4. Reasoning تصمیم را ثبت می‌کند.
5. تصمیم تعریف‌شده در World Model را commit می‌کند.
6. World State و نسخه آن را می‌بیند.
7. Observation Timeline و Audit Eventها را می‌بیند.
8. Proof State همچنان مستقل و UNPROVEN باقی می‌ماند.

## Deterministic Runtime Definition

Mission Design برای v1 یک بخش machine-readable در `world_context.runtime_v1` حمل می‌کند:
- initial_state
- decision_options
- decision_effects
- complete_after_decision

این بخش اجرای قطعی World Model را ممکن می‌کند و LLM در correctness مسیر Runtime هیچ وابستگی‌ای ندارد.

## Safety / Governance Invariants

- Mission Runtime هیچ API برای تغییر Flag Profile ندارد.
- Mission Runtime هیچ Accepted Evidence تولید نمی‌کند.
- Observation factual است و Judgment نیست.
- Reserved namespaces `profile`, `evidence`, `competency`, `gate` توسط World Effect قابل mutation نیستند.
- World State mutation فقط از effect تعریف‌شده در Mission Version انجام می‌شود.
- هر mutation معتبر `world_state_version` را افزایش می‌دهد.
- Action retry با idempotency key تکرار state mutation ایجاد نمی‌کند.
- stale action با `WORLD_STATE_VERSION_CONFLICT` رد می‌شود.

## Stage Acceptance

Ephemeral Stage باید با PostgreSQL واقعی و Live OIDC اثبات کند:
- Academy Admin Mission را Draft → Pilot → Validated → Active می‌کند.
- Candidate Mission فعال را start می‌کند.
- Information Request ثبت و canonical information آشکار می‌شود.
- Candidate Decision ثبت می‌شود.
- World State deterministic تغییر می‌کند.
- Mission به COMPLETED می‌رسد.
- PostgreSQL حداقل یک Mission Instance تکمیل‌شده دارد.
- حداقل دو Candidate Action وجود دارد.
- حداقل یک Decision Record وجود دارد.
- حداقل ۷ Runtime Event و ۳ Observation وجود دارد.
- Candidate Proof State بعد از Runtime همچنان UNPROVEN است.

## Out of Scope

- AI Actor Runtime
- delayed ScheduledEffect
- probabilistic rule execution
- Actor State mutation
- COMMUNICATE / ESCALATE / DELEGATE / CHANGE_SCOPE / ALLOCATE_RESOURCE / RUN_EXPERIMENT execution
- Evidence Interpretation
- Human Evidence Review
- Flag Profile mutation
- Gate evaluation
- Responsibility assignment

## Definition of Done

Sprint فقط وقتی Done/Accepted می‌شود که:
- backend + frontend vertical slice کامل باشد؛
- migration و contract tests وجود داشته باشد؛
- runtime invariants تست شده باشند؛
- live-browser E2E عبور کند؛
- CI Green باشد؛
- Code Review ثبت شود؛
- merge به main انجام شود؛
- Ephemeral Stage Acceptance Green باشد؛
- Stage evidence در GitHub Actions artifact ثبت شود.

> **Mission completion ≠ Proven Capability. Observation ≠ Accepted Evidence.**

## Acceptance Record

- Accepted implementation commit: `059a60c058128fe67a4fc6c55a87f2413e03ade4`
- Main CI Run: `37263630090` — PASS
- Ephemeral Stage Run: `37263630148` — PASS
- Code Review: `docs/reviews/05-sprint-5-mission-runtime-code-review.md` — PASS
- Stage evidence: `docs/48-sprint-5-stage-acceptance.md`
