# 32 — Domain Model & Entity/Relationship Specification

**وضعیت:** FINAL  
**تاریخ تثبیت:** 2026-10-04

## اصل معماری

> **هر Aggregate فقط از Invariantهای خودش محافظت می‌کند؛ هیچ Transaction نباید برای حفظ یک Business Rule مجبور باشد چند Bounded Context مستقل را هم‌زمان Lock کند.**

مرز Transaction از مرز Domain شروع می‌شود، نه از راحتی Database.

## 1. Identity & Versioning

همه Entityهای اصلی یک ID داخلی پایدار و opaque از نوع UUID دارند.

برای موجودیت‌های Versioned دو شناسه جدا داریم:
- definition_id — هویت مفهومی ثابت
- version_id — نسخه immutable مشخص

هیچ رابطه تاریخی نباید فقط به current version اشاره کند؛ هر Mission، Claim یا Board Decision باید Version دقیق Definitionهای مؤثر زمان خودش را نگه دارد.

## 2. Aggregate Rules

هر Aggregate Root باید چهار چیز را روشن کند:
- State Ownership
- Invariant
- Commands
- Domain Events

اصل:
> **Domain Event یعنی چیزی که اتفاق افتاده؛ Command یعنی چیزی که می‌خواهیم اتفاق بیفتد.**

مثال:
- ApproveEvidence = Command
- EvidenceAccepted = Event

## 3. Identity & Organization Context

### Aggregate: Person
مالک هویت انسانی پایدار.

Entityهای وابسته:
- PersonIdentity
- ContactPoint
- OrganizationMembership

Credential و Login متعلق به Identity Provider است، نه Domain.

### Aggregate: Organization
Entityهای اصلی:
- OrganizationUnit
- RoleDefinition
- Membership
- ContextPolicy

رابطه اصلی:
**Person ↔ OrganizationMembership ↔ Organization**

هر Candidate Journey باید به Organization Context مشخص Pin شود.

اصل:
> Evidence یک Candidate بدون Policy صریح نباید بین Organizationها قابل انتقال باشد.

## 4. Admissions Context

### Aggregate: AdmissionCase

State Machine:
**DRAFT → SUBMITTED → BASELINE → SIMULATION → CAMP → BOARD → DECIDED**

Terminal:
- ADMITTED
- RESERVED
- REJECTED
- WITHDRAWN

Child / Referenceهای اصلی:
- ApplicationSnapshot
- AdmissionStageState
- AdmissionAssessmentRef
- BaselineProfileRef

Commands:
- SubmitApplication
- AdvanceAdmissionStage
- RecordAdmissionAssessment
- OpenSelectionBoard
- DecideAdmission

Events:
- admission.application_submitted
- admission.stage_advanced
- admission.board_opened
- candidate.admitted
- candidate.reserved
- candidate.rejected

تصمیم ADMIT در Admissions transaction ثبت می‌شود و ساخت Candidate Journey در Context دیگر از طریق Event انجام می‌شود.

## 5. Capability & Curriculum Context

### Aggregate: CapabilityDefinition
State:
**DRAFT → ACTIVE → RETIRED**

Versionها immutable هستند.

Child definitions:
- LevelDescriptor
- ScopeExpectation
- BehaviourRequirement
- EvidenceRequirement

### Aggregate: CurriculumDefinition
مالک:
- Wave
- PrerequisiteRule
- GateRequirementRef
- MissionBundleRef
- LearningUnitRef

Curriculum به Version مشخص Capability reference می‌دهد؛ Capability داخل Curriculum embed نمی‌شود.

## 6. Learning Experience Context

### Aggregate: LearningUnit
انواع:
- LESSON
- EXERCISE
- KNOWLEDGE_CHECK
- RESOURCE
- TUTOR_SESSION

### Aggregate: LearningAttempt
State:
**ASSIGNED → STARTED → COMPLETED / ABANDONED**

اصل:
> Learning completion به‌خودی‌خود Profile Claim یا Capability Evidence ایجاد نمی‌کند.

## 7. Mission Design Context

Aggregateهای اصلی:
- MissionTemplate
- MissionTemplateVersion

MissionTemplateVersion شامل:
- Objective
- PrimaryCapabilityRefs
- SecondaryCapabilityRefs
- GateOpportunityRefs
- ActorDefinitions
- InformationDefinitions
- ConstraintDefinitions
- EventDefinitions
- ConsequenceRules
- EvidenceOpportunityDefinitions
- DifficultyEnvelope
- ReplayPolicy
- SafetyPolicy
- AIPolicy

Lifecycle:
**DRAFT → PILOT → VALIDATED → ACTIVE → RETIRED**

