# 14 — Capability 04: Data Thinking

**وضعیت:** FINAL  
**تاریخ تثبیت:** 2026-10-04

## تعریف

> **Data Thinking یعنی توانایی استفاده از داده برای فهم واقعیت، آزمون فرضیه و بهبود تصمیم؛ بدون افتادن در دام Vanity Metrics، Correlation ساده‌لوحانه یا عددسازی برای توجیه تصمیم.**

فرد لازم نیست Data Scientist باشد؛ اما باید بداند چه چیزی را اندازه بگیرد، چرا، با چه محدودیتی، و چه زمانی داده کافی یا قابل اعتماد نیست.

## خروجی Capability

فرد باید بتواند:
- سؤال کسب‌وکار را به سؤال داده تبدیل کند؛
- Metric مناسب انتخاب کند؛
- Leading و Lagging Indicator را تفکیک کند؛
- Funnel و Cohort را بفهمد؛
- Baseline بسازد؛
- Segmentهای مهم را جدا کند؛
- Correlation را با Causation اشتباه نگیرد؛
- کیفیت داده را بررسی کند؛
- Evidence مخالف فرض خود را پنهان نکند؛
- داده را به **Insight → Decision** تبدیل کند.

## Mission Ladder

### M1 — Vanity Dashboard
داشبوردی با اعداد ظاهراً مثبت ارائه می‌شود اما مسئله واقعی پشت آن پنهان است.

هدف:
- تشخیص Metric تصمیم‌ساز
- رد Vanity Metrics
- اتصال KPI به Outcome واقعی

### M2 — Broken Funnel
Conversion افت کرده و فرد باید Funnel را Breakdown کند.

هدف:
- یافتن محل واقعی Drop
- تعریف Baseline
- تفکیک Stageها
- تبدیل Observation به Insight

### M3 — Segment Trap
Average کلی خوب است اما یک Segment مهم افت جدی دارد.

هدف:
- جلوگیری از Average Blindness
- Segment Breakdown
- تشخیص Impact واقعی

### M4 — Conflicting Metrics
مثلاً Revenue رشد کرده اما Retention افت کرده است.

هدف:
- فهم Trade-off
- تشخیص Horizon زمانی
- جلوگیری از Optimizing یک KPI به قیمت آسیب به Outcome دیگر

### M5 — Dirty Data
داده ظاهراً نتیجه روشنی دارد اما کیفیت، تعریف یا Coverage داده مشکوک است.

هدف:
- Data Quality Check
- بررسی Tracking / Sampling / Missing Data
- جلوگیری از تصمیم روی داده نامعتبر

### M6 — Correlation Trap
دو متغیر هم‌زمان تغییر کرده‌اند اما رابطه علّی اثبات نشده است.

هدف:
- تفکیک Correlation و Causation
- ساخت Hypothesisهای جایگزین
- طراحی بررسی یا Experiment مناسب

## Artifactهای اصلی

- Metric Definition
- Metric Tree
- Funnel Analysis
- Cohort Analysis
- Segment Breakdown
- Baseline
- Data Quality Check
- Insight Memo
- Decision Recommendation

اصل:
> **Dashboard خروجی نیست؛ تصمیمی که از داده بهتر شده خروجی است.**

## Red Flagها

- انتخاب Metric صرفاً چون راحت اندازه‌گیری می‌شود
- Vanity Metrics
- Cherry-picking
- اتکا به Average بدون Segment
- Data dumping بدون Insight
- فرض اینکه «عدد دقیق» یعنی «واقعیت دقیق»
- Correlation = Causation
- نادیده‌گرفتن Missing Data
- ساخت نمودار برای دفاع از تصمیم قبلی
- تغییر تعریف KPI بعد از نتیجه نامطلوب

## نقش Parcham AI

### Learn Mode
AI می‌تواند آموزش دهد:
- Metric Design
- Leading / Lagging Indicators
- Funnel
- Cohort
- Segmentation
- Experiment Basics
- Data Bias
- Data Quality

### Practice Mode
نمونه Challengeها:
- اگر این Average را Segment کنیم چه می‌بینی؟
- کدام Metric واقعاً Outcome را نشان می‌دهد؟
- چه چیزی می‌تواند این Correlation را توضیح دهد؟
- چه Data Quality issueای ممکن است نتیجه را تغییر دهد؟

### Assessment Mode
AI نباید Insight را برای فرد استخراج کند.

وظیفه:
- ارائه Data Environment
- پاسخ به Queryهای معتبر
- فراهم‌کردن Breakdownها و Datasetهای قابل درخواست
- نگه‌داشتن بخشی از داده تا زمانی که فرد سؤال درست بپرسد

## Auditability of AI Analysis

اگر فرد از AI برای تحلیل داده استفاده می‌کند، باید قابل ردیابی باشد که:
- کدام بخش توسط AI تولید شده؛
- چه داده‌ای به AI داده شده؛
- چه Query یا Promptی استفاده شده؛
- خود فرد چه Judgmentی روی خروجی اعمال کرده؛
- کدام نتیجه نهایی مسئولیت انسانی دارد.

اصل:
> AI-generated analysis باید قابل Audit باشد و مسئولیت تصمیم نهایی با فرد باقی می‌ماند.

## Evidence

Evidence شامل:
- Metric selection
- Breakdownهای درخواستی
- Segmentهایی که بررسی شده
- Data Quality checks
- Hypothesisهای ساخته‌شده
- نحوه برخورد با Evidence مخالف
- Insightهای استخراج‌شده
- تصمیم یا تغییر Hypothesis ناشی از داده

## شرایط عبور

برای عبور، باید در چند Context مختلف Evidence وجود داشته باشد که فرد:
- Metric مناسب انتخاب می‌کند؛
- حداقل یک Vanity Metric را آگاهانه رد می‌کند؛
- داده را Segment می‌کند؛
- حداقل یک Data Quality Issue را پیش از تصمیم کشف می‌کند؛
- Correlation را به‌عنوان Causation اعلام نمی‌کند؛
- Insight را به Decision یا Hypothesis Change متصل می‌کند؛
- و در حداقل یک Mission با داده اولیه گمراه‌کننده، قبل از تصمیم آن را Challenge می‌کند.

## اصل فرهنگی

> **پرچمدار از داده برای اثبات خودش استفاده نمی‌کند؛ از داده برای نزدیک‌شدن به واقعیت استفاده می‌کند.**
