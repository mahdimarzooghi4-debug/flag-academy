# 37 — Sprint 1: Academy Foundation Vertical Slice

**وضعیت:** FINAL  
**تاریخ تثبیت:** 2026-10-04
**Execution Status:** ACCEPTED — Stage Acceptance PASS on 2026-10-04

## Sprint Goal

> **یک Candidate احراز هویت‌شده بتواند وارد Parcham OS شود، Cohort و برنامه آموزشی جاری خود را ببیند، کلاس‌ها و Capabilityهای جاری را مشاهده کند و سیستم به‌صورت واقعی نشان دهد «چه چیزی باید یاد بگیرم؟» و «چه چیزی باید اثبات کنم؟»؛ هم‌زمان Instructor بتواند حداقل Assignment آموزشی خودش به Cohort/Class را ببیند.**

Vertical Slice:
**Browser → Auth → API → Domain → PostgreSQL → Read Model → UI**

## Story 1 — Production Repository Skeleton

ساختار:
- backend/
- frontend/
- infra/
- docs/
- scripts/

Backend moduleهای Sprint:
- identity
- academy
- curriculum
- journey
- platform
- read_models
- api

هر Module:
- domain/
- application/
- infrastructure/
- api/

Acceptance:
- app boots
- module boundaries testable
- no cross-context repository imports
- /health
- /ready

## Story 2 — Local Development Environment

docker compose up وابستگی‌های Sprint را بالا می‌آورد:
- PostgreSQL
- Keycloak
- NATS JetStream
- MinIO
- OpenTelemetry Collector

Temporal configuration می‌تواند آماده باشد، اما چون Sprint 1 workflow طولانی ندارد، Critical Path نیست.

## Story 3 — PostgreSQL & Alembic Foundation

Schemaها:
- identity
- academy
- curriculum
- journey
- platform
- readmodel

Alembic تنها مسیر migration.

## Story 4 — Keycloak OIDC PKCE

Flow:
**Browser → Keycloak → Authorization Code → PKCE Exchange → Access Token → API**

Backend validates:
- signature
- issuer
- audience
- expiration
- subject mapping

## Story 5 — Request Identity Context

Per-request context:
- actor_id
- person_id
- organization_context_id
- roles
- trace_id

Domain JWT را نمی‌شناسد.

## Story 6 — Organization & Role Foundation

Entities:
- Person
- Organization
- OrganizationMembership
- Role Assignment

حداقل Roleها:
- CANDIDATE
- INSTRUCTOR
- ACADEMY_ADMIN

Fine-grained policy در Backend.

## Story 7 — Cohort Foundation

Aggregate/Data:
- Cohort
- Cohort Membership
- Cohort Status
- Track
- Start/End dates

Candidate باید عضو Cohort واقعی باشد.

## Story 8 — Class & Session Foundation

Entities:
- ClassOffering
- Session
- InstructorAssignment
- SessionSchedule

Session fields حداقل:
- title
- capability_version_refs
- starts_at
- ends_at
- delivery_mode
- status

Delivery Mode:
- IN_PERSON
- ONLINE
- HYBRID

## Story 9 — Instructor Foundation

Instructor به Class/Cohort assign می‌شود.

Read endpoint:
GET /api/v1/me/instructor-home

Minimum output:
- assigned classes
- upcoming sessions
- cohort roster count
- current curriculum/wave

Sprint 1 Instructor Workspace read-only است.

## Story 10 — Capability Registry

Seed 15 PM Capabilities.

Levels:
- L0
- L1
- L2
- L3
- L4

Scopes:
- TASK
- PROJECT
- TEAM
- PRODUCT
- BUSINESS
- ORGANIZATION

Capability versioning واقعی.

## Story 11 — Curriculum v1

PM Curriculum Version 1 با Waveهای:

Wave 1 — Think & Own:
- Ownership & Accountability
- Problem Framing
- Decision Making
- Data Thinking
- Reflection & Learning

Wave 2 — Discover & Decide:
- Customer Understanding
- Product Discovery
- Metrics & Experimentation

Wave 3 — Direct & Deliver:
- Product Strategy
- Prioritization
- Product Economics
- Delivery
- Stakeholder Alignment

Wave 4 — Lead & Build:
- Product Leadership
- System Building
- higher-scope Reflection

