# 30 — Evidence Engine Technical Model

**وضعیت:** FINAL  
**تاریخ تثبیت:** 2026-10-04

## تعریف

> **Evidence Engine ماشین امتیازدهی نیست؛ ماشین تبدیل Observationهای قابل ممیزی به Claimهای قابل دفاع است.**

زنجیره اصلی:

**Observation → Interpretation → Review → Accepted Evidence → Pattern → Profile Claim → Gate Review → Responsibility Recommendation**

هیچ مرحله‌ای نباید مرحله بعدی را دور بزند.

---

## 1. مرز Mission Engine و Evidence Engine

Mission Engine مالک Fact و Observation است.

Evidence Engine مالک Interpretation است.

اصل:

> **Mission Engine owns facts. Evidence Engine owns interpretations.**

اگر Interpretation تغییر کند، Observation ثابت می‌ماند.

---

## 2. موجودیت‌های اصلی Evidence Engine

- Observation
- EvidenceInterpretation
- EvidenceLink
- EvidenceSource
- EvidenceReview
- EvidenceConflict
- PatternCandidate
- BehaviourPattern
- CapabilityClaim
- CompetencyClaim
- GateAssessment
- ReplayRequirement
- ProfileSnapshot
- ResponsibilityRecommendation
- CalibrationCase
- AuditEntry

Observation می‌تواند از Mission، Real Project، Assessor، System، Peer، Artifact یا Source معتبر دیگر بیاید.

---

## 3. Observation Ingestion

هر Observation باید Provenance مشخص داشته باشد.

Fieldهای پایه:
- observation_id
- person_id
- source_type
- source_reference
- occurred_at
- context
- raw_observation
- mission / project reference
- source_independence_group
- prompt_history_reference
- ai_provenance
- integrity_status

Observation باید factual باشد، نه Judgment.

نمونه نامناسب:
> «علی Leader خوبی نبود.»

نمونه مناسب:
> «در سه Decision Point، اعضای تیم منتظر تأیید او ماندند؛ Decision Rights تعریف نشده بود و Candidate هر سه تصمیم را شخصاً گرفت.»

---

## 4. Versioned Interpretation

Observation immutable است اما Interpretation می‌تواند Version شود.

ساختار:
- Observation — immutable
- Interpretation v1 — SUPERSEDED
- Interpretation v2 — ACTIVE

اصل:
> **Fact immutable؛ meaning revisable.**

---

## 5. Evidence Interpretation Contract

هر Interpretation می‌تواند شامل:
- behaviour_code
- behaviour_description
- signal: POSITIVE / NEGATIVE / CRITICAL / NEUTRAL
- capability_links
- competency_links
- gate_links
- scope
- confidence
- context_difficulty
- prompt_contamination
- ai_contribution
- mode
- rationale

Confidence درباره اعتبار Interpretation است، نه کیفیت Performance.

مثال معتبر:
- signal = NEGATIVE
- confidence = HIGH

---

## 6. Evidence Review State Machine

State flow:

**DRAFT → SUBMITTED → UNDER_REVIEW → ACCEPTED / REJECTED / NEEDS_CONTEXT**

Transitionهای بعدی ممکن:
- ACCEPTED → SUPERSEDED
- ACCEPTED → CALIBRATION_REQUIRED

Evidence ردشده حذف نمی‌شود؛ فقط از Profile computation خارج می‌شود.

---

## 7. نقش AI در Interpretation

Parcham AI می‌تواند:
- Observationها را خلاصه کند؛
- Candidate Evidence پیشنهاد دهد؛
- Capability mapping پیشنهاد کند؛
- Contradiction پیدا کند؛
- Prompt Contamination را Flag کند؛
- Source Independence را Challenge کند؛
- Evidence gap پیدا کند.

اما AI به‌تنهایی حق ندارد:
- Gate را Fail کند؛
- Level نهایی را تعیین کند؛
- Flag Board decision بدهد؛
- Responsibility را فعال کند.

اصل Governance:

**AI Proposal → Human Review → Accountable Decision**

---

## 8. Review Policy براساس Consequence

