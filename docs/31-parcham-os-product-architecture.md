# 31 — Parcham OS Product Architecture

**وضعیت:** FINAL  
**تاریخ تثبیت:** 2026-10-04

## تعریف

> **Parcham OS یک Leadership Development Operating System است که تجربه می‌سازد، رفتار را مشاهده می‌کند، Evidence را با حاکمیت انسانی تفسیر می‌کند، قابلیت و Scope اثبات‌شده را در Flag Profile نگه می‌دارد و آن را به تصمیم قابل دفاع درباره مسئولیت بعدی متصل می‌کند.**

سه قانون معماری:

> **هر Truth یک Owner دارد.**

> **AI هیچ Domain State مهمی را مستقیماً مالک یا Mutation نمی‌کند.**

> **هر تصمیم درباره اعتماد و مسئولیت باید از Evidence تا Human Decision قابل ردیابی باشد.**

## 1. معماری کلان

چهار لایه:
- Experience Layer
- Core Domain Layer
- Intelligence Layer
- Platform & Data Layer

AI یک لایه افقی است و Source of Truth هیچ Domain نیست.

## 2. Product Surfaces

### Public Website
Brand، Philosophy، Tracks، Application، Admissions information و Partner/Employer information.

### Candidate Workspace
Journey، Current Wave، Missions، Learning، Feedback، Evidence visibility، Reflection، Flag Profile، Next Best Experience، Real Project و Gate status.

> Candidate Home باید بگوید «الان چه چیزی باید اثبات شود؟» نه «چند درصد دوره را تمام کرده‌ای؟»

### Mission Workspace
Brief، World، Actors، Messages، Data Requests، Resources، Decisions، Artifacts و Timeline.

### Mentor / Coach Workspace
Candidate Development، Feedback، Reflection، Learning Plan و Behaviour Commitments. Coach حق بازنویسی Evidence History را ندارد.

### Assessor Console
Observation Review، Evidence Interpretation، Independent Review، Conflict، Calibration و Replay Recommendation.

### Flag Board Console
Evidence Freeze، Profile Snapshot، Conflicts، Gate History، Responsibility Recommendation، Independent Review، Board Decision و Override Record.

### Academy Admin / Studio
Capability، Curriculum، Mission Template، Actor، World Model، Business Pack، Evidence Mapping، Gate Policies، Responsibility Definitions، Content و AI Policies.

### Organization / Leadership Console
Talent Pipeline، Responsibility Readiness، Scope Readiness، Succession، Capability Gaps و Appointment Candidates. Leaderboard مخفی افراد نباید مدل اصلی باشد.

## 3. Bounded Contexts

### 01 — Identity & Organization
مالک Person، User Account، Organization، Organization Unit، Role، Permission، Candidate Identity، Assessor Identity، Board Membership و Organization Context.

> Organization-aware از ابتدا؛ multi-tenant complexity فقط در صورت نیاز واقعی.

### 02 — Admissions
مالک Funnel: Application → Baseline Challenge → Simulation Assessment → Assessment Camp → Selection Board.

Output: ADMIT / RESERVE / REJECT به‌علاوه Candidate Baseline Profile. Admissions مالک Flag Profile نهایی نیست.

### 03 — Capability & Curriculum
مالک Capability، Capability Version، Level Definition، Scope، Prerequisite، Wave، Curriculum، Curriculum Version، Gate Requirement، Capability State Definition، Learning Unit و Mission Bundle.

تفکیک: Curriculum می‌گوید چه چیزی لازم است؛ Profile می‌گوید چه چیزی برای فرد اثبات شده.

### 04 — Learning Experience
مالک Lesson، Explanation، Example، Exercise، Knowledge Check، Learning Resource و Tutor Session.

> **Learning Content ≠ Assessment Definition**

### 05 — Mission Design
مالک MissionTemplate، MissionTemplateVersion، ActorDefinition، EventDefinition، ConsequenceRule، EvidenceOpportunity، DifficultyEnvelope، ReplayDefinition، EligibilityRule، SafetyPolicy و AI Policy.

Lifecycle: DRAFT → PILOT → VALIDATED → ACTIVE → RETIRED.

### 06 — Mission Runtime
مالک MissionInstance، WorldState، CandidateAction، Event، ActorInstance، Information State، Resource State، DecisionRecord، ScheduledEffect، Observation و Runtime Audit.

