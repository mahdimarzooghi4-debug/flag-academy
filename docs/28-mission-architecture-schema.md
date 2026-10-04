# 28 — Mission Architecture & Mission Schema

**وضعیت:** FINAL  
**تاریخ تثبیت:** 2026-10-04

## تعریف

> **Mission یک محیط هدفمند و محدود است که Candidate در آن باید با اطلاعات، محدودیت، Actorها و Trade-offهای واقعی تصمیم بگیرد و رفتار او Evidence قابل مشاهده تولید کند.**

اصل:
> **Mission برای گرفتن جواب درست ساخته نمی‌شود؛ برای آشکارشدن الگوی تصمیم و رفتار ساخته می‌شود.**

Mission واحد اصلی تجربه، تمرین، سنجش و تولید Evidence در Parcham OS است.

---

## 1. Mission Template vs Mission Instance

### Mission Template
تعریف قابل‌استفاده مجدد Mission است و مشخص می‌کند:
- Behaviourهای هدف
- Eventها
- Constraints
- Evidence Opportunities
- Actor model
- Replay pattern
- Difficulty envelope

### Mission Instance
اجرای واقعی Template برای یک Candidate، Business World و Context مشخص است.

اصل:
> **Template ثابت‌تر است؛ Instance متناسب با Candidate، Business World و Replay تغییر می‌کند.**

---

## 2. Mission Schema سطح بالا

هر Mission Template حداقل شامل:
- Identity
- Purpose
- World Context
- Objective
- Scope
- Capabilities
- Competencies
- Gate Opportunities
- Actors
- Information State
- Constraints
- Resources
- Decision Points
- Events
- Evidence Opportunities
- Consequences
- Completion Conditions
- Difficulty
- AI Mode Policy
- Replay Design
- Safety / Ethics
- Version

---

## 3. Identity & Versioning

Fieldهای پایه:
- mission_template_id
- mission_family
- version
- title
- status

Lifecycle:
**DRAFT → PILOT → VALIDATED → ACTIVE → RETIRED**

هر Mission Instance باید به Version دقیق Template اجراشده متصل بماند.

Versionهای مهم:
- Definition Version
- World Model Version
- Evidence Mapping Version
- AI Policy Version

Missionهای قبلی نباید با Update جدید overwrite شوند.

---

## 4. Purpose

طراحی Mission باید از Behaviour شروع شود، نه Story.

اصل:
> **Behaviour first → Scenario second**

هر Mission باید روشن کند:
- چه Behaviourهایی باید فرصت بروز داشته باشند؟
- چه Capability/Competency/Gateهایی هدف هستند؟
- چه نوع Evidence قابل مشاهده باید ایجاد شود؟

---

## 5. Primary vs Secondary Capability

### Primary Capability
Mission عمداً برای سنجش آن طراحی شده است.

### Secondary Capability
Mission می‌تواند Evidence جانبی برای آن ایجاد کند.

Evidence Capability اصلی معمولاً Strength بالاتری دارد، مگر Behaviour جانبی به‌طور مستقیم و قوی مشاهده شود.

---

## 6. Gate Opportunity

Mission می‌تواند Gate Opportunity داشته باشد، اما:

> **Gate Opportunity ≠ Gate Evidence**

Gate Evidence فقط در صورت بروز Behaviour واقعی ایجاد می‌شود.

---

## 7. World Context

World Context می‌تواند شامل:
- Business Model
- Product
- Market
- Customer Segments
- Team
- Technology
- Financial State
- Organization Structure
- Current Strategy
- Existing Commitments

دو مفهوم باید جدا بمانند:

### World Truth
واقعیت واقعی Simulation.

### Candidate Information State
آنچه Candidate اکنون می‌داند.

---

## 8. Information State

هر Information Item یکی از وضعیت‌های زیر را دارد:
- Available by default
- Discoverable
- Restricted
- Unavailable
- Misleading / Noisy