### Tier 1 — Developmental
Practice و Feedback. AI-assisted review می‌تواند کافی باشد.

### Tier 2 — Progression
Evidenceای که Capability State یا Gate Readiness را تغییر می‌دهد. Human Review لازم است.

### Tier 3 — Consequential
ADMIT، Gate Failure، Real Project Readiness، Ownership Trial، Flag Board و Appointment. Human Reviewer مشخص و accountable الزامی است.

---

## 9. Granular Evidence Link

یک Observation می‌تواند برای Targetهای مختلف Signal متفاوت داشته باشد.

هر EvidenceLink باید مستقل نگه دارد:
- target_type
- target_id
- signal
- scope
- relevance
- confidence

بنابراین Multi-dimensional interpretation Native است.

---

## 10. Evidence Strength Profile

Evidence Strength باید از چند Dimension فهمیده شود:
- Source Reliability
- Source Independence
- Behavioural Directness
- Context Difficulty
- Scope
- Repetition Context
- Prompt Purity
- Mode
- Recency
- Outcome Proximity

این Dimensionها نباید الزاماً به Score عددی واحد تبدیل شوند.

---

## 11. Evidence Conflict Engine

Contradiction یک First-class Entity است.

EvidenceConflict می‌تواند شامل:
- targets
- positive_set
- negative_set
- severity
- scope_difference
- recency_difference
- context_difference
- review_status

Reviewer باید بررسی کند:
- Context explains it؟
- Regression داریم؟
- Simulation transfer نشده؟
- Evidence invalid است؟
- Gate Review لازم است؟

اصل:
> **Contradiction برای تمیزشدن Profile حذف نمی‌شود؛ خودش Data است.**

---

## 12. Pattern Engine

مسیر طبیعی:

**Evidence → Evidence Set → Pattern Candidate → Reviewed Pattern**

BehaviourPattern حداقل باید داشته باشد:
- behaviour_pattern
- evidence_set
- contexts
- scopes
- time_span
- positive / negative / contradictory observations
- stability
- review_status

---

## 13. Single Critical Evidence

برخی Behaviourهای Critical می‌توانند بدون انتظار برای Pattern آماری، Immediate Gate Review ایجاد کنند.

نمونه‌ها:
- جعل Evidence
- دروغ عمدی
- دستکاری Assessment
- پنهان‌کاری جدی درباره Risk
- نقض جدی Trust

اما:
> **Critical Evidence مستقیماً Gate Failure ایجاد نمی‌کند؛ Gate Review ایجاد می‌کند.**

---

## 14. Pattern Status

Stateهای Pattern:
- EMERGING
- REPEATED
- STABLE
- CONTRADICTED
- REGRESSED
- RECOVERING

این مدل با Learning Memory و Behaviour Change Tracking هم‌راستاست.

---

## 15. Capability Claim

هر CapabilityClaim باید شامل:
- capability_id
- state: Unproven / Emerging / Demonstrated / Proven
- level: L0–L4
- proven_scope
- supporting_patterns
- contradictory_patterns
- evidence_recency
- confidence_in_claim
- reviewed_at
- reviewed_by
- next_evidence_needed

مثال:
> Decision Making — L2 — Project Scope — Demonstrated؛ Evidence در ambiguity و trade-off قوی است، اما authority-pressure evidence هنوز ناکافی است.

---

## 16. Level × Scope

Level و Scope مستقل‌اند.

مثلاً:
- Judgment Level = L3
- Proven Scope = Project

سیستم نباید از Level بالا، Scope بالاتر را خودکار نتیجه بگیرد.

---

## 17. Promotion Rule

Promotion وقتی مجاز است که Evidence Set نشان دهد:
- Behaviour requirement سطح بعدی دیده شده؛
- Contextهای کافی وجود دارند؛
- Scope لازم واقعاً تجربه شده؛
- Contradiction unresolved مهم وجود ندارد؛
- Replay موردنیاز وجود دارد؛
- Gateها سالم‌اند.

Threshold عددی دقیق فعلاً تعریف نمی‌شود؛ Semantics Promotion قفل می‌شود.

---

## 18. Downgrade Rule

یک Failure معمولی نباید Level را فوری پایین بیاورد.

