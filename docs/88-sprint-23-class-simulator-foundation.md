# 88 — Sprint 23: Class Simulator Foundation

**Status:** ACTIVE  
**Date:** 2026-10-08  
**Parent:** Sprint 22 — Parcham AI Foundation  
**Base branch:** `sprint-22-parcham-ai-foundation`  
**Working branch:** `sprint-23-class-simulator-foundation`

## Goal

Turn Parcham's existing Cohort/Class/Learning/Mission/Evidence foundations into one coherent **Class Simulator** product contract.

The business model is:

**One class reality → different role views**

- Candidate experiences the class as learner.
- Instructor operates the same class as teacher.
- Assessor observes the same class for formal evidence.
- Academy Admin sees operational class truth across people, attendance and activity.
- Parcham AI assists only from the data authorized for the active role plus approved Academy Knowledge.

Sprint 23 does **not** introduce a new score-based school model. It does not make attendance, course completion, report-card presentation, or AI output equivalent to formal proof of capability.

## Existing foundations reused

Sprint 23 must extend the current architecture rather than build parallel models.

Existing Academy truth:
- `Cohort`
- `CohortMembership`
- `ClassOffering`
- `Session`
- `InstructorAssignment`

Existing Learning truth:
- `LearningUnit`
- `LearningUnitProgress`
- `Assignment`
- `Submission`
- `InstructorFeedback`
- `PracticeAttempt`
- `PracticeFeedback`

Existing Simulation truth:
- Mission Design
- Mission Assignment
- Mission Instance
- Candidate Action
- Decision Record
- Runtime Event
- Observation

Existing formal-growth truth remains:
- Evidence
- Reviewed Behaviour Pattern
- Flag Profile
- Gate Assessment

Sprint 23 MUST NOT duplicate these aggregates under a new simulator schema.

## Business contract

### 1. Class Simulator is the shared context

A Parcham class is not a static dashboard.

It is the shared context in which:
- people belong to a Cohort/Class;
- Sessions happen;
- attendance is recorded;
- learning activities and Missions are performed;
- instructors provide feedback;
- Assessors inspect eligible observations/evidence;
- report cards summarize learning truth;
- formal growth remains governed through Evidence → Pattern → Profile → Gate.

The role changes the view and permitted action, not the underlying class reality.

### 2. “Subject” in v1 maps to Capability, not a new curriculum entity

Existing Parcham decision remains authoritative:

> Curriculum design unit is Capability, not course/content.

Therefore Sprint 23 MUST NOT create a new authoritative `Subject` entity merely because the UI uses the Persian word «درس».

For Class Simulator v1:
- learner-facing «درس» is a presentation of an existing versioned `CapabilityVersion`;
- `ClassOffering` is the operational class delivery context;
- Learning Units / Assignments / Missions may point to the relevant Capability Version according to their existing contracts.

If a future product requirement proves that one business Subject must own multiple independent Capabilities as a first-class aggregate, that requires a separate explicit decision.

### 3. Attendance is operational truth only

Parcham needs attendance because instructors and Academy Admins need to operate a real class.

Initial business vocabulary is intentionally minimal:
- `PRESENT`
- `ABSENT`

No AttendanceRecord means **attendance has not been recorded**. It MUST NOT be interpreted as ABSENT.

Sprint 23 MUST NOT invent:
- LATE;
- EXCUSED;
- attendance score;
- attendance percentage threshold;
- attendance-based progression;
- attendance-based capability proof.

Attendance may be shown in operational and report-card views, but:
- attendance alone is not Learning Completion;
- attendance alone is not Evidence;
- absence alone is not weakness, failure, low motivation or Gate failure;
- Parcham AI must not infer personal reasons for absence.

Attendance recorder/correction authority for v1 is now explicit:

- only an authorized `ACADEMY_ADMIN` records attendance;
- only an authorized `ACADEMY_ADMIN` corrects a prior attendance record;
- every correction remains versioned/auditable and the previous value must remain reconstructable;
- no second-approver / maker-checker requirement is introduced by this decision.

Assigned Instructors may read attendance for their assigned class but do not mutate attendance in v1.

### 4. Class roster

A class roster is an operational read model of authorized class participants.

