# 27 — Prerequisite Map, Gate Matrix & Evidence Graph

**وضعیت:** FINAL  
**تاریخ تثبیت:** 2026-10-04

## هدف

این سند Curriculum Operating Model را به Specification قابل پیاده‌سازی در Parcham OS نزدیک می‌کند و سه جزء را تثبیت می‌کند:

1. Prerequisite Map
2. Gate Matrix
3. Evidence Graph

---

# 1. Prerequisite Map

سه نوع رابطه میان Capabilityها وجود دارد:

## Hard Prerequisite
بدون Evidence پایه در Capability قبلی، Mission اثباتی پیشرفته Capability بعدی باز نمی‌شود.

## Co-requisite
دو Capability باید در یک بازه رشد کنند و می‌توانند هم‌زمان تمرین شوند.

## Cross-cutting
در تمام Journey فعال است و Prerequisite خطی ندارد.

| Capability | Hard Prerequisite | Co-requisite / ارتباط نزدیک |
|---|---|---|
| Ownership & Accountability | — | تمام Capabilityها |
| Problem Framing | — | Decision Making، Customer Understanding |
| Decision Making | Problem Framing | Data Thinking، Reflection |
| Data Thinking | — | Decision Making، Metrics |
| Customer Understanding | Problem Framing | Data Thinking |
| Product Discovery | Problem Framing + Customer Understanding | Data Thinking + Metrics & Experimentation |
| Product Strategy | Product Discovery + Decision Making | Product Economics |
| Prioritization | Product Strategy | Decision Making + Product Economics |
| Metrics & Experimentation | Data Thinking | Product Discovery |
| Product Economics | Data Thinking | Product Strategy + Prioritization |
| Delivery | Ownership + Prioritization | Stakeholder Alignment |
| Stakeholder Alignment | Ownership | Decision Making + Delivery |
| Product Leadership | Delivery + Stakeholder Alignment | Reflection & Learning |
| System Building | Delivery + Product Leadership | Data Thinking + Reflection |
| Reflection & Learning | — | Cross-cutting در همه مسیر |

اصل:
> **Hard Prerequisite فقط برای Missionهای اثباتی پیشرفته اعمال می‌شود، نه برای Learning Content.**

Candidate می‌تواند محتوای Capability پیشرفته را زودتر یاد بگیرد، اما تا Evidence پایه Prerequisite را نشان نداده، Evidence سطح بالاتر نباید به‌طور کامل Proven تلقی شود.

---

# 2. Gate Matrix

## Gate A — Foundation Readiness

**سؤال تصمیم:** آیا فرد آماده ورود جدی به Product Core است؟

حداقل Evidence:
- Trustworthiness = PASS
- Ownership = PASS
- Accountability = PASS
- Problem Framing حداقل Demonstrated
- Decision Making حداقل Demonstrated
- Data Thinking حداقل Demonstrated
- Reflection فعال

خروجی:
- ENTER PRODUCT CORE
- NOT YET

## Gate B — Product Judgment Readiness

**سؤال تصمیم:** آیا فرد می‌تواند در مسئله محصولی پیچیده Judgment نشان دهد؟

حداقل Evidence:
- Customer Understanding حداقل Demonstrated
- Product Discovery حداقل Demonstrated
- Metrics & Experimentation حداقل Demonstrated
- Decision Making در چند Context
- Replay معتبر

خروجی:
- ENTER INTEGRATED SIMULATION
- NOT YET

## Gate C — Real Project Readiness

**سؤال تصمیم:** آیا امن است بخشی از واقعیت کسب‌وکار را به او بسپاریم؟

حداقل Evidence:
- Gates رفتاری PASS
- Integrated Simulation
- Delivery حداقل Demonstrated
- Stakeholder Alignment حداقل Demonstrated
- Product Judgment قابل اتکا
- Behaviour Change اثبات‌شده

خروجی:
- ENTER APPRENTICESHIP
- NOT YET

## Gate D — Ownership Trial Readiness

**سؤال تصمیم:** آیا می‌توان Outcome واقعی را به او سپرد؟

حداقل Evidence:
- Evidence واقعی از Delivery
- Evidence واقعی از Stakeholder Alignment
- Accountability معتبر
- Strategy / Prioritization متناسب با Scope
- Real Project Evidence کافی

خروجی:
- GRANT OUTCOME OWNERSHIP
- REMEDIATE

## Gate E — Flag Board

**سؤال تصمیم:** دقیقاً چه مسئولیتی را می‌توان با اطمینان به این فرد سپرد؟

حداقل Evidence:
- Flag Profile کامل
- Real Project Evidence
- Replay
- Gate History
- Evidence Conflict Review
- Outcome History

خروجی:
- READY
- NOT YET
- DIFFERENT SCOPE

اصل:
> **Gate نتیجه Average Score نیست؛ Gate یک Decision مبتنی بر Evidence است.**

Capability قوی نمی‌تواند Gate Failure را با میانگین جبران کند.

---

# 3. Gate Failure vs Insufficient Evidence

این دو باید جدا باشند.

## INSUFFICIENT EVIDENCE
هنوز Evidence کافی برای تصمیم نداریم.

## GATE FAILURE
Evidence معتبر از رفتار ناسازگار با Gate داریم.

این دو مسیر Remediation یکسان ندارند.

---

# 4. Gate State

Stateهای Gate:

**UNPROVEN → PASS → AT_RISK → FAIL → REMEDIATION → REASSESSMENT → PASS / FAIL**

Gate باید Living باشد.

