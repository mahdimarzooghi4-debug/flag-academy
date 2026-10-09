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


### P23-05 — Qualitative subject report card read model — BACKEND/CI VERIFIED (PARTIAL)
- `GET /api/v1/class-offerings/{class_offering_id}/report-cards/{person_id}` exposes learner-specific, per-CapabilityVersion class report facts with the real CapabilityVersion name/version.
- Learning Unit Progress, Assignment Submission, Practice Attempt and Instructor/Practice Feedback preserve exact source/parent IDs and recorded states/timestamps; Session Attendance preserves per-Session status, recording source ID, and explicit `NOT_RECORDED` when absent.
- Candidate own-only, Instructor assigned-class-only, Academy Admin same-organization read; Assessor global role alone fails closed. No new write aggregate, migration, mutation or formal-growth side effect.
- `app.flag_profile.public_reader.read_candidate_safe_reviewed_claims` is the Flag Profile-owned public read contract for current, human-applied CapabilityClaims. It scopes subject person, organization, track, and Capability *definition* identity (not CapabilityVersion ID), exposing candidate-safe claim ID/version/state/level/reviewed timestamp only.
- The report card field `reviewed_claim` is separate from `proof_state`: no synthetic mapping or automatic proof conversion. Reviewer/private rationale, provenance/confidence and assessment-internal records are not exposed.
- `learning_state` now uses the existing CandidateHome qualitative rule from a shared Learning-owned pure reader: `TO_LEARN`, `IN_LEARNING`, `LEARNING_COMPLETED` for a class CapabilityVersion's active units/assignments; missing active requirements return `null` (never an invented completion). CandidateHome shares this same rule; practice/attendance/reviewer data never counts as completion.
- `proof_state` and `next_learning_focus` remain `null` pending independent authoritative source contracts. Historical CandidateHome static `UNPROVEN` is NOT an authoritative ProofState.
- Mission summaries remain out of this slice because there is no trustworthy Mission-to-ClassOffering link. No grade, rank, average, readiness score or auto-progression.

Implementation and CI evidence:
- base report-card implementation `b57b23518bc61d889c6969b5ea9f39336415237e`, route `479bf752c5f53953d7523d86bbe50356aa32425d`, tests `cb3c5fe74ac79b5dd2d20ad9e33a7a2ed3ccbfc3`, fixture fix `08935d23adc4e32d1deea57141ee948cdf5d273d`, attendance type safety `936749c472f352cb6b373fca56ef0807ad3dbe62`, CI `37832493397` SUCCESS.
- public reviewed-claim contract `bdf0b9bc8a61fabfb76d3a6dc4b0715ed3b11c7b`, report integration `c76b86c5884d955cf0c0f87b2d4e3990042b802f`, report tests `8e2b916febdb7b5c36df5bd4d548b28055af580d`, public reader tests `cf1970d8c9c66b912248ddfb20dd9b6859cf6f0c`.
- CI `37834816816` SUCCESS (Backend, Frontend, E2E), including browser/live OIDC and existing AI governance verifications.
- shared LearningState commits: Learning-owned reader `f5a03f2448f8914c6ba2c064b9f382ac3803956a`, CandidateHome parity `bcc228c12c0e417ec88fc64afbc579d454d7fe5e`, class report `ece980b2a7701bfc886ff2281e504eeb8eb5a937`, active requirements `6ef7a45f53d39cdfb8ef3cabd50dfdd203e2a816`, report tests `bf28ac46fcddc8c942a27d1b5b27af42515b5b30`, semantics/parity tests `5071dccf490ea84e961fb81f30ee1f1b06c56b73`, import hygiene `503af44f3ea6f64f97f4170fd7c5f423add5dc27`.
- CI `37836558356` SUCCESS (Backend, Frontend, E2E). No scores, automatic progression, new Evidence, or formal-governance mutations.
- P23-05 remains PARTIAL: no Stage/QA Gate or final Sprint acceptance is claimed. Outstanding: authoritative ProofState public contract, next-focus policy and verified class-linked Mission participation.