اصل:
> Version فعال‌شده ویرایش نمی‌شود؛ تغییر Definition یعنی Version جدید.

## 8. Mission Runtime Context

### Aggregate: MissionInstance

State Machine:
**CREATED → ELIGIBILITY_CHECK → READY → RUNNING → TERMINAL**

MissionInstance مالک:
- mission_template_version_id
- candidate_id
- mode
- target_scope
- simulation_seed
- current_world_version

Aggregateهای مرتبط:
- ActorInstance
- DecisionRecord
- ScheduledEffect
- EvidenceOpportunityInstance

Transaction Candidate Action:
**validate action → append domain event(s) → apply deterministic mutation → increment world version**

اصل:
> **هیچ Event خارجی قبل از Commit موفق Domain Transaction منتشر نمی‌شود.**

Transactional Outbox Pattern بخشی از معماری منطقی است.

## 9. World Model Context

Aggregateها:
- WorldModelDefinition
- WorldModelVersion
- BusinessSimulationPack

World Model Rule Setها:
- business
- customer
- financial
- team
- technical
- market
- stakeholder
- risk

Shared Mission Runtime نباید Business-specific logic را hardcode کند.

## 10. Observation Model

### Aggregate: Observation

Fieldهای محوری:
- observation_id
- subject_person_id
- source_context
- source_ref
- occurred_at
- observed_fact
- scope_context
- provenance
- independence_group
- prompt_history_ref
- integrity_state

State:
**DRAFT → SEALED**

اصل:
> Observation بعد از Seal شدن Edit نمی‌شود؛ Correction Observation جدید ساخته می‌شود.

## 11. Evidence Engine Context

### Aggregate: EvidenceCase

داخل Case:
- EvidenceInterpretation
- EvidenceLink
- ReviewState
- ReviewerAssignment
- CandidateResponseRef

State:
**DRAFT → SUBMITTED → UNDER_REVIEW → ACCEPTED / REJECTED / NEEDS_CONTEXT**

Interpretation پذیرفته‌شده می‌تواند بعداً SUPERSEDED شود اما حذف نمی‌شود.

Aggregateهای دیگر:
- EvidenceConflict
- BehaviourPattern

Pattern State:
**EMERGING → REPEATED → STABLE**

و Branchها:
- CONTRADICTED
- REGRESSED
- RECOVERING

## 12. Human Review Context

### Aggregate: ReviewCase

review_type:
- EVIDENCE
- GATE
- CALIBRATION
- PROFILE_UPDATE
- FLAG_BOARD

Child entities:
- ReviewerAssignment
- IndependentReview
- ReviewDecision
- CandidateResponse
- OverrideRecord

اصل:
> Reviewer مستقل تا قبل از Submit نظر خودش نباید Review دیگر را ببیند.

## 13. Calibration Aggregate

### Aggregate: CalibrationCase

State:
**OPEN → INDEPENDENT_REVIEWS → DISAGREEMENT_DETECTED → CALIBRATION → RESOLVED**

Output:
- ACCEPT INTERPRETATION A
- ACCEPT INTERPRETATION B
- NEW INTERPRETATION
- INSUFFICIENT CONTEXT
- REQUIRE REPLAY

Calibration Candidate Score تولید نمی‌کند.

## 14. Flag Profile Context

### Aggregate: FlagProfile

کلید مفهومی:
**Person × Organization Context × Track**

مالک:
- CapabilityClaimRef
- CompetencyClaimRef
- GateStateRef
- LearningMemoryRef
- UnprovenArea
- CurrentRecommendedScopeRef

### Entity: CapabilityClaim

کلید مفهومی:
**person + capability + track**

Fieldها:
- state
- level
- proven_scope
- supporting_pattern_refs
- contradictory_pattern_refs
- recency
- next_evidence_needed

اصل:
> Current Claim فقط از Accepted Profile Update ساخته می‌شود؛ EvidenceCase مستقیماً Claim را Mutation نمی‌دهد.

## 15. Profile Update Aggregate

### Aggregate: ProfileUpdateCase

Input:
- current_profile_snapshot
- new_patterns
- proposed_changes

State:
**PROPOSED → REVIEW_REQUIRED / AUTO_ELIGIBLE → APPROVED → APPLIED**

Developmental update کم‌ریسک می‌تواند AUTO_ELIGIBLE باشد؛ Promotion consequential نیازمند Human Review است.

Event profile.claim_changed باید old و new state را هر دو داشته باشد.

## 16. Gate Model

### Aggregate: GateAssessment

کلید:
**person × gate_definition × organization_context**

State:
**UNPROVEN → PASS → AT_RISK → REVIEW_REQUIRED → PASS_CONFIRMED / FAIL**

