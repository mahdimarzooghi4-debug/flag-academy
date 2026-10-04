# 21 — Capability 11: Delivery

**وضعیت:** FINAL  
**تاریخ تثبیت:** 2026-10-04

## تعریف

> **Delivery یعنی توانایی تبدیل Outcome و تصمیم محصول به نتیجه واقعی در محیطی چندتیمی، محدود و متغیر؛ بدون گم‌کردن هدف، کیفیت، مسئولیت و Feedback Loop.**

اصل:
> **Done یعنی Outcome قابل مشاهده؛ نه صرفاً Ticket بسته‌شده.**

## جایگاه Delivery در زنجیره تولید

Delivery باید با فرآیند مادر تولید محصول هم‌راستا باشد:

**Business → Technical → Scrum/Product Backlog → Sprint → Code → Code Review → Stage → QA/Testing → Release Approval → Production → Monitoring → Improvement**

Product Manager قرار نیست همه این مراحل را شخصاً انجام دهد؛ باید بداند:
- محصول اکنون در کدام مرحله است؛
- Owner هر مرحله چه کسی است؛
- چه چیزی مانع عبور است؛
- و چه زمانی خروجی واقعاً آماده مرحله بعد است.

اصل:
> مالکیت End-to-End به معنی انجام شخصی همه کارها نیست.

## خروجی Capability

فرد باید بتواند:
- Outcome را به Scope قابل اجرا تبدیل کند؛
- Success Criteria و Acceptance Boundary روشن کند؛
- Teamها و Dependencyها را بشناسد؛
- Delivery Risk را پیش از بحران کشف کند؛
- Scope / Time / Quality را آگاهانه Trade-off کند؛
- تصمیم‌ها را سریع و قابل ردیابی بگیرد؛
- Release Readiness را بفهمد؛
- Rollout و Rollback طراحی کند؛
- بعد از Production عملکرد واقعی را Monitor کند؛
- Delivery را با Release تمام‌شده فرض نکند.

## Delivery ≠ Feature Factory

چرخه مطلوب:

**Outcome → Scope → Build → Validate → Release → Observe → Learn → Improve**

نه:

**Requirement → Build → Release → Next Feature**

Feature Factory و Velocity بدون تغییر Outcome، Red Flag هستند.

## Mission Ladder

### M1 — From Outcome to Execution
به فرد یک Outcome داده می‌شود، نه Feature.

هدف:
- تبدیل Outcome به Scope
- Hypothesis
- Deliverables
- Dependencies
- Success Criteria

### M2 — The Dependency Web
چند تیم و سرویس وابسته وجود دارند و یکی از Dependencyها دچار تأخیر می‌شود.

هدف:
- Critical Path
- Parallelization
- Scope adaptation
- Escalation

### M3 — Scope Pressure
Deadline ثابت و Scope بیشتر از ظرفیت است.

هدف:
- Trade-off میان Time / Scope / Quality
- Scope reduction آگاهانه
- جلوگیری از Death March

اصل:
> فشار برنامه‌ریزی نباید با بدهی پنهان انسانی یا کیفی حل شود.

### M4 — Quality vs Deadline
QA مسئله مهمی پیدا کرده اما فشار برای Launch وجود دارد.

هدف:
- Severity
- User Risk
- Reversibility
- Business Cost
- Rollback capability
- Risk-based decision

### M5 — Release Incident
Release انجام شده و Error Rate یا Metric مهم خراب شده است.

هدف:
- Stabilize
- Decision Rights
- Rollback / Mitigation
- Stakeholder alignment
- Root cause after stabilization

### M6 — Successful Release, Failed Outcome
Release فنی موفق است اما Outcome تغییر نکرده.

هدف:
- تفکیک Shipping و Value Creation
- تصمیم Iterate / Investigate / Stop / Reframe

### M7 — End-to-End Delivery
فرد یک Initiative واقعی یا Simulation کامل را از تصمیم تا Production و Monitoring حمل می‌کند.

## Planning

Planning باید Unknown و Confidence را صریح کند.

ساختار:
- Known
- Unknown
- Dependency
- Risk
- Confidence

در صورت عدم قطعیت، Forecast می‌تواند Range داشته باشد.

مثال: Expected: 3–5 weeks / Medium confidence

نه تاریخ دقیق کاذب.

## Scope Management

Scope Reduction باید بر اساس **Minimum Coherent Scope** انجام شود:

> کوچک‌ترین Scopeای که هنوز Hypothesis یا Outcome اصلی را حفظ می‌کند.

هدف فقط کوچک‌کردن نیست؛ حفظ معنا و ارزش است.

## Definition of Ready / Done

### Ready for Build
حداقل باید روشن باشد:
- Problem
- Outcome
- Scope
- Main Assumption
- Acceptance Boundary
- Key Dependencies
- Measurement Plan