به‌جای آن ممکن است:
- Proven → AT_RISK
- Pattern → REGRESSED

Downgrade رسمی باید Human-reviewed و Evidence-based باشد.

---

## 19. Gate Assessment State Machine

Stateهای Gate:

**UNPROVEN → PASS → AT_RISK → REVIEW_REQUIRED → PASS_CONFIRMED / FAIL**

در صورت FAIL:

**FAIL → REMEDIATION → REASSESSMENT → PASS / FAIL**

اصل:
> AI یا یک Event منفرد هیچ‌وقت مستقیم Gate Failure ایجاد نمی‌کند.

---

## 20. Gate Assessment Record

Fieldهای پایه:
- gate_id
- current_state
- triggering_evidence
- supporting_evidence
- contradictory_evidence
- severity
- reviewer
- decision
- decision_rationale
- remediation_required
- reassessment_conditions
- effective_at

Gate History باید کامل حفظ شود.

---

## 21. Candidate Visibility

Candidate باید ببیند:
- Capability State
- Evidenceهای پذیرفته‌شده مهم
- Unproven areas
- Gate Risk
- Next Evidence Needed
- Behaviour Commitments باز

اما Hidden Trigger یا Behaviour Opportunityهای Assessment لزوماً پیشاپیش افشا نمی‌شوند.

دو مفهوم مستقل:
- Profile Transparency
- Assessment Secrecy

---

## 22. Candidate Response / Dispute

Candidate باید بتواند Evidence مهم را Challenge کند و Context اضافه کند، اما حق بازنویسی Evidence را ندارد.

Candidate Response باید به Review Case متصل شود.

اصل:
> **Assessment auditable باید حق ارائه Context داشته باشد، بدون اینکه Candidate بتواند Evidence را بازنویسی کند.**

---

## 23. Calibration State Machine

State flow:

**OPEN → INDEPENDENT_REVIEWS → DISAGREEMENT_DETECTED → CALIBRATION → RESOLVED**

خروجی‌های ممکن:
- ACCEPT INTERPRETATION A
- ACCEPT INTERPRETATION B
- NEW INTERPRETATION
- INSUFFICIENT CONTEXT
- REQUIRE REPLAY

Independent Review باید قبل از مشاهده نظر Reviewer دیگر انجام شود تا Anchoring کاهش یابد.

---

## 24. Calibration Principle

> **Calibration برای توافق درباره معنای Evidence است؛ نه رسیدن به حس مشترک درباره Candidate.**

بحث باید روی Observation، Behaviour، Context، Standard و Scope بماند.

---

## 25. Reviewer Bias Monitoring

Parcham OS می‌تواند Patternهای Reviewer را برای QA Assessment نگه دارد، مانند:
- Interpretation negativity rate
- Disagreement rate
- Domain-specific bias signals

این Signalها به‌تنهایی Reviewer را بی‌اعتبار نمی‌کنند؛ برای Quality Assurance استفاده می‌شوند.

---

## 26. Profile Snapshot

Flag Profile Living است، اما در نقاط تصمیم مهم Snapshot immutable لازم است.

نمونه نقاط Snapshot:
- Admission
- Real Project Entry
- Ownership Trial
- Flag Board
- Appointment

هر Decision باید به Snapshot و Evidence Set زمان خودش متصل باشد.

---

## 27. Profile Update Proposal

AI یا Engine می‌تواند Profile Update Proposal تولید کند.

برای تغییر Consequential:

**Profile Update Proposal → Human Review → Apply**

برای Developmental stateهای کم‌ریسک Automation بیشتری مجاز است.

---

## 28. Responsibility Definition

ResponsibilityDefinition باید Requirementهای یک Scope مسئولیت را مشخص کند.

مثال مفهومی:
**Product Manager — Product Scope**

می‌تواند نیازمند این‌ها باشد:
- Ownership: L3 / Product
- Judgment: L3 / Product
- Execution: L3 / Product
- Communication: L3 / Product
- Leadership: L2 / Team
- Gates: PASS
- Strategy minimum state
- Delivery: Proven
- Evidence freshness requirements