It must be able to represent at least:
- Candidate membership;
- assigned Instructor;
- explicitly authorized Assessor context when that policy is implemented;
- Academy Admin scoped view.

A global `ASSESSOR` role MUST NOT automatically grant visibility into every class.

Exact Assessor-to-Class assignment mechanics are intentionally unresolved in this planning slice and must be explicitly defined before implementation.

### 5. Unified class activity

Instructor and Academy Admin need a coherent activity view without replacing source-domain ownership.

The class activity view may compose references from:
- learning-unit progress;
- assignment submissions;
- practice attempts and feedback;
- mission assignments / instances / events;
- attendance;
- eligible assessment workflow states.

It is a **read model**, not a new event source of truth.

Activity composition MUST preserve:
- source aggregate/reference;
- source timestamp;
- subject person;
- class/session context when available;
- visibility policy.

### 6. Multi-subject report card

Each learner may have a qualitative report-card view per learner-facing «درس» / `CapabilityVersion`.

The report card is a **derived read model**. It does not own Capability truth and cannot mutate Evidence/Profile/Gate.

A report-card subject view may surface:
- Capability/lesson identity and version;
- relevant class context;
- attendance summary;
- recent learning activity;
- Mission activity;
- Instructor feedback;
- existing `LearningState`;
- existing formal `ProofState` only when sourced from its authoritative contract;
- next learning focus when explicitly set by approved curriculum/instructor workflow;
- source references sufficient for audit.

It MUST NOT synthesize:
- a numeric grade;
- GPA/average;
- percentage;
- class rank;
- hidden readiness score;
- proof state from attendance/activity counts;
- automatic progression.

Missing data must be represented as missing/insufficient data, never as zero or failure.

### 7. Report card and formal growth remain separate

The user-facing report card explains the learning journey.

Formal growth remains:

**Observation → Accepted Evidence → Reviewed Pattern → Profile Update Proposal → Human Review → Explicit Apply → Gate Review**

Rules:
- completing a lesson does not automatically create formal Evidence;
- Instructor feedback does not automatically create formal Evidence;
- a positive report card state does not automatically change CapabilityClaim;
- report-card display never passes a Gate;
- formal proof may be displayed read-only in a report card only from the authoritative formal-growth contract.

### 8. Manager operational visibility

Academy Admin needs an operational Academy/Class view containing authorized information such as:
- Cohorts / classes;
- people and role;
- upcoming/current Sessions;
- attendance recording status;
- recent learner activity;
- Instructor activity requiring attention;
- assessment queues where the Admin is authorized to see them;
- Mission activity;
- qualitative report-card summaries.

The Admin view must remain tenant/class scoped.

“Manager can see all information” means all **authorized operational Academy information**, not unrestricted private reviewer notes, hidden assessment mechanics, AI secrets, or cross-tenant data.

### 9. Academy Knowledge is separate from Model Training Data

Parcham AI requires approved Academy knowledge before it can become a useful instructor assistant.

Academy Knowledge may include:
- approved curriculum/capability definitions;
- approved learning content;
- approved Mission content;
- teaching guidance;
- feedback guidance;
- approved vocabulary;
- product/governance rules;
- approved examples.

Every knowledge source must eventually be:
- versioned;
- approved;
- attributable to an owner/source;
- traceable;
- revocable/retirable without silently rewriting historical audit.

Critical separation:

**Academy Knowledge approval for day-to-day assistance**

is not the same authorization as:

**AI-learning eligibility for Governed Dataset → Training → Model Version → Evaluation → Human Promotion**

Knowledge-use approval alone MUST NOT automatically:
- create a Training Dataset;
- start Training;
- change model weights;
- promote a model;
- activate runtime.

If an Academy Knowledge source is separately approved by policy for AI learning, DEC-625 / DEC-626 / DEC-627 apply and the eligible source may enter the Automatic Dataset Builder with its required provenance, purpose and governance.

The storage/indexing/retrieval implementation for Academy Knowledge is intentionally unresolved in this planning slice.

## Role contract

### Candidate

Can see:
- own class/cohort context;
- own Sessions;
- own Learning Units / Assignments / Missions;
- own Instructor feedback;
- own qualitative report card;
- candidate-safe formal growth projection.

Can act on:
- permitted learning activities;
- practice/replay;
- assigned Missions.