### P23-06 — Candidate report-card experience — CODE/CI VERIFIED (current-cohort foundation)
- Candidate-only GET `/api/v1/cohorts/{cohort_id}/class-offerings` checks exact same-organization `CohortMembership(person_id, member_type=CANDIDATE)` before listing genuine `ClassOffering` items, including classes with no learning tasks. It performs no writes and discloses no cross-cohort class list.
- React `CandidateReportWorkspace` is mounted only in authenticated Candidate UI, derives current cohort and person IDs from real CandidateHome and identity context, and reads a selectable class's own `/class-offerings/{id}/report-cards/{person_id}` API; server-side report authorization remains authoritative.
- UI shows all returned CapabilityVersion subjects with recorded progress, feedback, class attendance, and candidate-safe human-reviewed claim. It explicitly distinguishes absent classes, absent sessions, unrecorded attendance (`NOT_RECORDED` ≠ `ABSENT`), missing lesson activities, no feedback, unavailable formal ProofState, and independently reviewed claims.
- Report subject cards are display-only and have their own CSS selector; operational Learning cards preserve existing controls. No grade, threshold, automatic Evidence/Profile/Gate transition or guessed focus. Mission is not attributed to class until a verified mapping exists.
- Backend source-scope/OpenAPI tests and React view/selection/missing-data tests added. Existing live OIDC browser E2E and AI Governance integration regression passed; a dedicated full report-card browser scenario remains for later P23-12 acceptance.

Code and CI evidence:
- candidate class discovery `9a9bfcd57b391ab0d9fdaad8b9ff0e0291878620`, router `a9365805e4d6ea0f8402c304ea046f27230abb42`, backend tests `aab5dc7a406693c2637bacf4974caf5d7bad0121`
- web component `7341f5db95aa6b74d72603b94db240350b56d49d`, integration `16ff69216bcf98de2a7fe91006c150d453988356`, view tests `ad853f1d4f8844f6d5503db21e7d99422a8e525e`, vitest fixture cleanup `597afe01351e4deb190218ad4dbda34a910cb1e0`
- browser regression fixes `cbfa7ff2dd40c44cc643103a42476d66a8bda7ae`, presentation selector `4621698b99e671e0bc28c783c746e9ea71ba8c50`, styles `b50194c56a0886e133e9817fab14d22b585d757e`.
- CI `37897611025` — SUCCESS (Backend, Frontend, E2E with live OIDC and AI governance regressions).
- Scope is current-cohort learner experience only, not unrestricted multi-cohort admin or instructor experience. PR #21 remains Draft/Open/Unmerged. Stage/QA/Release/Production not performed.


### P23-07 — Instructor Class Workspace — CODE/CI VERIFIED (foundation)
- New read-only `GET /api/v1/class-offerings/{class_offering_id}/sessions` resolves the exact organization of `ClassOffering` through its `Cohort`, then requires either a real same-class InstructorAssignment or ACADEMY_ADMIN. An unauthorized request is 404 before any Session data is read; no attendance writes or ownership inference.
- Existing `/me/instructor-home` supplies assigned-class choices and the existing feedback-action queues. React `InstructorClassWorkspace` embeds alongside `InstructorHome`, preserving its actual feedback submission actions rather than inventing new mutations.
- For the selected assigned class, the UI uses the existing class roster and activity read models; the new authorized class sessions list; existing session attendance GET; and existing per-person qualitative report card. Each backend endpoint independently enforces its own tenant/assignment/person scope.
- Candidate roster persons only are shown for attendance and report selection. An absent AttendanceRecord is displayed as `NOT_RECORDED`, never `ABSENT`; attendance remains ACADEMY_ADMIN-write only.
- Activity shows real source type/ID/state and truncation, with no raw practice text in the timeline. Feedback pending summaries originate from the instructor home read projection and are explicitly labeled as across the instructor's assigned classes, not inferred per selected class.
- Report shows per-CapabilityVersion educational LearningState, human-reviewed claim independently, and unknown ProofState without converting one into another. No grades, readiness, weighted averages, Evidence mutation, or automatic Gate decision.
- Backend tests verify GET-only OpenAPI, tenant and assignment isolation including unassigned/other-org 404, and admin read. React tests cover class/session/person selection, absent attendance, no class, error handling, source context, and separation of reviewed claim versus formal proof.
- Dedicated real-browser tests for every new P23-07 flow and cross-class denial are still required as part of P23-11/12; the existing live OIDC/browser and AI governance E2E regression suite is green.

