# 36 — Product Backlog v1 (Blended Learning)

**وضعیت:** FINAL  
**تاریخ تثبیت:** 2026-10-04

## Product Goal

Parcham OS باید به‌عنوان سیستم عامل یک آکادمی توسعه رهبری، زنجیره زیر را به‌صورت یکپارچه پشتیبانی کند:

**Class → Practice → Simulator → Feedback → Reflection → Real Application → Evidence → Flag Profile**

اصل:
> **کلاس محل اصلی آموزش است؛ Simulator مکمل کلاس برای Practice، Transfer و Assessment است.**

## Backlog Strategy

اولویت Backlog:
**Safety / Governance dependency → Architectural dependency → Learning Journey continuity → End-to-End Product Value → Evidence value → UX polish**

## Epic 00 — Foundation Platform — P0
Outcome:
- Monorepo production-ready
- Backend/Frontend/Infra skeleton
- PostgreSQL + Alembic
- NATS JetStream
- Keycloak/OIDC PKCE
- MinIO/S3 abstraction
- OpenTelemetry
- Docker Compose
- GitHub Actions
- Health/Readiness
- Standard error, trace, audit, outbox/inbox foundations

## Epic 01 — Identity, Organization & Roles — P0
Outcome:
- Person
- Organization
- Membership
- Organization Context
- Candidate role
- Instructor role
- Mentor role
- Assessor role
- Board/Admin roles
- Contextual authorization

## Epic 02 — Academy Core: Cohort, Class & Schedule — P0
Outcome:
- Cohort
- Cohort Membership
- Instructor Assignment
- Class / Learning Offering
- Session
- Schedule
- Session Status
- Attendance foundation
- Group foundation
- Milestone foundation

> **Cohort و Instructor از ابتدا First-class هستند، نه Feature جانبی آینده.**

## Epic 03 — Capability & Curriculum Registry — P0
Outcome:
- 15 PM Capabilities
- L0–L4
- Scope hierarchy
- Capability versions
- Curriculum version
- Waves
- Prerequisites
- Mapping Class/Practice/Simulator to Capability

## Epic 04 — Learning Experience — P0
Outcome:
- Learning Unit
- Class Content
- Pre-work
- Material
- Reading
- Knowledge Check
- Assignment
- Submission
- Instructor Feedback
- Session Completion

> **Learning Completion ≠ Proven Capability**

## Epic 05 — Candidate Journey & Home — P0
Outcome:
- Candidate Journey
- Track
- Current Wave
- Cohort
- Upcoming Sessions
- Learning Tasks
- Practice Tasks
- Proof Tasks
- Processing State
- Candidate Home answers «الان چه چیزی باید یاد بگیرم؟» و «الان چه چیزی باید اثبات کنم؟»

## Epic 06 — Instructor Workspace — P0/P1
Outcome:
- Assigned Classes
- Cohort Roster
- Session Schedule
- Materials
- Assignment overview
- Submission review
- Instructor Feedback
- Learning progress

Instructor cannot mutate Evidence History or directly mark Capability Proven.

## Epic 07 — Practice Layer — P1
Outcome:
- Workshop
- Case Study
- Guided Exercise
- Group Exercise
- Practice Attempt
- Feedback
- AI Tutor later through governed AI Gateway

Practice may produce developmental signals but is distinct from independent proof.

## Epic 08 — Mission Design — P1
Outcome:
- Mission Template
- Versioning
- Actors
- Information
- Constraints
- Rules
- Evidence Opportunities
- Difficulty
- Replay policy
- Learn/Practice/Assessment policies

## Epic 09 — Mission Runtime — P1
Outcome:
- Deterministic stateful simulator
- Candidate Actions
- Information Requests
- Decisions
- Events
- Consequences
- Actor State
- World State
- Replayable audit
- no LLM dependency for core correctness

## Epic 10 — Observation & Evidence — P1
Outcome:
- factual Observation
- sealing
- Evidence Case
- Interpretation
- Review
- Candidate Response
- Conflict
- Calibration
- independent review secrecy

## Epic 11 — Flag Profile — P1
Outcome:
- Capability Claims
- Competency Claims
- Gate projection
- Proven Scope
- Unproven Areas
- Claim lineage
- Profile snapshots

## Epic 12 — Reflection & Replay — P1
Outcome:
- Reflection
- Learning Record
- Behaviour Commitment
- Replay Requirement
- Behaviour Change verification

Flow:
**Evidence → Reflection → Behaviour Commitment → Replay → New Evidence**

## Epic 13 — Responsibility & Flag Board — P1
Outcome:
- Responsibility Definition
- Responsibility Assessment
- READY / READY WITH CONDITIONS / DIFFERENT SCOPE / NOT YET / BLOCKED BY GATE
- Evidence Freeze
- Board Review
- Board Decision
- Appointment Eligibility

## Epic 14 — Parcham AI Gateway & Roles — P1
Order of initial AI roles:
1. Tutor
2. Reflection Coach
3. Evidence Analyst
4. Actor Runtime
5. Curriculum Orchestrator Copilot
6. Responsibility Matcher

All AI use is governed, versioned, auditable and non-authoritative for consequential decisions.

## Epic 15 — Curriculum Orchestrator — P1
Outcome:
- Next Best Experience
- chooses among Class, Learning Unit, Practice, Workshop, Simulator, Replay, Reflection, Human Coaching, Real Project

> **Orchestrator is an Evidence Gap Resolver and Learning Journey Planner, not merely a course player.**

## Epic 16 — Real Projects — P2
Outcome:
- Apprenticeship
- Ownership Trial
- Learning & Evidence Contract
- Decision Rights
- Outcome
- External Source Events
- Real-world Observations

## Epic 17 — Admissions — P2
Outcome:
- Application
- Baseline Challenge
- Simulation Assessment
- Assessment Camp
- Selection Board
- ADMIT / RESERVE / REJECT
- Baseline Profile

## Epic 18 — Academy Studio Expansion — P2
Outcome:
- graphical curriculum authoring
- class/session authoring
- mission authoring
- actor/world/business pack management
- evidence mappings
- gate policies
- responsibility definitions
- AI policies

## Milestones

### M0 — Academy Foundation
**Auth + Cohort + Class + Curriculum + Candidate/Instructor Home**

### M1 — Learning Loop
**Class → Assignment/Practice → Feedback → Reflection**

### M2 — Evidence Loop
**Simulator → Observation → Human Review → Flag Profile**

### M3 — Development Loop
**Reflection → Replay → Behaviour Change**

### M4 — Trust Loop
**Responsibility → Flag Board → Appointment Eligibility**

### M5 — Intelligence Loop
**Parcham AI + Next Best Experience + governed AI roles**

## First Product Proof

> **یک Candidate در Cohort واقعی وارد می‌شود، کلاس و Learning Journey خود را می‌بیند، آموزش/تمرین را انجام می‌دهد و سپس در مسیر اثبات همان Capability به Practice/Simulator هدایت می‌شود.**

اولین Evidence Proof:
> **Mission → Observation → Evidence → Human Review → Flag Profile**

## Definition of Done

هر Backlog Item فقط زمانی Done است که:
- Product behaviour کامل باشد
- Backend + Frontend لازم وجود داشته باشد
- Domain invariants تست شده باشند
- API contract تست شده باشد
- Authorization enforce شود
- Migration وجود داشته باشد
- Observability لازم وجود داشته باشد
- Audit برای consequential actionها ثبت شود
- Documentation به‌روز باشد
- CI سبز باشد
- Acceptance criteria روی Stage اثبات شود

> **Merged ≠ Done.**

> **Backend endpoint ≠ Product capability.**