Cannot:
- alter attendance truth;
- accept formal Evidence;
- alter Profile/Gate;
- see another learner's private record.

### Instructor

Can see for assigned class scope:
- roster;
- Sessions;
- recorded attendance;
- learning activity;
- submissions/practice attempts;
- Mission learning context when authorized;
- learner qualitative report-card views relevant to teaching.

Can:
- teach;
- provide feedback;
- select/approve learning content according to future content policy;
- read attendance for their assigned class.

Instructor attendance mutation is not permitted in v1; Attendance recording/correction belongs to an authorized Academy Admin.

Cannot:
- automatically convert feedback/activity into formal Evidence;
- directly mutate Candidate formal Profile/Gate through the teaching surface.

### Assessor

Can see:
- explicitly authorized class/subject context;
- Observation/Evidence lineage required for assessment;
- relevant formal profile/gate facts through existing public contracts.

Cannot:
- use global role membership as universal class access;
- turn attendance or report-card presentation into Evidence automatically;
- coach the Candidate in Assessment mode.

### Academy Admin

Can see authorized operational Academy truth:
- classes;
- people;
- roles;
- sessions;
- attendance;
- class activity;
- report-card summaries;
- Mission Studio;
- AI governance.

Can:
- record PRESENT / ABSENT attendance for authorized class Sessions;
- correct a prior Attendance record while preserving version/audit history.

Admin visibility does not bypass:
- tenant isolation;
- assessor-private rationale restrictions;
- hidden evaluation mechanics;
- formal Human Review boundaries.

### Parcham AI

May:
- summarize;
- draft;
- propose;
- retrieve approved Academy Knowledge;
- prepare instructor/admin context;
- surface uncertainty.

Must not:
- infer missing attendance;
- infer personal reason for absence;
- invent report-card grades;
- convert activity into formal proof automatically;
- mutate CapabilityClaim;
- pass/fail Gate;
- use raw operational activity for model training without governed Dataset eligibility.

## Technical contract

### Bounded-context ownership

Sprint 23 extends existing contexts:

**Academy owns**
- Cohort;
- ClassOffering;
- Session;
- Cohort membership;
- Instructor assignment;
- Attendance truth.

**Learning owns**
- Learning Unit / progress;
- Assignment / submission;
- Practice attempts;
- Instructor learning feedback.

**Mission Design / Runtime own**
- Mission definitions;
- assignment;
- simulation execution;
- runtime activity.

**Evidence / Pattern / Flag Profile / Gate own**
- formal-growth truth.

**Read Models compose**
- roster;
- class workspace;
- class activity timeline;
- qualitative report card;
- manager operational projection.

No read model becomes an authoritative write aggregate.

### Attendance persistence direction

Expected relational identity:

**session × person**

Attendance must be tenant/class scoped through the Session → ClassOffering → Cohort chain.

Expected properties include:
- session reference;
- person reference;
- attendance status;
- record version;
- recorded timestamp;
- accountable recorder;
- correction/audit lineage sufficient to reconstruct changes.

Attendance mutations are authorized only for `ACADEMY_ADMIN` in v1. Assigned Instructors remain read-only for Attendance. Public mutation APIs may be implemented only with tenant/class/session scoping, version safety and audit preservation.

### Report-card read-model identity

Conceptual key:

**person × organization_context × capability_version × relevant class/cohort context**

The projection should compose source facts but not recalculate formal proof.

It must remain possible to answer:

> Which source facts caused this report-card field to be displayed?

### Security

All class operational reads must:
- tenant-scope before data return;
- class/cohort-scope actors before revealing roster/activity;
- fail closed on unauthorized class access;
- never expose another learner's private record through Candidate surfaces.

### Events / projection

Sprint 23 should reuse existing domain/outbox facts wherever available.

If Attendance is implemented, Attendance changes must be auditable and projection-safe.

A generic “activity” event that duplicates every domain event SHOULD NOT be created merely for the dashboard; the unified timeline should project from authoritative source events/records.

## Scrum / Product Backlog

### P23-01 — Class Simulator architecture guards — COMPLETE
- shared-class / role-view contract recorded;
- no new Subject entity;
- no score/GPA/rank;
- no attendance-based proof/progression;
- report card remains derived.

