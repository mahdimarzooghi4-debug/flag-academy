# 29 — Mission Runtime Data Model & Contracts

**وضعیت:** FINAL  
**تاریخ تثبیت:** 2026-10-04

## اصل معماری

> **LLM می‌تواند جهان را روایت کند؛ اما State معتبر جهان را فقط Mission Engine تغییر می‌دهد.**

> **LLM proposes. Engine validates. Rules mutate. Events record. Observations preserve. Evidence interprets. Humans remain accountable.**

به فارسی:

> **AI پیشنهاد می‌دهد؛ موتور اعتبارسنجی می‌کند؛ قواعد State را تغییر می‌دهند؛ Eventها تاریخچه را حفظ می‌کنند؛ Observation واقعیت را ثبت می‌کند؛ Evidence Engine معنا می‌سازد؛ و تصمیم‌های مهم انسانی باقی می‌مانند.**

## 1. Runtime Flow

**Mission Template Version → Mission Instance → Initial World State → Candidate Action → Runtime Validation → Event → Consequence Rules → World State Transition → Observation → Evidence Pipeline**

AI Actors و Simulation Director فقط از طریق Contractهای مشخص با Engine تعامل دارند و مستقیماً State معتبر را تغییر نمی‌دهند.

## 2. موجودیت‌های اصلی

- MissionTemplate
- MissionTemplateVersion
- MissionInstance
- WorldState
- WorldStateSnapshot
- ActorDefinition
- ActorInstance
- InformationItem
- Resource
- Constraint
- DecisionPoint
- CandidateAction
- DecisionRecord
- EventDefinition
- EventInstance
- ConsequenceRule
- ScheduledEffect
- EvidenceOpportunity
- Observation
- MissionArtifact
- MissionResult
- ReplayRelation
- AuditEntry

Evidence یک Entity در Evidence Engine است؛ Mission Engine مستقیماً Evidence نهایی تولید نمی‌کند و Observation تولید می‌کند.

## 3. MissionTemplate & Version

MissionTemplate هویت پایدار Family را نگه می‌دارد و MissionTemplateVersion Definition immutable هر نسخه است.

Versionهای مهم:
- definition_version
- world_model_version
- evidence_mapping_version
- ai_policy_version
- difficulty_profile
- eligibility_policy
- safety_policy
- replay_policy

> **Mission Instance همیشه به نسخه دقیق اجراشده Pin می‌شود.**

## 4. Mission Instance State Machine

State flow:
**CREATED → ELIGIBILITY_CHECK → READY → RUNNING → TERMINAL**

زیرحالت‌های RUNNING:
- ACTIVE
- WAITING_FOR_WORLD
- WAITING_FOR_CANDIDATE
- PAUSED

Terminal Stateها:
- COMPLETED
- FAILED_WORLD_STATE
- TIME_EXPIRED
- ABORTED
- WITHDRAWN
- INVALIDATED

INVALIDATED زمانی استفاده می‌شود که اجرای Mission از نظر Assessment Integrity معتبر نباشد، حتی اگر Runtime به پایان رسیده باشد.

## 5. Event-sourced State

Source of Truth مفهومی:
**Initial State + Ordered Events = Current State**

WorldStateSnapshot برای Performance نگهداری می‌شود، اما History همچنان Event-based و قابل Audit است.

## 6. Immutable Runtime History

Eventهای اجراشده Edit یا Delete نمی‌شوند.

اصلاح از طریق Eventهای جدید مانند event.corrected یا event.invalidated انجام می‌شود.

> **Runtime history append-only است؛ Current interpretation قابل تغییر است.**

## 7. Candidate Action Contract

Fieldهای پایه:
- action_id
- mission_instance_id
- actor_id
- action_type
- target
- payload
- reasoning
- confidence
- requested_at
- effective_at
- resource_cost
- mode
- provenance
- idempotency_key

Action Typeهای پایه:
- REQUEST_INFORMATION
- COMMUNICATE
- DECIDE
- ESCALATE
- DELEGATE
- CHANGE_SCOPE
- ALLOCATE_RESOURCE
- RUN_EXPERIMENT
- NO_ACTION

Schema باید توسعه‌پذیر بماند.

## 8. Decision Contract

Decisionهای مهم باید DecisionRecord مستقل داشته باشند:
- Question
- Options considered
- Available evidence
- Assumptions
- Decision
- Reasoning
- Confidence
- Expected outcome
- Revisit trigger
- Decision owner
- Reversibility

Decision Record باید تا حد امکان پیش از Consequence Freeze شود تا Hindsight Rewrite رخ ندهد.

## 9. Information Contract

هر InformationItem دو بخش دارد:

### Truth
حقیقت World.

### Access Policy
نحوه دسترسی Candidate.

Fieldهای مهم:
- availability_type
- required_action
- required_permission
- resource_cost
- latency
- quality
- confidence
- noise_level
- expires_at

Information Gathering باید Cost و Trade-off واقعی داشته باشد.

## 10. Canonical Truth Rule

> **AI Actor نمی‌تواند Fact جدیدی را که در World Model وجود ندارد به حقیقت Canonical تبدیل کند.**

اگر Actor پاسخ را نمی‌داند، پاسخ باید یکی از حالت‌های UNKNOWN، NOT_AVAILABLE یا ACTOR_DOES_NOT_KNOW باشد.

## 11. Actor Definition vs Actor Instance

ActorDefinition صفات پایه Actor را نگه می‌دارد و ActorInstance State زنده Actor در یک Mission را.

Stateهای نمونه:
- trust_toward_candidate
- current_frustration
- commitment
- known_information

## 12. Actor Runtime Contract