این‌ها Specification مسئولیت‌اند، نه Threshold عددی نهایی.

---

## 29. Responsibility Recommendation

Stateهای Recommendation:
- READY
- READY WITH CONDITIONS
- DIFFERENT SCOPE
- NOT YET
- BLOCKED BY GATE

Recommendation باید Explainable باشد و نشان دهد:
- Supporting Evidence
- Remaining Gaps
- Accepted Risks

---

## 30. Appointment Boundary

> **Responsibility Recommendation ≠ Appointment Decision**

AI یا Engine می‌تواند Recommendation بدهد، اما Appointment / Promotion / Reduced Scope نیازمند Explicit Human Decision است.

Decision maker باید ثبت شود.

---

## 31. Human Override

Human می‌تواند خلاف Recommendation تصمیم بگیرد، اما باید ثبت شود:
- Recommendation
- Human Decision
- Override = true
- Reason
- Accountable Decision Maker

Outcome این Override بعداً Learning Data می‌شود.

---

## 32. Flag Board State Machine

State flow:

**DRAFT_CASE → EVIDENCE_FREEZE → INDEPENDENT_REVIEW → CONFLICT_RESOLUTION → BOARD_READY → BOARD_DECISION → DECISION_ACKNOWLEDGED**

Board Decision یکی از:
- READY
- NOT_YET
- DIFFERENT_SCOPE

در صورت READY:
- APPOINTMENT_ELIGIBLE

خود Appointment تصمیمی جدا از Flag Board است.

---

## 33. Evidence Freeze

پیش از Flag Board باید Evidence Set تا Timestamp مشخص Freeze شود.

Evidence جدید بعداً Profile را تغییر می‌دهد اما Decision قبلی را بازنویسی نمی‌کند.

---

## 34. Actionable NOT YET

NOT YET باید تولید کند:
- Blocking Evidence Gaps
- Required Behaviours
- Recommended Mission / Experience
- Replay Requirements
- Review Horizon

NOT YET بخشی از Development است، نه Verdict مبهم.

---

## 35. Learning Loop Integration

Evidence Engine باید رابطه زیر را دنبال کند:

**Learning Claim → Replay Opportunity → Behaviour Evidence**

Pattern می‌تواند با Behaviour Change از REGRESSED/NEGATIVE به RECOVERING و سپس STABLE POSITIVE حرکت کند.

---

## 36. Data Lineage

برای هر Claim باید مسیر کامل قابل مشاهده باشد:

**Claim → Pattern → Evidence Links → Evidence Interpretations → Observations → Mission Event / Real Project Source**

اصل:
> **No claim without lineage.**

---

## 37. No Black-box Profile

LLM embedding، latent score یا مدل پیش‌بینی می‌تواند Retrieval/Detection را کمک کند، اما Source of Truth شایستگی نیست.

Profile باید Explainable و متصل به Evidence قابل بازرسی باشد.

اصل:
> **No responsibility assignment from a black-box score.**

---

## 38. Evaluation of the Assessment System

خود Evidence Engine و Assessment System باید با Outcome واقعی ارزیابی شوند.

Feedback Loop:

**Assessment Decision → Real Performance → Outcome → Calibration of Assessment System**

باید بررسی شود:
- READYها بعداً چگونه عمل می‌کنند؟
- NOT YETها پس از Remediation چگونه تغییر می‌کنند؟
- کدام Missionها Predictive نیستند؟
- کدام Assessorها Disagreement غیرعادی دارند؟
- کدام Evidence Patternها با Performance واقعی هم‌خوان نیستند؟

---

## تعریف نهایی

> **Evidence Engine حافظه قضایی پرچم است: واقعیت را از Observation می‌گیرد، Interpretation را قابل بازبینی نگه می‌دارد، Contradiction را پنهان نمی‌کند، Pattern را از تکرار می‌سازد، Profile را از Evidence می‌سازد و هیچ تصمیم مهمی را بدون Lineage و مسئول انسانی نهایی نمی‌کند.**

سه اصل فنی:

> **No claim without lineage.**

> **No gate failure without accountable human review.**

> **No responsibility assignment from a black-box score.**