### P23-02 — Attendance foundation — COMPLETE
- Academy-owned relational AttendanceRecord;
- PRESENT / ABSENT only;
- missing record remains NOT RECORDED and is never inferred as ABSENT;
- ACADEMY_ADMIN-only record/correction API;
- assigned Instructor read-only attendance access;
- optimistic version safety;
- idempotent command replay with conflict detection;
- append-only DB-enforced AttendanceRevision audit history;
- attendance recorded/corrected domain events;
- zero Evidence/Profile/Gate mutation.

Completion evidence:
- implementation HEAD: `216055fc0fe90265962261737e349aef290321dc`
- CI run: `37820626275` — SUCCESS
- Backend: SUCCESS
- Frontend: SUCCESS
- Live OIDC E2E: SUCCESS

### P23-03 — Class roster read model — COMPLETE (backend foundation)
- GET `/api/v1/class-offerings/{class_offering_id}/roster` composes existing Cohort, ClassOffering, CohortMembership and InstructorAssignment; no new aggregate, migration or writes.
- Candidate sees only their own membership; assigned Instructor sees the class roster; authorized Academy Admin sees the organization-scoped roster.
- Unauthorized actors, cross-organization requests and global Assessor-only access fail closed with non-disclosing 404; Assessor assignment mechanics remain separately unresolved.
- OpenAPI and backend guard tests cover GET-only contract, role/tenant checks and absence of formal growth mutation; full role-browser UX remains a later Sprint 23 slice.

Completion evidence:
- code commit `463de938fbade3b8f6b17d1d866efdefb12d0669`; test commit and tested HEAD `c93c6c32d8b76d60b3fe5f5b53c7070def8f52d5`
- CI `37828166995` — SUCCESS (Backend, Frontend and E2E); PR #21 kept Draft/Open/Unmerged.


### P23-04 — Unified class activity read model — COMPLETE (backend foundation)
- GET `/api/v1/class-offerings/{class_offering_id}/activity` composes Academy Attendance with Learning Unit Progress, Assignment Submission, Instructor Feedback, Practice Attempt and Practice Feedback.
- Every item preserves source kind/id, source parent, subject person, class context, real timestamp, and source status where present; read model has no mutation authority.
- Class- and tenant-scoped Candidate-own, assigned Instructor, Academy Admin visibility; global Assessor role is never sufficient.
- No raw feedback/attempt text, no made-up absent state or formal proof, and no Mission activity while a verified Mission-to-ClassOffering linkage is unavailable.
- Source-local bounded reads, chronological merge, truncation reporting.
- Backend tests cover source lineage, absence of writes, role/tenant isolation and OpenAPI.

Completion evidence:
- implementation commits `6e7332f97e7ed9da6cdf196880aec5981de479b3`, `ceb7ccae225d4aa6b54f8f106dd534211c9f9a48`, tests `9c8f5843743f464ba0eba2f1944644d2336cd3cf`
- CI fixes `91ced146bb62f11ca862fa779424d68b244d2ef7` (Lint) and `3d963a8a53cf5f5c578eb835a46653708d038900` (Pyright test-double types)
- CI `37830689165` — SUCCESS, Backend/Frontend/E2E
- No Stage/QA gate, Production, or human release approval claimed.


### P23-05 — Qualitative subject report card read model
- per CapabilityVersion learner-facing «درس»;
- attendance + learning + mission + feedback summaries;
- existing LearningState / authoritative ProofState only;
- no numeric grade/average/rank;
- source traceability.

### P23-06 — Candidate report-card experience
- own multi-subject report card;
- plain-language missing-data state;
- formal growth clearly separated.

### P23-07 — Instructor Class Workspace
- class roster;
- attendance read state;
- recent activity;
- feedback work queue;
- report-card view;
- same underlying class context as Candidate.

### P23-08 — Academy Admin Operations Workspace
- people;
- classes;
- sessions;
- attendance;
- recent activity;
- report-card summaries;
- Mission / assessment operational queues under authorization.

### P23-09 — Assessor class-context binding
- explicit authorized class context;
- Evidence workspace can display class/session context;
- global ASSESSOR role alone is insufficient for unrestricted class roster access.