AI Actor می‌تواند Structured Proposal برگرداند:
- Utterance
- Intent
- Information disclosed
- Requested action
- Emotional / interaction signal

AI Actor اجازه ندارد State را مستقیم Mutation دهد.

## 13. State Mutation Rule

منابع Proposal برای Mutation:
- Candidate Action
- Event
- Validated Consequence Rule

Commit نهایی فقط توسط Engine انجام می‌شود:
**proposal → validate → commit**

نه:
**LLM output → database update**

## 14. Event Contract

هر EventInstance حداقل:
- event_id
- event_type
- source
- trigger_type
- trigger_reference
- occurred_at
- effective_at
- visibility
- payload
- world_version_before
- world_version_after
- causal_parent_ids
- idempotency_key

Trigger Typeها:
- SCHEDULED
- STATE_TRIGGERED
- BEHAVIOUR_TRIGGERED
- EXTERNAL
- MANUAL_OPERATOR

## 15. Causality Chain

Eventهای مهم باید causal_parent_ids داشته باشند تا چرایی رخداد قابل ردیابی باشد.

فقط Causalityهایی که World Model تعریف کرده Canonical محسوب می‌شوند.

## 16. Consequence Rule

هر Rule شامل:
- Trigger
- Preconditions
- Effects
- Timing
- Visibility
- Probability / uncertainty
- Reversibility
- Evidence observability

Rule باید World State را تغییر دهد و نباید Competency Score را مستقیم تغییر دهد.

> **Action → Consequence → Observation → Evidence Review**

نه:
> Action → Competency Score

## 17. ScheduledEffect

برای Delayed و Latent Consequence:
- scheduled_effect_id
- due_at / trigger_condition
- origin_event
- effect_payload
- cancellable
- cancel_condition
- visibility

ScheduledEffect می‌تواند با تغییر معتبر World State قبل از اجرا Cancel شود.

## 18. World State Namespaces

Namespaceهای استاندارد:
- business
- product
- customer
- financial
- team
- technical
- stakeholder
- market
- risk
- mission

Business Pack می‌تواند Fieldهای اختصاصی اضافه کند.

## 19. World State Version

هر Mutation معتبر باید world_state_version را افزایش دهد.

Candidate Action باید روی Version مشخص اعمال شود و Engine Conflict میان Mutationهای هم‌زمان را مدیریت کند.

## 20. Deterministic Core + Probabilistic Edge

> **Core rules deterministic؛ uncertainty explicit.**

عدم‌قطعیت باید از World Model و Probability Versioned بیاید، نه تصمیم آزاد LLM.

## 21. Replayable Randomness

اگر Runtime از Randomness استفاده می‌کند باید simulation_seed ذخیره شود.

هدف: Debug، Audit، Comparison و Reproducibility.

## 22. Evidence Opportunity Contract

Fieldهای Runtime:
- opportunity_id
- trigger_condition
- behaviour_target
- capability_links
- competency_links
- gate_links
- observation_sources
- contamination_policy
- active_from
- active_until

وقتی Trigger برقرار شود opportunity.opened ثبت می‌شود.

## 23. Temporal Opportunity Window

Evidence Opportunity باید Window زمانی داشته باشد؛ Timing رفتار بخشی از Observation است.

## 24. Observation Contract

Mission Engine باید Observation بسازد، نه Judgment.

نمونه معتبر:
> Risk در 10:20 discoverable شد، Candidate در 10:31 آن را مشاهده کرد و اولین Escalation در 16:42 رخ داد.

Interpretation به Evidence Engine تعلق دارد.

## 25. Prompt / Hint Events

هر Hint یا Intervention باید Event باشد:
- assistant.hint_delivered
- assessor.prompt_delivered

و target_behaviour، delivery_time، source و mode را ثبت کند.

## 26. Mission Audit Package

Timeline قابل بازسازی:
**T0 Initial State → T1 Information Request → T2 Actor Interaction → T3 Decision → T4 Event → T5 Consequence → T6 State Change → T7 Observation**

هر مورد باید به Source و Version مربوط متصل باشد.

## 27. Security Boundary

Data Classification:
- PUBLIC
- INTERNAL
- CONFIDENTIAL
- RESTRICTED

AI و Actorها فقط Least-privilege Context دریافت می‌کنند، به‌خصوص در REAL_PROJECT.

## 28. Assessment Integrity Policy

در ASSESSMENT Mode:
- AI نباید Hidden Behaviour Target را افشا کند.
- AI نباید Decision Recommendation بدهد.
- Discoverable Information بدون Action مناسب Candidate افشا نمی‌شود.
- Outcome برای کمک به Candidate نرم‌تر نمی‌شود.
- تخطی از Policy باید Event شود.
- تخطی جدی می‌تواند Mission را INVALIDATED کند.

## 29. Runtime Failure Categories

### WORLD FAILURE
World به Failure State رسیده.

### CANDIDATE OUTCOME
Outcome مرتبط با تصمیم و رفتار Candidate.

### SYSTEM FAILURE
زیرساخت، Actor Runtime یا Processing خطا کرده.

System Failure نباید Candidate Failure تلقی شود و می‌تواند Retry، Pause یا Invalidate ایجاد کند.

## 30. Idempotency

تمام Action و Eventهای مهم باید idempotency_key داشته باشند تا Retry باعث Mutation تکراری نشود.

## 31. Contract Versioning

Contractهای Runtime باید Version-aware باشند:
- Action Schema Version
- Event Schema Version
- Consequence Rule Version
- Actor Policy Version
- World Model Version

این Versionها برای Cohort Comparison و Audit حفظ می‌شوند.

## اصل نهایی

> **LLM proposes. Engine validates. Rules mutate. Events record. Observations preserve. Evidence interprets. Humans remain accountable.**