در صورت Fail:
**FAIL → REMEDIATION → REASSESSMENT → PASS / FAIL**

FlagProfile فقط Current Gate Projection را نشان می‌دهد؛ Gate History مستقل و auditable باقی می‌ماند.

## 17. Reflection Context

### Aggregate: LearningRecord

State:
**DRAFT → COMMITTED → REPLAY_PENDING → VERIFIED / NOT_YET_VERIFIED**

Child entities:
- Reflection
- LearningClaim
- BehaviourCommitment
- ReplayRequirement

Behaviour Commitment خودش Profile را تغییر نمی‌دهد؛ Event behaviour_commitment.created Orchestrator را برای Replay تحریک می‌کند.

## 18. Real Projects Context

### Aggregate: RealProjectEngagement

Type:
- APPRENTICESHIP
- OWNERSHIP_TRIAL

مالک:
- candidate
- organization
- scope
- decision_rights
- outcome_definition
- constraints
- evidence_contract
- supervisor
- start/end

State:
**DRAFT → APPROVED → ACTIVE → REVIEW → COMPLETED / TERMINATED**

اصل:
> Real Project بدون Learning & Evidence Contract فعال نمی‌شود.

External integration flow:
**External Event → Source Event → Validation → Observation**

## 19. Responsibility Context

### Aggregate: ResponsibilityDefinition

Versioned و شامل:
- CapabilityRequirement
- CompetencyRequirement
- GateRequirement
- FreshnessRequirement
- ScopeRequirement

### Aggregate: ResponsibilityAssessment

Input:
- profile_snapshot_id
- responsibility_definition_version_id

Output:
- READY
- READY_WITH_CONDITIONS
- DIFFERENT_SCOPE
- NOT_YET
- BLOCKED_BY_GATE

به‌علاوه:
- supporting_reasons
- gaps
- conditions
- risk_notes

این Assessment Recommendation است، نه Appointment.

## 20. Flag Board Aggregate

### Aggregate: FlagBoardCase

State:
**DRAFT_CASE → EVIDENCE_FREEZE → INDEPENDENT_REVIEW → CONFLICT_RESOLUTION → BOARD_READY → BOARD_DECISION → DECISION_ACKNOWLEDGED**

Output:
- READY
- NOT_YET
- DIFFERENT_SCOPE

در صورت READY:
- APPOINTMENT_ELIGIBLE

References:
- profile_snapshot
- frozen_evidence_set
- gate_history_refs
- responsibility_assessment
- board_reviews
- decision_rationale

اصل:
> Board Decision بعد از Evidence Freeze به Evidence جدید وابسته نمی‌شود.

## 21. Appointment Boundary

### Aggregate: AppointmentDecision

Readiness با Appointment یکی نیست.

Fieldها:
- person
- responsibility
- scope
- effective_date
- decision_maker
- source_flag_board_case
- override_reason در صورت نیاز

## 22. Curriculum Orchestrator

### Domain/Application Service: NextExperiencePlanner

Input:
- FlagProfile
- GateState
- EvidenceGaps
- ReplayRequirements
- LearningCommitments
- MissionHistory
- Eligibility

Output:
- ExperienceRecommendation

Recommendation می‌تواند Persist شود برای Audit، اما Planner Source of Truth Profile نیست.

## 23. AI Context

### Aggregate: AIInvocation

برای Audit/Governance، شامل:
- role
- mode
- provider/model
- policy_version
- prompt_policy_version
- input_data_classification
- tool_permissions
- output_schema_version
- latency
- cost
- result_status

Retention محتوای حساس Prompt جداگانه Policy می‌شود.

## 24. Knowledge Context

Aggregateها:
- KnowledgeSource
- KnowledgeSnapshot

State:
**DRAFT → VALIDATED → ACTIVE → RETIRED**

هر Retrieval باید به Source Version قابل ردیابی باشد.

Knowledge Source هیچ‌وقت Simulation Truth را override نمی‌کند.

## 25. Transaction Boundaries

Business Operation → Aggregate Transaction Boundary:
- Candidate Action → Mission Runtime
- Mission State Change → Mission Runtime
- Observation Seal → Observation
- Evidence Acceptance → EvidenceCase
- Calibration Resolution → CalibrationCase
- Capability Claim Change → ProfileUpdateCase + FlagProfile
- Gate Decision → GateAssessment
- Reflection Commit → LearningRecord
- Real Project Start → RealProjectEngagement
- Responsibility Recommendation → ResponsibilityAssessment
- Flag Board Decision → FlagBoardCase
- Appointment → AppointmentDecision

Cross-context consistency:
**Domain Event + Outbox + Idempotent Consumer**