> **فقط Mission Runtime حق تغییر Canonical Simulation State را دارد.**

### 07 — World & Simulation Models
مالک Economic Model، Customer Behavior، Market Rules، Product Mechanics، Technical Constraints و Organizational Behavior Primitives. Business Simulation Packها مانند Fintech، E-commerce و SaaS روی آن قرار می‌گیرند.

### 08 — Evidence Engine
مالک Observation Ingestion، Evidence Interpretation، Review، Conflict، Calibration، Pattern، Capability Claim Proposal، Gate Assessment Cases و Replay Need.

Evidence Engine Mission Runtime State را تغییر نمی‌دهد و Flag Profile را بدون Profile Update Contract مستقیم تغییر نمی‌دهد.

### 09 — Flag Profile
مالک Current Capability Claims، Competency Profile، Proven Scopes، Gate States، Learning Memory، Profile Snapshots و Unproven Areas.

> **Living model of demonstrated capability and organizational trust.**

Flag Profile نه CV است، نه Badge Collection و نه AI Personality Report.

### 10 — Responsibility & Trust
مالک ResponsibilityDefinition، ResponsibilityRequirement، ResponsibilityRecommendation، Scope Requirement، Conditional Readiness، Risk و Appointment Eligibility.

Output: READY / READY WITH CONDITIONS / DIFFERENT SCOPE / NOT YET / BLOCKED BY GATE.

### 11 — Human Review & Governance
مالک ReviewCase، ReviewerAssignment، IndependentReview، CalibrationCase، DecisionRecord و OverrideRecord.

> AI می‌تواند پرونده را آماده کند؛ انسان پرونده را می‌بندد.

### 12 — Real Projects
مالک Apprenticeship، Real Project، Ownership Trial، Learning & Evidence Contract، Project Scope، Decision Rights، Outcome، Constraints، Evidence Opportunities و Project Review.

External events ابتدا Source Event / Observation می‌شوند و مستقیماً Profile را تغییر نمی‌دهند.

### 13 — Learning & Reflection
مالک Reflection، Learning Record، Behaviour Commitment، Replay Plan، Learning Claim، Learning Status و Personal Operating Manual.

چرخه: Evidence → Reflection → Behaviour Commitment → Replay → Evidence.

### 14 — Curriculum Orchestrator
Input: Profile، Evidence Gaps، Gate States، Replay Requirements، Learning Commitments، Mission History، Eligibility و Scope Target.

Output: Next Best Experience.

> **Orchestrator Course Player نیست؛ Evidence Gap Resolver است.**

### 15 — Parcham AI
AI Orchestration & Governance Layer با Roleهای Tutor، Mentor، Simulation Director، Actor Runtime، Observer Copilot، Evidence Analyst، Reflection Coach، Curriculum Orchestrator Copilot، Business Pack Builder و Responsibility Matcher.

هر Role دارای Mode Policy، Data Policy، Tool Permissions، Output Schema و Audit است.

### 16 — Knowledge & Business Context
مالک Knowledge Source، Knowledge Version، Business Context، Policy و Source Permission.

Simulation Truth از World State و Organizational Knowledge از Knowledge Context می‌آید.

### 17 — Audit & Compliance
مالک Governance Audit درباره Evidence access، Interpretation changes، Gate decisions، Override، AI policy، Model version و Data sent to AI.

## 4. Parcham AI Gateway

هیچ Domain نباید Provider LLM را مستقیم صدا بزند. همه AI callها از Parcham AI Gateway عبور می‌کنند.

Gateway مسئول Model Routing، Prompt/Policy Version، Structured Output، Retry، Safety، Data Classification، Cost، Latency، Provider Abstraction، Trace و Evaluation Hook است.

## 5. Core Sources of Truth

- Curriculum Definition → Curriculum
- Mission Definition → Mission Design
- Simulation State → Mission Runtime
- Business Simulation Rules → World Model
- Raw Observation → Source / Mission Runtime
- Evidence Interpretation → Evidence Engine
- Current Proven Profile → Flag Profile
- Gate Decision → Human Review / Governance
- Responsibility Requirements → Responsibility Domain
- Responsibility Recommendation → Responsibility Domain
- Appointment Decision → Organization / Human Decision
- Learning Commitment → Reflection Domain

## 6. Event Backbone

