# 24 — Capability 14: System Building

**وضعیت:** FINAL  
**تاریخ تثبیت:** 2026-10-04

## تعریف

> **System Building یعنی توانایی تبدیل رفتارهای موفق و تصمیم‌های تکرارشونده به سازوکارهایی پایدار، قابل مشاهده و قابل بهبود؛ به‌گونه‌ای که کیفیت، مسئولیت و یادگیری کمتر به حافظه، Heroics و افراد خاص وابسته باشد.**

اصل:
> **سیستم خوب جای Judgment را نمی‌گیرد؛ Judgment را در جایی نگه می‌دارد که واقعاً لازم است.**

## تفاوت Process و System

**Process** می‌گوید چه مراحلی را طی کنیم.

**System** علاوه بر Process مشخص می‌کند:
- Input چیست؟
- Output چیست؟
- Owner کیست؟
- Decision Right کجاست؟
- Standard چیست؟
- Feedback از کجا می‌آید؟
- Failure چگونه دیده می‌شود؟
- Exception چگونه مدیریت می‌شود؟
- System چگونه خودش بهتر می‌شود؟

## جایگاه System Building در مدل پرچم

زنجیره بلوغ:

**Person-dependent → Team-dependent → System-enabled**

و در اتصال Capabilityها:

**Align People → Lead Team → Build System**

سؤال اصلی:
> **آیا کیفیت خوب حتی با تغییر افراد نیز تا حد قابل قبولی باقی می‌ماند؟**

## خروجی Capability

فرد باید بتواند:
- Failure Pattern تکرارشونده را تشخیص دهد؛
- Root Cause سیستمی را از خطای فردی جدا کند؛
- Workflow واقعی را Map کند؛
- Decision Pointها را مشخص کند؛
- Owner و Interfaceها را روشن کند؛
- Standard و Guardrail بسازد؛
- Feedback Loop طراحی کند؛
- Exception Handling تعریف کند؛
- Automation مناسب ایجاد کند؛
- System Health را اندازه بگیرد؛
- Processهای بی‌ارزش را حذف یا ساده کند.

## اصل ساخت System

> **System باید پاسخ به یک Pattern واقعی، Risk واقعی یا Scale Problem واقعی باشد.**

یک Incident منفرد لزوماً Process جدید نمی‌خواهد.

اما Failure تکرارشونده می‌تواند Signal یک System Gap باشد.

## System Opportunity

برای هر System پیشنهادی باید روشن باشد:
- Failure / Need
- Pattern
- Root Cause
- System Intervention
- Owner
- Signal
- Cost
- Retirement Rule

Processها باید امکان Retirement یا Redesign داشته باشند.

## Mission Ladder

### M1 — Repeated Failure
یک Failure مشخص چند بار تکرار شده است.

هدف:
- حرکت از Reminder به Mechanism
- تشخیص System Gap
- طراحی Intervention متناسب

### M2 — The Hero Dependency
یک فرد Context حیاتی را در ذهن خود نگه می‌دارد و نبودش کار را متوقف می‌کند.

هدف:
- کاهش Key-person dependency
- حذف Single Point of Human Failure
- استفاده متناسب از Runbook، Backup Owner، Pairing، Knowledge Transfer و Decision Record

### M3 — Broken Handoff
Roleها برداشت متفاوتی از Ready / Done یا اطلاعات موردنیاز دارند.

هدف:
- تشخیص Interface Problem
- طراحی Interface Contract با:
  - Input
  - Required Information
  - Owner
  - Acceptance
  - Next State

### M4 — Process Explosion
پس از Incidentهای متعدد، Approval و Checklist زیاد شده و Delivery کند شده است.

هدف:
- Simplification
- حذف Controlهای کم‌ارزش
- تشخیص اینکه کدام Step واقعاً Risk را کاهش می‌دهد

### M5 — Exception Case
System در حالت عادی کار می‌کند اما یک مورد خاص با Rule معمول سازگار نیست.

هدف:
- طراحی Exception Handling
- جلوگیری از Rule Breaking بی‌قاعده یا Blind Compliance

الگوی Exception:
**Exception Criteria → Approval → Documentation → Review**