Implementation and CI evidence:
- sessions backend `1c8fd84724dff55fde77d4756e47c97f2eed0303`; router `dffdbbb56800c51a945e7aeeeefb0c53c604a2bf`; backend tests `b144f35ae0f8fd59afa97c26f28c4682d11272ab`.
- Instructor UI `7b5900924e35e95e06236f531cf756dca138b162`; App integration `4e9745c4e765ae00c3346d1aba7ea9141ca6e0d0`; UI tests and tested HEAD `8bed43e417b27c72d9503bd5864c15a40e277764`.
- Exact-head CI `37900696895` SUCCESS: Backend, Frontend and E2E (including live OIDC and AI Governance).
- PR #21 remains Draft/Open/Unmerged. No Stage, QA Gate, human Release Approval, or Production.


### P23-08 — Academy Admin Operations Workspace — CODE/CI VERIFIED (bounded foundation)
- Academy Admin-only GET `/api/v1/admin/academy/cohorts` lists only the authenticated organization's real Cohort records, with stable code/ID ordering, bounded `limit <= 100`, `offset >= 0`, and explicit `next_offset` (never a silently complete catalog).
- Academy Admin-only GET `/api/v1/admin/academy/cohorts/{cohort_id}/classes` validates exact Cohort organization before reading ClassOffering records; same bounded and stable pagination, non-disclosing 404 on unknown/cross-org cohort. No new business ownership inferred.
- React `AdminAcademyOperationsWorkspace` is mounted only for authenticated ACADEMY_ADMIN. It supports paged Cohort and class selection, then reads the existing authorized class roster, sessions, recorded Session attendance, source-linked activity and a selected learner's qualitative report card; every underlying API independently enforces organization/class/person scope.
- Class members and instructor assignment IDs originate from CohortMembership/InstructorAssignment (no invented person display names). Attendance `NOT_RECORDED` is explicitly distinct from human-recorded `ABSENT`. Admin's PRESENT/ABSENT buttons invoke ONLY the existing admin-authorized attendance mutation with actual current `expected_version` and independent idempotency key; successful commands refresh attendance, activity and report, while errors are surfaced without success claims.
- The report remains per real CapabilityVersion. Educational LearningState and human-applied Flag Profile Claim are shown separately; formal ProofState is unknown until an independently approved contract exists. There is no score, grade, auto-gate decision, automatic Evidence, or new authorization.
- Existing AcademyStudio retains authorized Mission template/assignment work; assessment/Evidence/Gate operations are NOT consolidated into a new cross-role administrative queue or inferred via capability matching. No new Mission-to-ClassOffering linkage is invented.
- Backend tests cover GET-only OpenAPI, query bounds, exact organization filter, non-disclosing cross-org rejection, paging and empty catalogs. React tests cover true missing attendance, explicit status-action callbacks, selector and paging changes, error privacy, and formal proof separation.
- Existing browser E2E with live OIDC and AI Governance regression passed; a comprehensive dedicated browser acceptance for new admin navigation/attendance and negative-role cases remains under P23-11/12, and is not a Stage pass.

Implementation and CI evidence:
- backend discovery `d9813a149819063dd5fbf67802544b5261e7f7c7`, router `871286adf138dbd6cc03d3f6b37ab75da8aa44aa`, backend tests `63b3f418cbbf5b8a7d4f011217e7f73b35822a54`;
- admin UI `07df06f296f780fa3fecac00be7fe53b4249f0a1`, App integration `74f7538a30fbbdd02d9ffc4ac1791c52b1da8cd2`, frontend tests `7e8472ad10f48e375dd454766276824aabc92cf2`;
- type-safety CI fix `f43286f305b4dfbd7ae76556f3d95f9430424b23`, E2E heading selector fix / tested HEAD `05ee6fb6962c4910787804a47f8a9168eefe7e92`;
- exact-head CI `37902990284`: SUCCESS (Backend, Frontend, E2E with live OIDC and AI Governance verification).
- PR #21 remains Draft/Open/Unmerged. No Code Review sign-off, Stage, QA Gate, Release Approval, or Production.


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