نمونه Eventها:
- candidate.admitted
- mission.assigned
- mission.started
- mission.completed
- observation.created
- evidence.accepted
- pattern.updated
- capability.claim_changed
- gate.at_risk
- gate.review_completed
- profile.snapshot_created
- responsibility.recommended
- flag_board.decided
- appointment.recorded
- behaviour_commitment.created
- replay.required

## 7. Sync vs Async

> **User interaction synchronous where immediate truth is needed; cross-domain propagation asynchronous where eventual consistency is acceptable.**

## 8. Read Models

Read Modelهای اصلی:
- Candidate Home
- Assessor Evidence Case
- Flag Board Case

Domain Data نباید صرفاً در UI به شکل ad-hoc Join شود.

## 9. Write Contracts

Commandها باید Intent-based باشند، مانند SubmitReflection، RequestInformation، RecordDecision، AcceptEvidence، OpenGateReview، ApplyProfileUpdate و SubmitBoardDecision.

> API باید Business Language داشته باشد.

## 10. Data Architecture

چهار نوع Storage منطقی:
- Transactional Store
- Event / Audit Store
- Object Store
- Search / Retrieval Index

Retrieval Index Source of Truth اصلی نیست.

## 11. Eventual Consistency UX

Stateهای First-class مانند PROCESSING، PENDING REVIEW، PROCESSING EVIDENCE و PROFILE UPDATE PENDING باید در UX دیده شوند.

## 12. Authorization

مدل Authorization: RBAC + Contextual Policy.

Candidate Hidden Assessment Definition را نمی‌بیند؛ Assessor فقط Assignment مجاز؛ Board فقط Frozen Case؛ Mentor Developmental Context متناسب با Permission.

## 13. Separation of Duties

برای تصمیم‌های Consequential باید Separation of Duties وجود داشته باشد؛ Mission Designer نباید الزاماً تنها Reviewer نهایی همان Mission باشد و Policy change نباید خودکار Evidence تاریخی را re-score کند.

## 14. Version Everything That Changes Meaning

هر Definitionی که تغییرش معنای Evidence یا Decision را عوض می‌کند باید Version شود:
- Capability Definition
- Curriculum
- Mission
- World Model
- Evidence Mapping
- Gate Policy
- Responsibility Definition
- AI Policy
- Prompt Policy
- Knowledge Policy

History با Definition امروز بازنویسی نمی‌شود.

## 15. Product Analytics vs Assessment Evidence

> **Product Analytics ≠ Assessment Evidence**

Completion Rate، Drop-off، Time in Mission و Feature Usage خودکار Evidence شایستگی نیستند.

## 16. Observability

سه سطح:
- Technical Observability
- AI Observability
- Assessment Observability

Assessment Observability شامل Review Latency، Disagreement، Invalidated Missions، Evidence Conflicts و Gate Reversals است.

## 17. Public Website vs Parcham OS

- flag.academy → Brand / Public / Application
- app.flag.academy → Authenticated Parcham OS

Domain separation مهم‌تر از تعداد Hostnameهاست.

## 18. Modular Monolith First

> **Bounded Context ≠ Microservice.**

نسخه اول می‌تواند Modular Monolith باشد: یک Deployable، یک Transactional Database و یک Event Backbone؛ اما Module Ownership و Contractها باید از ابتدا روشن باشند.

Extraction به Microservice فقط با نیاز واقعی Scale یا Isolation.

## 19. Architecture Dependency Rule

Dependency Direction:

**Experience → Application/API → Domain**

Integration میان Domainها با Contracts + Events.

ممنوع:
- UI → Direct DB
- AI Agent → Direct Domain DB write
- Analytics Job → Profile Claim mutation

## 20. Parcham OS Kernel

هفت جزء Core:
1. Curriculum
2. Mission
3. Evidence
4. Flag Profile
5. Human Governance
6. Responsibility
7. Parcham AI

Admissions، Website، Real Projects، Knowledge و Analytics حول این Kernel ساخته می‌شوند.

## تعریف نهایی

> **Parcham OS یک Leadership Development Operating System است که تجربه می‌سازد، رفتار را مشاهده می‌کند، Evidence را با حاکمیت انسانی تفسیر می‌کند، قابلیت و Scope اثبات‌شده را در Flag Profile نگه می‌دارد و آن را به تصمیم قابل دفاع درباره مسئولیت بعدی متصل می‌کند.**