## 26. Event Envelope

تمام Domain Eventها Envelope مشترک دارند:
- event_id
- event_type
- event_version
- aggregate_type
- aggregate_id
- aggregate_version
- occurred_at
- actor
- correlation_id
- causation_id
- organization_context_id
- data_classification
- payload
- trace_id

## 27. Optimistic Concurrency

Aggregateها version دارند.

هر Command با expected_aggregate_version اجرا می‌شود.

در Conflict:
**409 VERSION_CONFLICT**

Last-write-wins ممنوع است.

## 28. Governance History

برای Observation، Evidence، Gate Decision، Board Decision و Audit حذف عادی نداریم.

Stateهای جایگزین:
- VOIDED
- SUPERSEDED
- INVALIDATED

Delete واقعی فقط طبق Data Retention / Privacy Policy و فرآیند ویژه Governance.

## 29. Read Model Projection

Projectionهای اصلی:
- CandidateHomeView
- MissionWorkspaceView
- EvidenceReviewView
- FlagProfileView
- FlagBoardCaseView
- LeadershipReadinessView

Domain Aggregateها برای UI shape طراحی نمی‌شوند.

## 30. Aggregate Size Rule

> **چیزی فقط وقتی داخل Aggregate است که برای حفظ Invariant همان Transaction واقعاً لازم باشد.**

Monster Aggregate ممنوع است.

## 31. Relationship Philosophy

سه نوع رابطه Domain:
- Ownership
- Reference
- Snapshot

برای Governance Decisionها Snapshot بر Live Reference ترجیح دارد.

## 32. Cross-context Invariant

Cross-context invariant ممنوع است.

مثلاً Mission COMPLETED نباید در همان Transaction Profile را Update کند.

درست:
Mission completion → Event → Evidence processing → در صورت کافی بودن Profile Update.

## 33. Command Ownership

هر Command دقیقاً یک Owner دارد.

نمونه:
- StartMission → Mission Runtime
- SubmitReflection → Reflection
- AcceptEvidence → Evidence Engine
- ResolveCalibration → Governance
- ApplyProfileUpdate → Flag Profile
- DecideGate → Gate Assessment
- RecommendResponsibility → Responsibility
- DecideFlagBoard → Flag Board

اگر یک Command نیازمند چند Context است، احتمالاً بیش از حد بزرگ طراحی شده.

## 34. Domain Event Naming

قاعده:
> **past tense + business meaning**

خوب:
- mission.started
- evidence.accepted
- gate.failed
- profile.claim_changed

ضعیف:
- update_done
- record_changed
- process_completed

## 35. ID Philosophy

Primary ID باید opaque باشد.

Business Code جدا نگه داشته می‌شود، مثلاً:
`responsibility_code = PM_PRODUCT_SCOPE`

## 36. Logical ER Core

Backbone:

**Person → AdmissionCase → CandidateJourney**

**CandidateJourney → MissionInstance → Observation → EvidenceCase → BehaviourPattern → ProfileUpdate → FlagProfile**

**FlagProfile → ResponsibilityAssessment → FlagBoardCase → AppointmentDecision**

Learning Loop:

**Evidence → LearningRecord → BehaviourCommitment → Replay Mission → New Evidence**

## 37. Architectural Invariants

ده Invariant غیرقابل‌مذاکره:
1. Mission همیشه به Version دقیق Pin می‌شود.
2. فقط Mission Runtime Simulation State را Mutation می‌دهد.
3. Observation بعد از Seal immutable است.
4. Evidence Interpretation Versioned و Reviewable است.
5. Profile از Raw Observation مستقیماً تغییر نمی‌کند.
6. AI/Event مستقیم Gate را Fail نمی‌کند.
7. Responsibility Recommendation با Appointment یکی نیست.
8. Evidence Freeze قبل از Board Decision الزامی است.
9. AI Direct Domain DB Write ممنوع است.
10. Governance History overwrite نمی‌شود.

## 38. عمداً باز برای Technical Architecture

در این مرحله هنوز نهایی نشده:
- PostgreSQL schema per context
- one DB vs multiple DBs
- exact message broker
- ORM mapping
- API transport
- event serialization technology
- cache strategy
- deployment topology

این‌ها در Technical Architecture v1 تصمیم‌گیری می‌شوند.

## تعریف نهایی

> **Domain Model پرچم باید هر تصمیم مهم را در Aggregate صاحب آن نگه دارد، هر Context فقط Truth خودش را Mutation کند، ارتباط Contextها با Contract و Event انجام شود، و کل زنجیره از تجربه Candidate تا مسئولیتی که به او سپرده می‌شود دارای Lineage قابل ممیزی باشد.**