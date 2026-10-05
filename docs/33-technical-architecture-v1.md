# 33 — Technical Architecture v1

**وضعیت:** FINAL  
**تاریخ تثبیت:** 2026-10-04

## اصل طراحی

> **Parcham OS در نسخه اول یک Modular Monolith رویدادمحور است؛ Domainها مستقل‌اند، ولی پیچیدگی Distributed System تا زمانی که واقعاً لازم نشده وارد نمی‌شود.**

> **سادگی Deployment را حفظ می‌کنیم، بدون اینکه مرزهای Domain را قربانی کنیم.**

## 1. Technology Stack

- Backend: Python 3.12 + FastAPI
- Domain/Data: SQLAlchemy 2 async + Pydantic
- Database: PostgreSQL
- Migration: Alembic
- Event Backbone: NATS JetStream
- Long-running Workflow: Temporal
- Frontend: React + TypeScript + Vite
- Server State: TanStack Query
- Authentication: Keycloak + OIDC/OAuth2 PKCE
- Object Storage: S3-compatible؛ MinIO برای Local/Stage
- Knowledge / Vector: PostgreSQL Full Text + pgvector
- Observability: OpenTelemetry
- Testing: Pytest + Playwright
- Static Quality: Ruff + Pyright + TypeScript checks
- Local Environment: Docker Compose
- API Contract: OpenAPI 3
- CI/CD: GitHub Actions

در v1 عمداً Kubernetes، Kafka، Elasticsearch و Microservice proliferation وارد نمی‌شوند.

## 2. Modular Monolith Structure

Backend یک Deployable اصلی دارد ولی Bounded Contextها Moduleهای مستقل هستند.

ساختار مفهومی:

backend/
  app/
    identity/
    admissions/
    curriculum/
    learning/
    mission_design/
    mission_runtime/
    world_model/
    evidence/
    profile/
    responsibility/
    governance/
    real_projects/
    reflection/
    orchestration/
    ai/
    knowledge/
    audit/
    platform/
    read_models/
    api/

هر Module به Domain / Application / Infrastructure / API تفکیک می‌شود.

اصل:
> **Module می‌تواند API یا Event Contract ماژول دیگر را مصرف کند؛ نباید Repository داخلی آن را import کند.**

## 3. PostgreSQL Architecture

در v1 یک PostgreSQL Cluster کافی است.

برای هر Bounded Context PostgreSQL Schema منطقی جدا داریم، به‌علاوه platform و readmodel.

اصل:
> **Foreign Key بین Bounded Contextها ایجاد نمی‌شود.**

FK داخل Context مجاز است؛ Cross-context consistency از Contract/Event می‌آید.

## 4. Transaction Model

هر Command فقط Transaction Aggregate خودش را باز می‌کند.

Domain mutation و Outbox write در یک Transaction انجام می‌شوند.

اصل:
> **هیچ Dual Write مستقیم بین Database و Message Broker نداریم.**

## 5. Event Backbone

NATS JetStream برای Domain Event propagation استفاده می‌شود.

Delivery semantics:
**At-least-once + Idempotent Consumers**

Consumer باید event_id مصرف‌شده را در Inbox ثبت کند.

## 6. Temporal Boundary

NATS برای Event propagation است؛ Temporal برای Workflowهای طولانی، Retry، Timeout، Human Wait و Scheduling.

نمونه Workflowها:
- Admission
- Evidence Review Deadline
- Calibration
- Gate Remediation
- Flag Board
- Delayed Mission Effects
- Replay Scheduling

اصل:
> **Temporal Coordinator است؛ Source of Truth نیست.**

## 7. Mission Runtime Engine

Mission Runtime تا حد ممکن Deterministic و LLM-independent است.

Flow:
**Action → Validation → Rule Evaluation → Domain Event → State Mutation → Observation**

Mission Definitionها Declarative و Schema-validated هستند.

اصل:
> **Mission authoring نباید Remote Code Execution engine بسازد.**

## 8. World State Storage

World State JSON آزاد نیست؛ Schema-versioned و Pydantic-validated است.

Namespaceهای مشترک:
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

Snapshot در PostgreSQL JSONB ممکن است ذخیره شود؛ History واقعی از Event Log می‌آید.

## 9. Mission Concurrency

MissionInstance دارای world_state_version است.

Candidate Action باید روی Version مشخص اعمال شود.

در Conflict:
**409 WORLD_STATE_VERSION_CONFLICT**

## 10. Frontend Architecture

Frontend: React + TypeScript + Vite با Persian RTL به‌صورت First-class.

Server state: TanStack Query.

TypeScript API Client از OpenAPI Generate می‌شود.