### P23-10 — Academy Knowledge foundation — ACTIVE
- versioned/approved/traceable source contract;
- explicit separation from AI Training Dataset;
- Initial Knowledge Pack v1 authored in `docs/89-parcham-ai-initial-knowledge-pack-v1.md`;
- Decision-Making Curated Synthetic Seed Corpus v1 authored in `docs/90-parcham-ai-decision-making-seed-corpus-v1.md` and `docs/ai/seed/decision-making-v1.jsonl`;
- Seed corpus contains 24 source-linked synthetic examples spanning Learn / Practice / Assessment / Instructor-assist / Governance behaviour;
- existence of Seed content does not create a Dataset or authorize Training;
- Human-governed Seed Learning Approval Bridge — COMPLETE;
- exact Seed artifact digest preview + ACADEMY_ADMIN-only explicit approval implemented;
- approval emits existing `ai.learning_input_approved.v1` through Domain Event + Outbox;
- existing Automatic Dataset Builder remains the only Dataset Version creator;
- CI acceptance proves ephemeral Seed → approval → Dataset Version 1 without Training/runtime activation;
- completion CI evidence: implementation `36ce527916c2824f35290f9b6f367d3851e8b217`, run `37825433611` SUCCESS (Backend, Frontend, E2E); follow-up HEAD `644e444cde35b64a83abdbb052feb9db2f07d284`, CI `37826174432` SUCCESS;
- acceptance source: `backend/scripts/ai_seed_learning_approval_acceptance.py` verifies `training_started=NO` and `runtime_activation=NO`;
- real Academy-environment Seed approval has not been executed;
- Academy Knowledge retrieval/indexing and model-runtime technology remain unresolved and are not selected in this slice.

### P23-11 — Interaction / stale-safety / security tests
- role isolation;
- tenant isolation;
- missing attendance safety;
- report-card provenance;
- stale projection behavior;
- no formal-growth mutation from report card.

### P23-12 — Live OIDC E2E + Stage Acceptance
- Candidate / Instructor / Assessor / Admin view same class truth appropriately;
- no private cross-role leakage;
- no score invention;
- no attendance-driven progression;
- no AI-driven consequential decision.

## Explicit unresolved product decisions

These MUST NOT be guessed in code:

1. Do future attendance statuses beyond PRESENT / ABSENT exist (late, excused, remote, etc.)?
2. Does a Session become attendance-locked after a defined lifecycle state?
3. What explicit mechanism scopes an Assessor to a class?
4. Does Parcham ever introduce numeric subject grades? If yes, the formula/scale/governance requires a separate contract.
5. What storage/index/retrieval technology serves Academy Knowledge?
6. Which Academy Knowledge categories are permitted to reach each AI mode?
7. Which instructor content-generation actions may eventually execute automatically versus requiring confirmation?

## First implementation slice — COMPLETE

**Attendance persistence foundation + architecture guards** is complete on the evidence recorded under P23-02.

The next implementation slice is:

**P23-03 — Class roster read model**

It must remain read-model only and must not yet add:
- Attendance UI editing;
- Report-card projection;
- Assessor global class visibility;
- Academy Knowledge retrieval;
- Instructor AI runtime.

## Definition of Done

Sprint 23 is accepted only when:

1. existing Academy/Learning/Mission/formal-growth sources remain authoritative.
2. no parallel Subject aggregate is introduced without a separate decision.
3. Attendance is auditable operational truth and never implicit proof/progression.
4. no missing attendance record is interpreted as ABSENT.
5. role-scoped roster/class access fails closed.
6. report card is derived, qualitative and provenance-aware.
7. report card does not mutate Evidence/Profile/Gate.
8. Candidate sees only own private learning/report data.
9. Instructor/Admin operational views are class/tenant scoped.
10. Assessor access is explicitly scoped.
11. Academy Knowledge remains separate from Training Dataset.
12. no external AI provider/runtime is introduced.
13. CI, Live OIDC E2E and Stage Acceptance prove the above invariants.

## Out of scope

- numeric grading/GPA/ranking;
- attendance-based completion/progression;
- attendance reason inference;
- a new authoritative Subject bounded context;
- automatic formal Evidence creation from classroom activity;
- automatic CapabilityClaim update;
- automatic Gate decision;
- final Gemma runtime;
- AI instructor assistant runtime;
- Academy Knowledge vector/index technology selection;
- Production deployment.