### M6 — Scale Shock
تیم، Product یا Scope سازمان رشد می‌کند و Mechanism شفاهی دیگر Scale نمی‌شود.

هدف:
- طراحی Standard
- Role Clarity
- Interface
- Ownership Model
- Review Cadence
- Shared Artifact

### M7 — Design the Operating System
یک جریان مهم مانند:
**Product Discovery → Prioritization → Delivery → Release → Learning**
به فرد داده می‌شود.

هدف:
- طراحی Stages
- Entry Criteria
- Exit Criteria
- Owner
- Decision Rights
- Evidence
- Gates
- Feedback Loops
- Metrics
- Exceptions

### M8 — Remove Your Own System
System یا Process قبلی دیگر Value کافی ندارد.

هدف:
- Retire / Redesign
- جلوگیری از وابستگی هویتی به Process ساخته‌شده توسط خود فرد

## Building Blocks سیستم

هر System می‌تواند از این Building Blockها ساخته شود:
- State
- Trigger
- Owner
- Input
- Action
- Decision
- Standard
- Gate
- Output
- Feedback
- Exception
- Escalation
- Metric
- Learning Loop

این Building Blockها باید قابلیت ترجمه به Parcham OS را داشته باشند.

## Gates

Gate فقط وقتی ارزش دارد که عبور اشتباه از آن Risk معناداری ایجاد کند.

برای هر Gate باید پرسید:
> **این Gate دقیقاً چه Riskی را کنترل می‌کند؟**

اگر پاسخ روشن نیست، Gate باید Challenge یا حذف شود.

## Standards

Standard باید روشن کند:
> خوب یعنی چه؟

Standard نباید آن‌قدر جزئی شود که Judgment را خفه کند.

## Guardrail vs Rule

### Rule
Constraintی که در اغلب شرایط نباید نقض شود.

### Guardrail
Boundary تصمیم است که درون آن تیم آزادی عمل دارد.

اصل:
> رهبران خوب تا حد ممکن از Guardrailهای روشن به‌جای Ruleهای بی‌شمار استفاده می‌کنند.

## Feedback Loop

هر System باید بتواند خودش را اصلاح کند.

چرخه:
**Operate → Observe → Detect → Review → Improve**

System بدون Feedback Loop ناقص است.

## System Health

Signalهای مهم می‌توانند شامل:
- Lead Time
- Failure Rate
- Rework Rate
- Exception Rate
- Escalation Frequency
- Manual Intervention Rate
- Decision Latency
- Adoption
- Compliance
- Outcome Reliability

اصل:
> **System Health باید Outcome را هم ببیند، نه فقط Process Compliance را.**

## System Debt

سه نوع Debt در معماری پرچم اکنون عبارت‌اند از:

### Discovery Debt
Unknownهای حیاتی بدون کاهش کافی وارد Delivery شده‌اند.

### Leadership Debt
تیم برای سرعت کوتاه‌مدت به Leader وابسته شده است.

### System Debt
کار مهم به Manual Workaround، Knowledge پنهان، Interface مبهم یا Process شکننده وابسته است.

System Debt می‌تواند پذیرفته شود، اما باید Visible و قابل پیگیری باشد.

## Automation

ترتیب سالم:

**Understand → Simplify → Standardize → Automate**

اصل:
> **چیزی را که هنوز نمی‌فهمیم، فقط سریع‌تر نکنیم.**

Automation کردن Process بد فقط Failure را سریع‌تر می‌کند.

## Documentation

Documentation بخشی از System است، نه خود System.

Documentation خوب باید:
- قابل پیدا کردن باشد؛
- Current باشد؛
- Owner داشته باشد؛
- با Decision و Workflow واقعی مرتبط باشد.

## Artifactهای اصلی

- System Problem Brief
- Current-State Map
- Failure Pattern Log
- Root Cause Map
- Future-State Design
- Workflow / State Model
- Decision Rights
- Interface Contract
- Standard
- Gate Definition
- Guardrail Definition
- Exception Policy
- Escalation Path
- System Health Metrics
- Automation Candidate Map
- Runbook
- System Change Log
- System Review
- Retirement / Simplification Decision

## Red Flagها