Information Request خودش Event و Evidence است.

باید ثبت شود:
- چه اطلاعاتی درخواست شد؛
- چه زمانی؛
- با چه Costی؛
- و آیا واقعاً Decision-relevant بود.

---

## 9. No Hidden Required Answer

Mission نباید یک «جواب پنهان طراح» داشته باشد.

اصل:
> چند Decision متفاوت می‌توانند معتبر باشند، اگر Reasoning و Trade-off قابل دفاع باشند.

باید تفکیک شود:
- Invalid Behaviour
- Alternative Valid Decisions

---

## 10. Actors

هر Actor حداقل Stateهای زیر را دارد:
- Role
- Goal
- Incentive
- Knowledge
- Concern
- Authority
- Trust toward Candidate
- Patience
- Commitment
- Communication Style

برای Missionهای Leadership:
- Motivation
- Capability
- Load
- Friction

Candidate Behaviour باید Actor State را تغییر دهد.

---

## 11. Constraints

نمونه:
- Time
- Budget
- Team Capacity
- Regulation
- Technical Limitation
- Customer Contract
- Reputation
- Quality Standard
- Decision Authority

اصل:
> **اگر Candidate بتواند همه گزینه‌های خوب را هم‌زمان انتخاب کند، Mission احتمالاً Trade-off کافی ندارد.**

---

## 12. Resources

Resourceهای Mission می‌توانند شامل:
- People
- Budget
- Time
- Data
- Tools
- Executive Attention
- Customer Access
- Engineering Capacity
- Vendor Capacity

برخی Resourceها باید Cost داشته باشند تا Requesting Information نیز Decision واقعی باشد.

---

## 13. Decision Points

Decision Point می‌تواند Explicit یا Emergent باشد.

برای هر Decision Point:
- Decision Context
- Available Information
- Available Options
- Deadline
- Reversibility
- Cost of Delay
- Decision Owner
- Expected Consequence Space

ثبت می‌شود.

Decision Log باید تا حد ممکن پیش از Consequence شامل:
**Decision → Reasoning → Confidence → Expected Outcome**
باشد.

---

## 14. Action Space

Candidate باید بتواند:
- سؤال بپرسد
- Data درخواست کند
- Meeting بخواهد
- Scope تغییر دهد
- Escalate کند
- Delegate کند
- Experiment طراحی کند
- تصمیم بگیرد
- تعویق آگاهانه ایجاد کند
- یا هیچ Actionی انجام ندهد

اصل:
> **No Action هم Action است و می‌تواند Consequence داشته باشد.**

---

## 15. Event Engine

سه Event Type اصلی:

### Scheduled Event
بر اساس زمان یا Calendar.

### State-triggered Event
بر اساس تغییر World State.

### Behaviour-triggered Event
در پاسخ به رفتار Candidate.

Behaviour-triggered Event برای Assessment حیاتی است چون Consequence را مستقیماً به رفتار واقعی متصل می‌کند.

---

## 16. Success Events

Simulator فقط Crisis Generator نیست.

Success نیز باید Event ایجاد کند، مانند:
- Scaling Pressure
- Executive Overconfidence
- More Budget
- New Market Temptation

Success می‌تواند Evidence بسیار مهم برای Judgment ایجاد کند.

---

## 17. Evidence Opportunity

هر Evidence Opportunity شامل:
- Trigger Situation
- Behaviour of Interest
- Capability / Competency / Gate Links
- Contamination Rule
- Observation Sources
- Positive Signals
- Negative Signals

اصل:
> **Evidence Opportunity شرایط را می‌سازد؛ Behaviour را به Candidate تحمیل نمی‌کند.**

---

## 18. Evidence Coverage Map

هر Mission Template باید نشان دهد:
- برای کدام Behaviourها Opportunity واقعی دارد؛
- کدام Capabilityها Primary/Secondary هستند؛
- چه Gateهایی قابل مشاهده‌اند؛
- چه Evidence Sourceهایی قابل Capture هستند.

