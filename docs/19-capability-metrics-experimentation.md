# 19 — Capability 09: Metrics & Experimentation

**وضعیت:** FINAL  
**تاریخ تثبیت:** 2026-10-04

## تعریف

> **Metrics & Experimentation یعنی توانایی تبدیل Outcome به معیارهای قابل‌اندازه‌گیری، طراحی سنجش معتبر، و استفاده از Experiment برای کاهش عدم‌قطعیت درباره رابطه میان اقدام و نتیجه.**

Data Thinking واقعیت را از داده می‌فهمد؛ Metrics & Experimentation پیش از اقدام مشخص می‌کند موفقیت چیست و بعد بررسی می‌کند تغییر واقعاً اثر کرده یا فقط هم‌زمان اتفاق افتاده است.

## زنجیره استاندارد

**Outcome → Behavior → Metric → Baseline → Target → Guardrails → Intervention → Measurement → Interpretation → Decision**

پیش از Build باید روشن باشد:
- چه تغییری انتظار داریم؛
- برای چه Segmentی؛
- در چه بازه‌ای؛
- کدام Metric باید حرکت کند؛
- چه چیزی نباید خراب شود؛
- و چه Evidenceای Success / Failure را تعریف می‌کند.

## Metric Architecture

### Outcome Metric
نهایتاً چه نتیجه‌ای باید تغییر کند؟

### Input / Driver Metric
چه رفتارهایی Outcome را حرکت می‌دهند؟

### Leading Indicator
چه Signalی زودتر ظاهر می‌شود؟

### Lagging Indicator
نتیجه نهایی دیرتر کجا دیده می‌شود؟

### Guardrail Metric
چه چیزی نباید در ازای موفقیت Metric اصلی خراب شود؟

### Diagnostic Metric
اگر نتیجه تغییر کرد، برای فهم علت چه چیزی را بررسی می‌کنیم؟

اصل:
> **هر Metric مهم باید سایه خودش را هم داشته باشد.**

## Goodhart Protection

وقتی Metric تبدیل به Target می‌شود، امکان Gaming بالا می‌رود.

اصل:
> **هدف Metric بالا بردن عدد نیست؛ فهمیدن و بهبود واقعیتی است که عدد نمایندگی می‌کند.**

برای هر Metric باید پرسید:
> چه رفتاری ممکن است این عدد را بهتر کند ولی Outcome واقعی را بدتر کند؟

## Mission Ladder

### M1 — The Wrong Metric
تیم Success را با Activity Metric نامناسب می‌سنجد.

هدف:
- تفکیک Activity و Outcome
- انتخاب Metric تصمیم‌ساز

### M2 — Metric Tree
یک Outcome کلی باید به Driverها و رفتارهای قابل سنجش شکسته شود.

هدف:
- ساخت مدل سیستم محصول
- Leading/Lagging understanding
- Driver selection

### M3 — Guardrail Trap
Metric اصلی بهتر می‌شود اما Metric دیگری آسیب جدی می‌بیند.

هدف:
- Guardrail awareness
- جلوگیری از Success ظاهری

### M4 — Correlation Is Not Impact
Feature و Outcome هم‌زمان تغییر کرده‌اند اما Confounder وجود دارد.

هدف:
- تشخیص نیاز به Comparison / Control
- جلوگیری از ادعای Causality بدون Evidence

### M5 — Design the Experiment
فرد باید برای Hypothesis مشخص Experiment طراحی کند.

هدف:
- Population
- Control / Treatment
- Primary Metric
- Guardrail
- Duration
- Success criteria

### M6 — The Tempting Result
Result مثبت است اما Sample، Duration یا Segment مسئله دارد.

هدف:
- Caveat detection
- جلوگیری از «عدد مثبت = Ship»

### M7 — Negative Experiment
Experiment منفی است اما تیم روی ایده سرمایه‌گذاری کرده.

هدف:
- پذیرش Evidence
- جلوگیری از Metric Shopping
- انتخاب Stop / Iterate / Investigate

## Experiment Contract

پیش از شروع Experiment باید ثبت شود:
- Hypothesis
- Population / Segment
- Intervention
- Control / Comparison
- Primary Metric
- Secondary Metrics
- Guardrails
- Baseline
- Expected Effect
- Decision Rule
- Duration / Stopping Rule
- Known Risks

اصل:
> Decision Rule باید تا حد امکان پیش از دیدن Result تعریف شود.

## A/B Test همه‌چیز نیست

روش باید متناسب با سؤال و Constraint باشد.