## Story 12 — Learning Journey Mapping

Class/Sessionها به Capability Version متصل می‌شوند.

Candidate Home Learning side را از Proof side جدا نمایش می‌دهد.

حداقل State:
- TO_LEARN
- IN_LEARNING
- LEARNING_COMPLETED
- UNPROVEN

LEARNING_COMPLETED هرگز خودکار PROVEN نمی‌شود.

## Story 13 — Candidate Journey

CandidateJourney:
- person_id
- organization_context_id
- cohort_id
- track_code
- curriculum_version_id
- state
- current_wave
- version

States:
- ACTIVE
- PAUSED
- COMPLETED
- WITHDRAWN

Admissions در Sprint 1 bootstrap/seed می‌شود و بعداً جایگزین خواهد شد.

## Story 14 — Candidate Home Read Model

Endpoint:
GET /api/v1/me/candidate-home

Minimum sections:
- journey
- cohort
- current_wave
- upcoming_sessions
- what_to_learn
- what_to_prove
- learning_tasks
- open_missions
- profile_summary
- processing_states

در Sprint 1:
- open_missions = empty
- profile_summary = UNPROVEN

هیچ Fake Score وجود ندارد.

## Story 15 — Candidate Home UI

دو بخش اصلی:

### چه چیزی باید یاد بگیرم؟
- upcoming class/session
- capability
- pre-work placeholder/state
- learning state

### چه چیزی باید اثبات کنم؟
- Wave capability list
- current proof state
- initially UNPROVEN

همچنین Cohort، Track و Current Wave نمایش داده می‌شوند.

## Story 16 — Instructor Home UI

حداقل:
- Assigned Cohort
- Assigned Class
- Upcoming Sessions
- Number of Candidates
- Capability focus

هدف Sprint 1 ایجاد Role و Surface واقعی Instructor است، نه کامل‌کردن LMS feature set.

## Story 17 — RTL Foundation

Persian RTL first-class:
- dir=rtl
- Persian typography
- RTL layouts/forms
- technical IDs/code in LTR components

## Story 18 — Event Envelope + Outbox

Event envelope استاندارد پیاده می‌شود.

حداقل Eventها:
- academy.cohort_created.v1
- academy.session_scheduled.v1
- candidate.journey_created.v1

Outbox write در همان DB transaction.

## Story 19 — NATS Dispatcher + Inbox Foundation

Worker:
**Outbox → NATS JetStream → published_at**

Consumer idempotent.

Inbox unique:
**consumer_name + event_id**

## Story 20 — Read Model Projection

Projectionهای Sprint:
- readmodel.candidate_home
- readmodel.instructor_home

Browser نباید چند Context را ad-hoc Join کند.

## Story 21 — OpenAPI Contract

حداقل endpointها:
- GET /health
- GET /ready
- GET /api/v1/me
- GET /api/v1/me/candidate-home
- GET /api/v1/me/instructor-home
- GET /api/v1/capabilities
- GET /api/v1/capabilities/{id}
- GET /api/v1/curricula/{id}
- GET /api/v1/cohorts/{id}/schedule

TypeScript client از OpenAPI Generate می‌شود.

## Story 22 — Standard Error Model

Error contract:
- code
- message
- details
- trace_id
- retryable

Minimum codes:
- AUTHENTICATION_REQUIRED
- INSUFFICIENT_PERMISSION
- PERSON_NOT_FOUND
- ORGANIZATION_CONTEXT_REQUIRED
- CANDIDATE_JOURNEY_NOT_FOUND
- INSTRUCTOR_ASSIGNMENT_NOT_FOUND
- COHORT_NOT_FOUND
- CURRICULUM_NOT_FOUND
- VERSION_CONFLICT
- INTERNAL_ERROR

## Story 23 — Optimistic Concurrency

Mutable aggregateها version دارند.

Last-write-wins ممنوع.

Conflict:
409 VERSION_CONFLICT

## Story 24 — Audit & Trace Foundation

Structured audit for:
- identity mapping
- organization context switch
- admin bootstrap/create operations

Structured JSON logs + trace_id.

> **Logs are for operations; Audit is for accountability.**

## Story 25 — Seed Strategy