Mission بدون Opportunity واقعی برای Behaviour هدف، برای Assessment آن Behaviour معتبر نیست.

---

## 19. Consequence Engine

Consequence نباید Hidden Score ساده باشد.

Consequence باید World State را تغییر دهد.

مثال:
Scope reduction:
- Delivery probability ↑
- Feature coverage ↓
- Customer satisfaction ممکن است ↓
- Team load ↓

اصل:
> **Outcome باید emergent باشد، نه Score animation.**

---

## 20. Consequence Timing

Consequence می‌تواند:
- Immediate
- Delayed
- Latent

باشد.

Latent consequence برای Strategy، System Thinking و Technical/Organizational Debt مهم است.

---

## 21. Difficulty Model

سطوح پایه:
- D1 — Clear Mission
- D2 — Ambiguous Problem
- D3 — Competing Stakeholders
- D4 — Crisis & Scarcity
- D5 — Strategic Complexity

اما هر Mission باید **Difficulty Profile** نیز داشته باشد:
- Information Ambiguity
- Actor Conflict
- Time Pressure
- Resource Scarcity
- Scope
- Consequence Delay
- Reversibility
- Dependency Count
- Ethical Tension
- Uncertainty
- Organizational Politics

---

## 22. Scope

Scopeهای رسمی:
**Task → Project → Team → Product → Business → Organization**

Mission target_scope و Evidence scope باید جداگانه ثبت شوند.

Evidence Mission با Scope بالا الزاماً برای هر Behaviour همان Scope را اثبات نمی‌کند.

---

## 23. Candidate Eligibility

Mission Template می‌تواند Eligibility Rule داشته باشد، مانند:
- Gate State
- Minimum Capability State
- Minimum Scope
- Replay spacing
- Previous Mission family

Eligibility برای Assessment Validity است، نه محدودکردن Learning.

Practice version می‌تواند زودتر در دسترس باشد.

---

## 24. Mode

هر Mission Instance یکی از Modeهای زیر را دارد:
- LEARN
- PRACTICE
- ASSESSMENT
- REAL_PROJECT

Mode باید در Evidence ثبت شود.

Policy:
- Learn: کمک کامل‌تر
- Practice: Hint محدود
- Assessment: بدون Behaviour Prompt
- Real Project: مطابق Policy سازمان

Evidence این Modeها Weight یکسان ندارد.

---

## 25. Completion State

Mission Instance می‌تواند:
- COMPLETED
- ABORTED
- FAILED_WORLD_STATE
- TIME_EXPIRED
- WITHDRAWN

باشد.

اصل:
> **Mission Failure الزاماً Candidate Failure نیست.**

---

## 26. World Outcome vs Behaviour Evidence vs Assessment Claim

سه خروجی باید مستقل باشند:

### World Outcome
در World چه اتفاقی افتاد؟

### Behaviour Evidence
Candidate چگونه رفتار کرد؟

### Assessment Claim
این Behaviour درباره Capability / Competency / Gate چه می‌گوید؟

---

## 27. Replay Architecture

هر Template باید مشخص کند:
- Underlying Behaviour Pattern
- Surface Variables

Replay باید Surface Context را تغییر دهد اما Pattern رفتاری را حفظ کند.

---

## 28. Replay Timing

دو نوع Replay:
- Immediate Practice Replay
- Delayed Evidence Replay

برای اثبات Behaviour Change، Delayed Replay معمولاً Evidence قوی‌تری دارد.

---

## 29. Adaptive Difficulty

### Practice
Adaptation داخل Mission می‌تواند گسترده‌تر باشد.

### Assessment
Difficulty Envelope باید از قبل تعریف و هر Adaptation ثبت شود.

### Real Project
Reality تعیین‌کننده است.