گزینه‌های ممکن:
- A/B Test
- Pre/Post Analysis
- Cohort Comparison
- Holdout
- Phased Rollout
- Interrupted Time Series
- Qualitative + Behavioral Evidence

سؤال اصلی:
> **قوی‌ترین روش معقول برای پاسخ به این سؤال در محدودیت‌های موجود چیست؟**

## Statistical Literacy موردنیاز PM

فرد باید به سطح کاربردی بفهمد:
- Sample Size
- Noise
- Confidence / Uncertainty
- Multiple Comparisons
- Seasonality
- Novelty Effect
- Segment Effect
- Regression to the Mean

هدف حفظ فرمول نیست؛ جلوگیری از قطعیت دروغین است.

## Artifactهای اصلی

- Outcome Definition
- Metric Tree
- Metric Specification
- Baseline Report
- Target / Expected Change
- Guardrail Set
- Experiment Contract
- Experiment Design
- Analysis Plan
- Experiment Result
- Interpretation Memo
- Ship / Iterate / Stop Decision
- Experiment Registry

## Experiment Memory

Parcham OS باید حافظه سازمانی Experiment بسازد:

- چه Hypothesisهایی آزمایش شدند؟
- در چه Segmentهایی؟
- نتیجه چه بود؟
- چه Caveatهایی داشت؟
- چه چیزی یاد گرفتیم؟
- چه تصمیمی گرفته شد؟

این داده باید به Parcham AI و Business World Model قابل اتصال باشد.

## Red Flagها

- انتخاب Metric بعد از Release
- تغییر Success Criterion بعد از Result
- گزارش فقط Metricهای مثبت
- نداشتن Guardrail
- Vanity Metric
- Early stopping بعد از مثبت‌شدن
- ادامه Experiment تا مثبت‌شدن
- Segment fishing
- Statistical significance بدون Business significance
- ادعای Causality از Correlation
- نادیده‌گرفتن Seasonality
- Experiment بدون Hypothesis
- Metric Shopping

## نقش Parcham AI

### Learn Mode
آموزش:
- Metric Design
- Experiment Basics
- Causality
- Guardrails
- Bias
- Statistical Literacy

### Practice Mode
Challengeهای نمونه:
- اگر Metric اصلی بالا برود، چه چیزی ممکن است خراب شود؟
- چه Confounder دیگری ممکن است این Result را توضیح دهد؟
- Success Criterion را قبل از دیدن داده بنویس.

### Assessment Mode
AI نباید Experiment Result را برای فرد تفسیر کند.

وظیفه:
- تولید Dataset
- اجرای Control / Treatment
- ایجاد Noise / Eventها
- ارائه Requested Analysis inputs
- ثبت تصمیم و Interpretation فرد

### Real Project Mode
AI Experiment Copilot می‌تواند هشدار دهد:
- Sampling issue
- Guardrail anomaly
- Metric definition mismatch
- Early-stop risk
- Segment inconsistency

اما Product Manager مالک تصمیم نهایی است.

## Ethical Review

هر Experiment باید User Risk / Ethical Review داشته باشد، به‌خصوص در حوزه‌های:
- Pricing
- Trust
- Health
- Security
- Children
- Personal Data
- Sensitive Behavior

Experiment نباید صرفاً به دلیل تولید Data خوب، Risk ناموجه یا فریب مخرب برای کاربر ایجاد کند.

## شرایط عبور

برای عبور، باید در چند Context مختلف Evidence وجود داشته باشد که فرد:
- Outcome را به Metric معتبر تبدیل می‌کند؛
- Metric Tree می‌سازد؛
- Guardrail تعریف می‌کند؛
- Baseline و Success Criteria را پیش از Result مشخص می‌کند؛
- Correlation را به‌سادگی Causation نمی‌نامد؛
- حداقل یک Experiment معتبر طراحی می‌کند؛
- در حداقل یک Result مثبت Caveat مهم شناسایی می‌کند؛
- در حداقل یک Experiment منفی بدون Metric Shopping نتیجه را می‌پذیرد؛
- Decision از نوع Ship / Iterate / Stop را به Evidence متصل می‌کند؛
- و حداقل در یک Mission، به دلیل بدترشدن Guardrail، Success ظاهری Metric اصلی را رد می‌کند.

## اصل فرهنگی

> **پرچمدار عددی را انتخاب نمی‌کند که موفق به نظر برسد؛ معیاری را انتخاب می‌کند که حقیقت موفقیت را آشکار کند.**
