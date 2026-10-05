# 51 — Sprint 7 Candidate-visible Truth Boundary

**وضعیت:** IN PROGRESS  
**تاریخ شروع:** 2026-10-05

## Sprint Goal

مرز امنیتی و Assessment Integrity میان Canonical World Truth و آنچه Candidate مجاز است در Mission Workspace ببیند enforce شود.

اصل FINAL:

> **Mission Workspace فقط Candidate-visible truth را برمی‌گرداند و Hidden World Truth هرگز expose نمی‌شود.**

## Gap بسته‌شونده

Mission Runtime تا Sprint 6 کل `world_state` را در Candidate API برمی‌گرداند و payload خام Runtime Eventها را نیز expose می‌کرد. همچنین `simulation_seed` در Candidate response قرار داشت.

این رفتار با قرارداد FINAL ناسازگار بود و در Assessment می‌توانست:
- Hidden World Truth را افشا کند؛
- Consequence Rule داخلی را از `effect_applied` لو بدهد؛
- deterministic/probabilistic replay seed را در اختیار Candidate بگذارد؛
- Event یا Observation جدید را بدون visibility policy به UI عبور دهد.

## Candidate World Projection

Mission Version در `world_context.runtime_v1.candidate_visible_paths` pathهای مجاز را صریحاً تعریف می‌کند.

نمونه:

```text
business.rollout_status
technical.error_rate_percent
technical.rollback_available
technical.rollback_started
risk.level
mission.decision_status
```

Canonical state می‌تواند داده بیشتری داشته باشد، اما Candidate response فقط projection همین allowlist را دریافت می‌کند.

Policy:

> **No allowlist entry → no Candidate visibility.**

## Hidden canonical truth in acceptance Mission

Canonical World State شامل:

```text
technical.root_cause_code = DOWNSTREAM_DEPENDENCY
```

است، اما این path در `candidate_visible_paths` وجود ندارد.

Candidate می‌تواند فقط از مسیر Action معتبر `REQUEST_INFORMATION` محتوای canonical تعریف‌شده برای `Dependency trace` را دریافت کند.

بنابراین:

> **Hidden truth is not rendered merely because it exists in canonical state.**

## Runtime Event Boundary

Runtime Event در DB همچنان audit کامل داخلی را نگه می‌دارد.

Candidate API:
- فقط Event با `visibility=CANDIDATE` را بررسی می‌کند؛
- خود `event_type` نیز باید در allowlist Candidate باشد؛
- payload هر event_type مجاز را با allowlist مستقل sanitize می‌کند؛
- event_type ناشناخته به‌طور کامل از Candidate response حذف می‌شود.

مثال:
- DB event `decision.committed` می‌تواند `effect_applied` را برای Audit داخلی حفظ کند.
- Candidate response از همان event فقط `decision_code` را می‌گیرد.

## Observation Boundary

Candidate فقط Observation Typeهای explicit allowlisted را دریافت می‌کند:
- MISSION_STARTED
- INFORMATION_REQUESTED
- DECISION_COMMITTED

Observation Type ناشناخته fail-closed است و به Candidate response وارد نمی‌شود.

Payload Observation نیز per-type allowlist دارد.

## Simulation Seed

`simulation_seed` همچنان روی Mission Instance در PostgreSQL ذخیره می‌شود برای:
- Debug
- Audit
- Replay
- Reproducibility

اما از Candidate API و Candidate UI حذف می‌شود.

## Product UX

Candidate:
- فقط Candidate-visible World State را می‌بیند؛
- Hidden root cause را قبل از Information Action نمی‌بیند؛
- seed را نمی‌بیند؛
- Information discoverable را فقط پس از Action معتبر مشاهده می‌کند؛
- Observation factual و Audit event metadata مجاز را می‌بیند.

## Invariants

- Canonical World State در DB overwrite یا ناقص نمی‌شود.
- Candidate projection از canonical state مشتق می‌شود، نه بالعکس.
- Hidden path بدون allowlist هرگز در Candidate response ظاهر نمی‌شود.
- Runtime Event audit داخلی می‌تواند richer از Candidate event payload باشد.
- Unknown Runtime Event Type برای Candidate fail-closed است و اصلاً serialize نمی‌شود.
- Unknown Observation Type برای Candidate fail-closed است.
- `effect_applied` در Candidate event payload افشا نمی‌شود.
- `simulation_seed` internal-only است.
- REQUEST_INFORMATION تنها اطلاعاتی را reveal می‌کند که Mission Design canonical تعریف کرده است.
- Truth Boundary هیچ Evidence، Proof State، Gate یا Flag Profile را تغییر نمی‌دهد.

## Stage Acceptance

Live OIDC + PostgreSQL باید اثبات کند:
1. Canonical Mission Instance در DB دارای `technical.root_cause_code=DOWNSTREAM_DEPENDENCY` است.
2. Candidate Workspace قبل و بعد از runtime آن raw hidden code را نمایش نمی‌دهد.
3. Candidate-visible state فقط pathهای allowlisted را نمایش می‌دهد.
4. Candidate با REQUEST_INFORMATION اطلاعات discoverable را به‌صورت صریح دریافت می‌کند.
5. `simulation_seed` در DB وجود دارد اما Candidate UI/API contract آن را expose نمی‌کند.
6. Internal decision event در DB `effect_applied` را برای audit حفظ می‌کند.
7. Candidate runtime تا COMPLETED پیش می‌رود.
8. Candidate Proof همچنان UNPROVEN می‌ماند.

## Out of Scope

- Actor State / Actor Runtime
- COMMUNICATE
- ESCALATE / DELEGATE / CHANGE_SCOPE / ALLOCATE_RESOURCE / RUN_EXPERIMENT / NO_ACTION
- ScheduledEffect
- probabilistic runtime
- Evidence Engine

## Definition of Done

- domain projection + fail-closed sanitizer tests
- Candidate API truth boundary
- Candidate UI language updated
- Live OIDC browser acceptance
- Stage DB evidence proving hidden canonical state is retained internally
- CI Green
- Code Review PASS
- merge main
- Ephemeral Stage PASS
- acceptance evidence recorded in GitHub

> **Canonical truth may exist without being Candidate-visible. Visibility is explicit policy, never an accidental consequence of serialization.**