هر Adaptive Change باید Audit شود.

---

## 30. Mission Validation

پیش از استفاده Assessment باید بررسی شود:
- Content Validity
- Difficulty Validity
- Contamination Risk
- Fairness
- Multi-path Validity
- Evidence Observability

Lifecycle رسمی:
**DRAFT → PILOT → VALIDATED → ACTIVE → RETIRED**

---

## 31. Mission Fairness

اصل:
> **Mission باید Behaviour هدف را سخت کند، نه Background Knowledge نامرتبط را.**

اگر Knowledge تخصصی ضروری است باید یا:
- از قبل آموزش داده شده باشد؛
- یا در World به‌صورت قابل دسترس وجود داشته باشد؛
- یا جزء هدف سنجش باشد.

---

## 32. Safety & Ethics

Mission می‌تواند Conflict، Failure، Pressure یا Ethical Dilemma داشته باشد، اما نباید شامل:
- تحقیر
- توهین
- Trauma simulation
- Deception غیرضروری
- فشار روانی ناسالم

باشد.

اصل:
> Realism با Toxicity فرق دارد.

Mission Safety Policy بخشی از Template است.

---

## 33. Mission Bundles

Bundleهای پیشنهادی:
- Foundation Bundle
- Discovery Bundle
- Product Judgment Bundle
- Delivery Bundle
- Leadership Bundle
- System Building Bundle
- Integrated Capstone

Candidate الزاماً همه Missionهای Bundle را اجرا نمی‌کند.

---

## 34. Mission Selection Engine

ورودی:
- Current Flag Profile
- Gate State
- Evidence Gaps
- Recent Missions
- Replay Needs
- Scope Target
- Difficulty Target

خروجی:
**Next Best Mission**

Mission Selection باید Evidence Value را نیز در نظر بگیرد؛ یک Mission می‌تواند چند Evidence Gap مهم را هم‌زمان پوشش دهد.

---

## 35. Mission Recommendation Explainability

برای Reviewer باید روشن باشد:
- کدام Evidence Gap هدف است؛
- چرا Scope مناسب است؛
- چرا Replay لازم است؛
- چرا Difficulty مناسب است.

اما Candidate در Assessment لازم نیست Hidden Behaviour Targetها را بداند.

اصل:
> **Reviewer explainability ≠ Candidate disclosure**

---

## 36. Mission Result Package

پس از هر Mission:
- Mission Context
- Decision Log
- Action Timeline
- Information Requests
- Actor Interactions
- Artifacts
- World Outcome
- Raw Observations
- Candidate Evidence
- AI / Assessor Provenance
- Reflection
- Replay Need
- Profile Update Proposal

تولید می‌شود.

برای Assessmentهای مهم، Human Review / Calibration لازم است.

---

## 37. Mission Profile Separation

اصل:
> **Mission فقط Evidence تولید می‌کند؛ خودش Capability Level یا Gate Status را تغییر نمی‌دهد.**

Profile update مسیر زیر را طی می‌کند:

**Mission → Evidence → Review → Pattern → Profile Update**

این Separation مانع تبدیل Simulator به ماشین امتیازدهی مخفی می‌شود.

---

## 38. Mission Audit Trail

هر Mission Instance باید ثبت کند:
- Template / Version
- Initial World State
- AI Policy
- Events
- Hints / Prompts
- Candidate Actions
- State Changes
- Evidence Produced
- Reviewer / Calibration

Mission باید از نظر Audit قابل Replay و بازسازی باشد.

---

## تعریف نهایی

> **Mission یک ماشین کوچک تولید تجربه و Evidence است: Situation می‌سازد، اختیار و محدودیت می‌دهد، رفتار را مشاهده می‌کند، Consequence واقعی ایجاد می‌کند و بدون اینکه خودش قاضی نهایی باشد، Evidence لازم برای قضاوت معتبر را تولید می‌کند.**