Surfaceها می‌توانند Route/Layout جدا داشته باشند، مثل:
- /candidate/*
- /assessor/*
- /board/*
- /studio/*

## 11. API Strategy

v1 از REST/JSON + OpenAPI استفاده می‌کند.

Readها resource-oriented و Writeها business-oriented هستند.

نمونه:
- POST /api/v1/missions/{id}/actions
- POST /api/v1/evidence-cases/{id}/accept
- POST /api/v1/gate-assessments/{id}/decisions
- POST /api/v1/flag-board-cases/{id}/decision

برای Writeهای حساس:
- Idempotency-Key
- expected_version / If-Match

## 12. Error Contract

Error contract حداقل شامل:
- code
- message
- details
- trace_id
- retryable

Client نباید Logic را از متن پیام استخراج کند.

## 13. Real-time UX

v1 از REST + Server-Sent Events استفاده می‌کند.

REST برای Command و SSE برای Updateهای Server→Client.

WebSocket فقط در صورت نیاز واقعی به Collaborative Simulation یا Multi-user realtime اضافه می‌شود.

## 14. Authentication

Keycloak + OIDC Authorization Code + PKCE.

Browser هیچ Client Secret ندارد.

Keycloak Authentication و Roleهای کلان را مدیریت می‌کند؛ Fine-grained authorization در Backend انجام می‌شود.

## 15. Authorization

مدل:
**RBAC + Contextual / Attribute Policy**

مثال:
evidence.review فقط همراه assignment، organization match و policy context معتبر است.

## 16. Object Storage

Artifactهای حجیم در S3-compatible Object Storage ذخیره می‌شوند.

Local/Stage: MinIO.

Database فقط Metadata، content_hash، version، classification، owner_context و timestamps را نگه می‌دارد.

Download با Signed URL.

## 17. Knowledge & Retrieval

v1 از PostgreSQL Full Text Search + pgvector استفاده می‌کند.

Retrieval Index Source of Truth نیست؛ هر نتیجه باید به Knowledge Source Version قابل ردیابی باشد.

## 18. Parcham AI Runtime Boundary

Parcham AI هیچ Model/Inference/Training capability را از AI API، Provider LLM، Foundation Model API یا Managed AI Service داخلی/خارجی دریافت نمی‌کند.

Flow:
**Domain/Application → Parcham AI Runtime → Policy → Parcham Model Version → Structured Output**

Parcham AI Runtime مسئول:
- Parcham Model Version Selection
- Structured Output Validation
- bounded Retry
- Safety
- PII/Data Filtering
- Prompt/Instruction Version
- Policy Version
- Training/Evaluation Lineage
- Compute/Latency Metadata
- Tracing
- Evaluation Hook

چرخه یادگیری مستقل پرچم:
**Governed Parcham Data → Curated Dataset → Training → Offline Evaluation → Versioned Model Artifact → Promotion → Runtime**

## 19. Structured AI Outputs

AI Outputهای واردشونده به Workflow باید Typed و Pydantic-validated باشند.

در Output نامعتبر:
- Retry محدود
- سپس AI_OUTPUT_INVALID

Parsing heuristic برای نجات Output نامعتبر پذیرفته نیست.

## 20. AI State Mutation Boundary

> **AI هیچ Repository Write Permission ندارد.**

Parcham AI Runtime فقط Structured Proposal برمی‌گرداند؛ Application Service تصمیم می‌گیرد با آن چه کند.

AI Agent فقط Commandهای allowlisted را از Application API اجرا می‌کند.

## 21. Data Classification Before AI

هر AI Request یکی از:
- PUBLIC
- INTERNAL
- CONFIDENTIAL
- RESTRICTED

Policy تعیین می‌کند کدام داده با چه purpose و retention می‌تواند وارد inference، structured memory، curated dataset و training داخلی Parcham AI شود.

## 22. AI Audit

هر AIInvocation باید Role، Mode، Parcham Model ID/Version، Training Data Version، Evaluation Version، Policy Version، Prompt Policy Version، Tool Permissions، Data Classification، Output Schema، Compute Metadata، Latency و Policy Violation را ثبت کند.

## 23. Read Models

Projectionهای اختصاصی مانند CandidateHomeView، EvidenceReviewView و FlagBoardCaseView ساخته می‌شوند.

UI نباید Domain Truth را با ad-hoc join چند Endpoint بسازد.

## 24. Background Processing

Workerها مسئول:
- Outbox Dispatch
- Event Consumption
- Projection Update
- Evidence Preprocessing
- AI Invocation
- Scheduled Activities

v1 حداقل API Process، Worker Process و در صورت نیاز Temporal Worker دارد، اما Codebase همچنان Modular Monolith است.

## 25. Observability

OpenTelemetry برای API، Worker، AI Gateway و Event Consumer.

سه View:
- Technical Observability
- AI Observability
- Assessment Observability

تمام Requestها و Eventها trace_id دارند.

## 26. Logging

Logها Structured JSON هستند.

Sensitive data masking اجباری است.

اصل:
> **Logs are for operations; Audit is for accountability.**

## 27. Testing Strategy

چهار خانواده Test حیاتی:
- Domain Invariant Tests
- Integration Tests
- Simulation Determinism Tests
- Assessment Integrity Tests

Frontend E2E با Playwright.

AI Roleها Offline Evaluation Set دارند.

## 28. Golden Mission Tests

Missionهای VALIDATED باید Golden Scenario داشته باشند:
- Initial State
- Simulation Seed
- Candidate Actions
- Expected World Event Sequence

تغییر Rule Engine که Validity را تغییر دهد باید Test را Fail کند.

## 29. Database Migration

Alembic تنها مسیر Schema Migration است.

Production App هنگام Startup Migration خودکار انجام نمی‌دهد.

Deploy:
**Migrate → Deploy**

Migration destructive نیازمند Explicit Review است.

## 30. CI Pipeline

حداقل:
**Lint → Type Check → Unit Tests → Domain Tests → Integration Tests → Frontend Build/Test → Migration Validation → Contract/OpenAPI Check**

برای تغییر Mission/Assessment Logic:
- Golden Mission Tests
- Assessment Integrity Tests

## 31. Deployment Topology v1

Componentهای اصلی:
- Web
- API
- Worker
- Temporal Worker
- PostgreSQL
- NATS JetStream
- Keycloak
- Object Storage
- OpenTelemetry Collector

Temporal Server می‌تواند Managed یا Self-hosted باشد؛ Infrastructure Provider هنوز قفل نمی‌شود.

## 32. No Kubernetes in v1

> **Kubernetes جزء Architecture v1 نیست.**

Containers کافی‌اند و Kubernetes فقط با نیاز واقعی Scaling/HA/Cluster complexity وارد می‌شود.

## 33. Local Development

محیط کامل با docker compose up قابل بالا آمدن است.

شامل PostgreSQL، NATS، Keycloak، MinIO، Temporal و OTel dependencies.

Seed Data باید Scenarioهای نمونه ایجاد کند.

## 34. Repository Strategy

Monorepo:
- backend/
- frontend/
- infra/
- docs/
- scripts/

OpenAPI از Backend تولید و TypeScript Client از آن Generate می‌شود.

Domain Eventها Schema Version مشخص دارند.

## 35. Security Defaults

- TLS در Production
- Secret در Repository ممنوع
- Secret Manager برای Credentialها
- Signed URL برای Object Storage
- Least Privilege
- Audit برای Admin Actionهای Consequential
- Restricted Data check پیش از AI
- Direct DB access کاربران Product ممنوع

## 36. Backup & Recovery

PostgreSQL باید Point-in-Time Recovery داشته باشد.

Object Storage برای Artifactهای مهم Versioning/Backup دارد.

NATS تنها Archive Governance نیست؛ Event/Audit Record پایدار در PostgreSQL حفظ می‌شود.

## 37. Performance Strategy

v1 بدون Cache-heavy architecture شروع می‌شود.

اولویت:
- PostgreSQL Indexes
- Read Projections
- Async Processing

Redis فقط با Use Case واقعی وارد می‌شود.

## 38. Scaling Strategy

اولین Candidateهای Extract/Scale مستقل:
- AI Workers
- Mission Runtime Workers
- Evidence Processing

Bounded Contextهای دیگر فقط در صورت نیاز واقعی جدا می‌شوند.

## 39. Technical Non-negotiables

- Modular Monolith First
- PostgreSQL
- Context isolation via PostgreSQL schemas + no cross-context FK
- NATS JetStream
- At-least-once delivery + idempotency
- Transactional Outbox
- Temporal as coordinator only
- REST/OpenAPI
- SSE first
- OIDC PKCE / Keycloak
- S3-compatible Object Storage
- Parcham AI Runtime-only access
- Structured/validated AI output
- PostgreSQL FTS + pgvector first
- Optimistic Concurrency
- OpenTelemetry
- Append-only/auditable runtime history
- Containers; no Kubernetes v1
- Domain + Integration + Golden Simulation + AI/Assessment Evaluation

## 40. عمداً باز

در این مرحله هنوز نهایی نشده:
- Cloud Vendor
- Managed PostgreSQL Provider
- Managed vs Self-hosted Temporal
- S3 Vendor
- Observability Backend
- CDN / Edge Provider

این‌ها در Infrastructure Deployment Specification تصمیم‌گیری می‌شوند.

## تعریف نهایی

> **Parcham OS v1 یک Modular Monolith مبتنی بر Python/FastAPI و PostgreSQL است که Contextها را در سطح Domain و Data ownership جدا نگه می‌دارد، تغییرات بین Contextها را با Transactional Outbox و NATS منتقل می‌کند، Workflowهای طولانی را با Temporal هماهنگ می‌کند، Parcham AI اختصاصی را با Model/Training/Evaluation lineage کنترل‌شده اجرا می‌کند و تمام زنجیره Candidate Action تا Human Decision را Versioned، observable و auditable نگه می‌دارد.**