PASS دائمی و غیرقابل‌تغییر نیست.

در عین حال یک Incident عادی نباید خودکار Gate را FAIL کند؛ Severity، Pattern، Context و Human Review باید لحاظ شوند.

---

# 5. Capability / Competency / Gate

این سه مفهوم مستقل‌اند:

## Capability
توانایی تخصصی Curriculum، مثل Product Discovery.

## Competency
یکی از 8 Competency سازمانی، مثل Judgment & Decision-making.

## Gate
شرط اعتماد، مثل Trustworthiness یا Accountability.

یک Behaviour می‌تواند هم‌زمان به چند Capability، Competency و Gate متصل شود.

Evidence نباید برای هر Mapping Copy شود؛ Multi-mapping باید Native باشد.

---

# 6. Evidence Lifecycle

Lifecycle پیشنهادی:

**Raw Event → Observation → Candidate Evidence → Reviewed Evidence → Pattern → Profile Claim**

### Raw Event
Log، Decision، Message، System Event، Assessor Note یا Artifact.

### Observation
ثبت آنچه واقعاً اتفاق افتاده، بدون Judgment زودهنگام.

### Candidate Evidence
Interpretation اولیه از ارتباط Observation با Capability / Competency / Gate.

### Reviewed Evidence
Evidence پس از Review یا Calibration.

### Pattern
چند Evidence مرتبط که رفتار تکرارشونده را نشان می‌دهند.

### Profile Claim
Claim معتبر در Flag Profile.

اصل:
> **Observation را با Judgment یکی نکنیم.**

---

# 7. Evidence Record — Core Fields

هر Evidence Record حداقل باید شامل این Fieldها باشد:

- Person
- Mission
- Situation
- Observation
- Behaviour
- Source
- Source Independence Group
- Capability Links
- Competency Links
- Gate Links
- Signal: Positive / Negative / Critical
- Scope
- Confidence
- Outcome Link
- Prompt Contamination
- AI Contribution
- Timestamp
- Review Status
- Reviewer
- Replay Link

---

# 8. Evidence Immutability

اصل:
> **Evidence خام حذف یا بازنویسی نمی‌شود؛ Interpretation می‌تواند Version شود.**

اگر Interpretation جدید جای قبلی را گرفت:
- Interpretation قبلی = superseded
- Interpretation جدید = active

Observation اصلی باید برای Audit حفظ شود.

---

# 9. Contradictory Evidence

Contradictory Evidence حذف یا Average نمی‌شود.

مثلاً:
- Positive Evidence: 3
- Contradictory Evidence: 1 critical

Contradiction خودش Data است و باید بررسی شود:
- Context متفاوت؟
- Regression؟
- Evidence issue؟
- Gate risk؟

---

# 10. Evidence Independence

چند Observation از یک Source یا Event الزاماً Evidence مستقل نیستند.

Field:
**Source Independence Group**

باید مشخص کند Evidenceها واقعاً از چند منبع مستقل آمده‌اند.

هدف:
> جلوگیری از Inflation مصنوعی تعداد Evidence.

---

# 11. Prompt Contamination

اگر قبل از رفتار مورد سنجش، AI یا Assessor آن رفتار را Prompt کند، Strength آن Evidence کاهش می‌یابد.

Field:
**prompt_contamination = true / false**

مثال:
اگر AI بگوید «Risk را Escalate کن» و Candidate همان کار را انجام دهد، Evidence Ownership قوی محسوب نمی‌شود.

---

# 12. AI Provenance

Artifact یا Behaviour می‌تواند یکی از این وضعیت‌ها را داشته باشد:
- Human-only
- AI-assisted
- AI-generated + human-reviewed
- AI-generated

اصل:
> **AI use Evidence را باطل نمی‌کند؛ ماهیت چیزی را که واقعاً سنجیده‌ایم تغییر می‌دهد.**

Judgment انسانی باید از Contribution ابزار جدا قابل مشاهده باشد.

---

# 13. Evidence Strength

Evidence Strength از چند بعد فهمیده می‌شود:

- Source Reliability
- Source Independence
- Behavioural Directness
- Context Difficulty
- Scope
- Repetition
- Prompt Purity
- Recency / Relevance

این Dimensions الزاماً به یک Score عددی واحد تبدیل نمی‌شوند.

---

# 14. Scope Rule

اصل:
> **Evidence در Scope پایین، به‌صورت خودکار Scope بالاتر را اثبات نمی‌کند.**

Task / Project / Team / Product / Business / Organization باید Explicit بماند.

Promotion Scope نیازمند Evidence واقعی در Scope بالاتر است.

---

# 15. Evidence Recency

Evidence قدیمی حذف نمی‌شود.

اما باید میان:
- Historical Evidence
- Current Capability Evidence

تفاوت وجود داشته باشد.

Evidence expire نمی‌شود، ولی ممکن است برای Claim فعلی کافی نباشد.

این موضوع به‌ویژه برای Leadership، System Building، Stakeholder Alignment و Gateها مهم است.

---

# 16. Profile Update Engine

Flag Profile نباید مستقیماً از Raw Event ساخته شود.

زنجیره:

**Events → Evidence → Reviewed Patterns → Capability Claims → Gate Status → Responsibility Recommendation**

آخرین خروجی باید پاسخ دهد:

> **براساس Evidence، این فرد در حال حاضر چه Scopeای را می‌تواند با Risk قابل قبول حمل کند؟**

Responsibility Recommendation نباید از Title فعلی فرد مشتق شود؛ باید Evidence-driven باشد.