Development seed:
- one organization
- one PM cohort
- one candidate
- one instructor
- PM curriculum v1
- 15 capabilities
- waves
- at least two scheduled sessions in Wave 1
- Candidate Journey
- Instructor Assignment

Production seed هیچ Demo User ایجاد نمی‌کند.

## Story 26 — Tests

Domain:
- capability version invariants
- cohort membership
- instructor assignment
- candidate journey transitions
- learning completion does not prove capability
- optimistic concurrency

Integration:
- PostgreSQL repositories
- migrations from clean DB
- outbox atomicity
- NATS publish
- OIDC token validation

API:
- candidate/instructor authorization
- home read models
- curriculum reads
- standard errors

Frontend:
- login callback
- Candidate Home
- Instructor Home
- unauthorized states

E2E:
1. Candidate login → Candidate Home → class + learn/prove sections
2. Instructor login → Instructor Home → assigned cohort/session

## Story 27 — CI Pipeline

Every PR:
- Backend Lint
- Pyright
- Unit
- Domain tests
- Integration tests
- Migration validation
- OpenAPI drift check
- Frontend type check
- Frontend tests
- Frontend build
- E2E smoke

Merge to main only with green CI.

## Sprint 1 Out of Scope

- Mission authoring
- Mission Runtime
- Evidence
- real Flag Profile claims
- AI roles
- Reflection workflow
- Assignment submission/review workflow
- Attendance workflow beyond foundation model
- Temporal workflow execution
- Flag Board
- Responsibility Engine
- Real Projects
- Admissions full flow
- Gamification / XP / Badges

## Demo Script

1. Clean environment بالا می‌آید.
2. Migration اجرا می‌شود.
3. Development seed اجرا می‌شود.
4. Candidate به App می‌رود.
5. Keycloak login انجام می‌شود.
6. Candidate Home باز می‌شود.
7. Cohort و PM Track نمایش داده می‌شود.
8. Wave 1 نمایش داده می‌شود.
9. Upcoming Class/Session دیده می‌شود.
10. بخش «چه چیزی باید یاد بگیرم؟» داده واقعی نشان می‌دهد.
11. بخش «چه چیزی باید اثبات کنم؟» Capabilityهای Wave 1 را با State UNPROVEN نشان می‌دهد.
12. هیچ Fake Score یا Completion Percentage به‌عنوان معیار اصلی وجود ندارد.
13. Instructor login می‌کند.
14. Instructor Home، Cohort/Class/Session assignment واقعی را نشان می‌دهد.
15. Requestها traceable هستند.
16. CI Commit را سبز تأیید کرده است.

## Sprint Acceptance Gate

Sprint فقط وقتی پذیرفته می‌شود که Vertical Slice روی Stage از clean deployment اجرا شود.

## Definition of Done

هر Story باید Implementation، Tests، Contract، Authorization، Migration، Observability، Documentation و CI لازم را داشته باشد و Acceptance Criteria روی Stage قابل اثبات باشد.

> **Merged ≠ Done.**

## Exit Condition

> **در پایان Sprint 1، Parcham OS فقط یک معماری یا Simulator prototype نیست؛ یک Academy Software واقعی است که Candidate و Instructor وارد آن می‌شوند، Cohort و کلاس واقعی دارند، Candidate می‌داند چه چیزی باید یاد بگیرد و چه چیزی هنوز باید اثبات کند، و تمام داده‌ها از Domainهای واقعی می‌آیند.**

## Next Sprint

Sprint 2:
**Learning Experience v1 + Class Materials + Pre-work + Assignment/Submission + Instructor Feedback + Practice Foundation**

Simulator از Sprintهای بعدی وارد می‌شود، پس از اینکه جریان اصلی آموزش کلاسی واقعاً در محصول وجود داشته باشد.

## Sprint 1 Acceptance Result

Sprint 1 acceptance is complete.

Evidence:
- Commit: `c7405e6658afe6d3e26ec6ec268eb0e3fd91c489`
- CI Run: `37223606979` — PASS
- Stage Acceptance Run: `37223607002` — PASS
- Browser OIDC Acceptance: PASS
- Published Outbox Events: 3
- Processed Inbox Events: 3
- Candidate Home Projection Rows: 1
- Instructor Home Projection Rows: 1

Sprint 1 is therefore **ACCEPTED** against its approved Definition of Done and Stage Gate.