- Process برای هر Incident
- Approval برای هر چیز
- System بدون Owner
- Rule بدون Risk
- Documentation بدون استفاده
- Automation کردن Process بد
- Checklist worship
- Process Compliance به‌جای Outcome
- One-size-fits-all system
- نداشتن Exception path
- Processهایی که هیچ‌کس دلیلشان را نمی‌داند
- System وابسته به یک فرد خاص
- Manual workaround دائمی
- افزودن Process برای پوشاندن ضعف Leadership
- استفاده از Process برای فرار از تصمیم سخت

اصل:
> **اگر برای هر Failure فقط Training اضافه کنیم، ممکن است Problem آموزشی نباشد؛ System Problem باشد.**

## نقش Parcham AI

### Learn Mode
آموزش:
- Systems Thinking
- Workflow Design
- Root Cause Analysis
- Operating Models
- Decision Rights
- Standard / Guardrail / Gate
- Feedback Loops
- Automation Thinking
- System Metrics

### Practice Mode
Challengeهای نمونه:
- این Failure فردی است یا Pattern سیستمی؟
- این Gate دقیقاً چه Riskی را کنترل می‌کند؟
- اگر این فرد فردا نباشد چه چیزی می‌شکند؟
- اگر این Process حذف شود چه اتفاقی می‌افتد؟
- کدام Step Value تولید نمی‌کند؟

### Assessment Mode
AI نباید System مطلوب را طراحی کند.

فرد باید System Intervention را طراحی کند و Simulator چند Cycle بعدی را اجرا کند.

Consequenceهای System باید واقعی باشند.

مثال:
- Failure ↓
- Lead Time ↑
- Frustration ↑
- Bypass Behavior ↑

فرد باید اثر System خود را مشاهده و در صورت نیاز اصلاح کند.

## Operating System Model

Parcham OS می‌تواند برای Business یک **Operating System Model** نگه دارد که شامل:
- Workflowها
- Decision Points
- Gates
- Owners
- Dependencies
- Bottlenecks
- Failure Patterns

باشد.

این مدل می‌تواند به Parcham AI امکان دهد Patternهای سیستمی و Bottleneckهای تکرارشونده را تشخیص دهد.

## Real Project Mode

AI System Copilot می‌تواند:
- Recurring failure را تشخیص دهد؛
- Process bottleneck را Flag کند؛
- Hidden dependency را پیدا کند؛
- Manual repeated work را Automation Candidate بداند؛
- Stale documentation را شناسایی کند؛
- Gate بدون Risk روشن را Challenge کند؛
- System metric degradation را هشدار دهد.

اصل:
> AI می‌تواند Pattern را ببیند؛ تصمیم طراحی سیستم مسئولیت انسان است.

## Human Override و Exception

Override یا Exception باید قابل Audit باشد:
- Who
- Why
- Risk accepted
- Duration
- Follow-up

هدف جلوگیری از Shadow Process است، نه ممنوع‌کردن Exception.

## شرایط عبور

برای عبور، باید در چند Context مختلف Evidence وجود داشته باشد که فرد:
- Failure Pattern تکرارشونده را از Incident منفرد تشخیص داده؛
- حداقل یک Root Cause سیستمی را پیدا کرده؛
- System Intervention متناسب طراحی کرده؛
- Owner، Decision Rights، Standard و Feedback Loop را روشن کرده؛
- حداقل یک Key-person dependency یا Manual dependency را کاهش داده؛
- حداقل یک Broken Handoff را با Interface روشن اصلاح کرده؛
- در یک مورد Process یا Gate اضافی را حذف یا Simplify کرده؛
- System خود را با Health Metric سنجیده و حداقل یک بار بر اساس Consequence واقعی اصلاح کرده؛
- حداقل یک System یا Process ساخته‌شده توسط خودش را به دلیل تغییر Context Retire یا Redesign کرده؛
- و در Mission نهایی، با تغییر چند نفر از تیم، کیفیت جریان اصلی به‌شکل جدی سقوط نکرده است.

## اصل فرهنگی

> **پرچمدار فقط مسئله امروز را حل نمی‌کند؛ سازوکاری می‌سازد که احتمال تکرار همان مسئله را کمتر کند.**