### Done for Product
حداقل:
- Quality Gate رد شده؛
- Release انجام شده؛
- Monitoring فعال است؛
- Outcome Measurement شروع شده؛
- Ownership بعد از Release مشخص است.

## Release Strategy

Release می‌تواند شامل:
- Internal
- Alpha
- Beta
- Feature Flag
- Percentage Rollout
- Segment Rollout
- Geography Rollout
- Full Release

هر Release مهم باید داشته باشد:
- Rollout Plan
- Monitoring
- Abort Condition
- Rollback Plan

## Artifactهای اصلی

- Delivery Brief
- Outcome / Scope Definition
- Execution Plan
- Delivery Backlog
- Dependency Map
- Critical Path
- Risk Log
- Decision Log
- Scope Change Log
- Release Readiness Checklist
- Rollout Plan
- Rollback / Mitigation Plan
- Monitoring Plan
- Launch Report
- Post-release Review
- Delivery Post-mortem

## Delivery Health

Parcham OS می‌تواند نگه دارد:
- Outcome Health
- Scope Health
- Dependency Health
- Quality Health
- Schedule Confidence
- Team Load
- Release Readiness
- Post-release Outcome

این Signalها باید برای Early Warning استفاده شوند، نه داشبورد تزئینی.

## Red Flagها

- Ticket completion = Success
- Feature Factory
- Roadmap shipping بدون Outcome
- Deadline قطعی بدون Confidence
- پنهان‌کردن Delay
- Scope creep دائمی
- اضافه‌کردن Scope بدون حذف چیز دیگر
- Death March
- Release بدون Monitoring
- Release بدون Rollback strategy
- دورزدن QA برای حفظ تاریخ
- Blame کردن یک‌طرفه Engineering یا Product
- Launch and forget
- Velocity worship
- تغییر Definition of Done برای سبزکردن Status

عبارت خطرناک:
> «فقط Release کنیم، بعداً درستش می‌کنیم.»

این فقط وقتی پذیرفتنی است که Risk، Cost و Recovery Plan روشن باشند.

## نقش Parcham AI

### Learn Mode
آموزش:
- Delivery Planning
- Scope Management
- Dependency Management
- Risk Management
- Release Strategy
- Monitoring
- Incident Basics
- Agile / Scrum principles
- Delivery Metrics

### Practice Mode
Challengeهای نمونه:
- اگر Deadline ثابت باشد چه چیزی را از Scope خارج می‌کنی؟
- Critical Path کدام است؟
- چه چیزی باعث Abort Release می‌شود؟
- اگر Dependency دو هفته دیر شود Plan B چیست؟

### Assessment Mode
AI نباید Execution Plan بهتر را پیشنهاد کند.

Simulation Director باید:
- Delay ایجاد کند؛
- Bug وارد کند؛
- Dependency بشکند؛
- Stakeholder pressure ایجاد کند؛
- Capacity تغییر دهد؛
- Production Signal تولید کند.

### Real Project Mode
AI Delivery Copilot می‌تواند:
- Blocked Dependency روی Critical Path را هشدار دهد؛
- Capacity mismatch را نشان دهد؛
- Monitoring gap را کشف کند؛
- تعارض Initiative با Outcome را Flag کند؛
- Riskهای بدون Owner را نشان دهد.

اصل:
> AI وضعیت را روشن می‌کند؛ انسان تصمیم می‌گیرد و مسئول آن می‌ماند.

## Delivery و Team Health

Team Health یک Constraint واقعی Delivery است.

Signalهای مهم:
- Sustainable Load
- Overtime Pattern
- Burnout Risk
- Rework
- Defect Rate

اصل:
> نتیجه گرفتن نباید با مصرف‌کردن انسان‌ها اشتباه گرفته شود.

## شرایط عبور

برای عبور، باید در چند Context مختلف Evidence وجود داشته باشد که فرد:
- Outcome را به Execution Plan قابل اجرا تبدیل می‌کند؛
- Dependency و Critical Path را مدیریت می‌کند؛
- Scope را با Capacity واقعی تطبیق می‌دهد؛
- حداقل یک بار تحت Deadline فشار، Scope را آگاهانه Reduce کرده بدون ازبین‌بردن Outcome اصلی؛
- Risk را پیش از بحران Escalate کرده؛
- Release / Rollback / Monitoring را طراحی کرده؛
- حداقل یک Incident یا Release Problem را مسئولانه مدیریت کرده؛
- و حداقل یک بار بعد از Release موفق اما Outcome ناموفق تصمیم خود را بازبینی کرده است.

## اصل فرهنگی

> **پرچمدار کار را برای بسته‌شدن تحویل نمی‌دهد؛ آن را تا رسیدن به نتیجه واقعی حمل می‌کند.**
