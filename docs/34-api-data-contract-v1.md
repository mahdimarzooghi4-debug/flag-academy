# 34 — API & Data Contract Specification v1

**وضعیت:** FINAL  
**تاریخ تثبیت:** 2026-10-04

## اصول

> **API قرارداد Business است، نه انعکاس مستقیم جدول‌های Database.**

> **هیچ Clientی حق ندارد State Domain را با ارسال فیلدهای دلخواه تغییر دهد؛ Client فقط Intent را ارسال می‌کند.**

Namespace عمومی API:
`/api/v1/...`

v1 نسخه Public HTTP Contract است، نه نسخه Domain Entity.

## 1. Command vs Query

Query می‌پرسد چه چیزی اکنون درست است؛ Command بیان می‌کند چه کاری باید انجام شود.

Direct state patchهایی مانند تغییر مستقیم level/profile ممنوع هستند.

## 2. Common Command Contract

Headerهای حساس:
- Authorization
- Idempotency-Key
- If-Match / expected_version
- X-Correlation-Id (optional)

Backend trace_id تولید می‌کند.

Request body فقط Business Payload را حمل می‌کند.

## 3. Response & Error

Resource response بدون envelope غیرضروری success/data برگردانده می‌شود.

Error contract استاندارد:
- code
- message
- details
- trace_id
- retryable

Client نباید Logic را از متن message استخراج کند.

## 4. HTTP Semantics

- 200: success with body
- 201: resource/case created
- 202: accepted, async processing pending
- 204: success no body
- 400: invalid contract/request
- 401: unauthenticated
- 403: authenticated but forbidden
- 404: not found / optionally hidden for security
- 409: business/version/idempotency conflict
- 412: precondition failure
- 422: domain-invalid input
- 429: rate limit
- 503: temporary dependency failure

## 5. Pagination / Sort / Filter

Mutable/audit-heavy collections از Cursor Pagination استفاده می‌کنند:
`?limit=50&cursor=...`

Response:
- items
- next_cursor
- has_more

Filter و Sort explicit و محدود هستند؛ query DSL آزاد در v1 نداریم.

## 6. Date, Enum, Money, IDs

- Timestamp: ISO-8601 UTC
- DB timestamp: TIMESTAMPTZ
- Business date: YYYY-MM-DD
- Enumها string-based
- Money: Decimal as string + currency
- Entity ID: UUID string
- Business code جدا از ID

## 7. Aggregate Versioning

Aggregateهای mutable دارای version هستند.

REST mutation عمومی از ETag / If-Match استفاده می‌کند.

Mission Runtime علاوه بر آن world_state_version را به‌عنوان Business Version نگه می‌دارد.

## 8. Idempotency

Commandهای create/decision/action حساس نیازمند Idempotency-Key هستند.

Backend حداقل نگه می‌دارد:
- key
- actor
- route
- request_hash
- response_status
- response_body_hash/ref
- created_at

تکرار همان Key با Payload متفاوت:
`409 IDEMPOTENCY_CONFLICT`

## 9. Candidate APIs

`GET /api/v1/me/candidate-home`

Read model شامل Journey، Current Wave، Next Experience، Open Missions، Profile Summary، Gate Summary، Open Behaviour Commitments و Processing States است.

## 10. Flag Profile APIs

`GET /api/v1/people/{person_id}/flag-profile`

Permission-sensitive و بدون Score کلی.

Claimها State، Level، Proven Scope، Evidence Recency و Next Evidence Needed را برمی‌گردانند.

Lineage:
`GET /api/v1/profile/claims/{claim_id}/lineage`

مسیر Claim → Pattern → Evidence → Interpretation → Observation → Source را برمی‌گرداند.

## 11. Curriculum & Capability APIs

Read:
- GET /api/v1/curricula/{id}
- GET /api/v1/capabilities
- GET /api/v1/capabilities/{id}

Studio:
- POST /api/v1/studio/capabilities
- POST /api/v1/studio/capabilities/{id}/versions
- POST /api/v1/studio/capability-versions/{version_id}/activate

Active Version مستقیم patch نمی‌شود؛ تغییر = version جدید.

## 12. Mission Design APIs

- POST /api/v1/studio/mission-templates
- POST /api/v1/studio/mission-templates/{id}/versions
- POST /api/v1/studio/mission-template-versions/{id}/validate
- POST /api/v1/studio/mission-template-versions/{id}/pilot
- POST /api/v1/studio/mission-template-versions/{id}/activate
- POST /api/v1/studio/mission-template-versions/{id}/retire

## 13. Mission Assignment & Runtime

`POST /api/v1/mission-assignments`

Mission Runtime:
- POST /api/v1/missions/{id}/start
- GET /api/v1/missions/{id}/workspace
- POST /api/v1/missions/{id}/actions
- POST /api/v1/missions/{id}/decisions
- POST /api/v1/missions/{id}/complete

Mission Workspace فقط Candidate-visible truth را برمی‌گرداند و Hidden World Truth هرگز expose نمی‌شود.

Decision Record شامل Question، Options، Evidence refs، Assumptions، Decision، Reasoning، Confidence، Expected Outcome، Revisit Trigger، Reversibility و world_state_version است و پیش از Outcome freeze می‌شود.

Mission completion ممکن است 202 PROCESSING_RESULTS برگرداند و Evidence pipeline async ادامه یابد.

## 14. Realtime

SSE endpoint:
`GET /api/v1/events/stream`

Browser UI Event Contract دریافت می‌کند، نه Domain Event داخلی.

## 15. Observation APIs

- GET /api/v1/observations/{id}
- POST /api/v1/observations (برای Manual Assessor Observation در صورت مجاز بودن)
- POST /api/v1/observations/{id}/seal

Observation پس از Seal editable نیست.

## 16. Evidence Case APIs

- GET /api/v1/evidence-cases/{id}
- POST /api/v1/evidence-cases/{id}/submit
- POST /api/v1/evidence-cases/{id}/reviews
- POST /api/v1/evidence-cases/{id}/accept
- POST /api/v1/evidence-cases/{id}/reject
- POST /api/v1/evidence-cases/{id}/request-context
- POST /api/v1/evidence-cases/{id}/candidate-response

Candidate Response Context اضافه می‌کند و Evidence را بازنویسی نمی‌کند.

## 17. Independent Review & Calibration

Review assignment:
`POST /api/v1/review-cases/{id}/assignments`

Review package:
`GET /api/v1/review-cases/{id}/review-package`

تا قبل از Submit، نظر Reviewerهای دیگر در پاسخ وجود ندارد.

Submit:
`POST /api/v1/review-cases/{id}/independent-reviews`

Calibration:
- POST /api/v1/calibration-cases
- GET /api/v1/calibration-cases/{id}
- POST /api/v1/calibration-cases/{id}/resolve

Resolutionها:
- ACCEPT_INTERPRETATION_A
- ACCEPT_INTERPRETATION_B
- NEW_INTERPRETATION
- INSUFFICIENT_CONTEXT
- REQUIRE_REPLAY

## 18. Profile Update APIs

- GET /api/v1/profile-update-cases/{id}
- POST /api/v1/profile-update-cases/{id}/approve
- POST /api/v1/profile-update-cases/{id}/reject

Direct PATCH روی Flag Profile وجود ندارد.

## 19. Gate APIs

- GET /api/v1/gate-assessments/{id}
- POST /api/v1/gate-assessments/{id}/open-review
- POST /api/v1/gate-assessments/{id}/decisions
- POST /api/v1/gate-assessments/{id}/start-remediation
- POST /api/v1/gate-assessments/{id}/reassess

AI/System endpoint مستقیم برای fail کردن Gate ندارد.

## 20. Reflection APIs

- POST /api/v1/learning-records
- POST /api/v1/learning-records/{id}/commit
- GET /api/v1/learning-records/{id}

Learning Record شامل Situation، Expected، Actual، Evidence refs، My Contribution، Assumption Challenged، Learning Claim و Behaviour Commitment است.

## 21. Real Project APIs

- POST /api/v1/real-project-engagements
- POST /api/v1/real-project-engagements/{id}/approve
- POST /api/v1/real-project-engagements/{id}/start
- POST /api/v1/real-project-engagements/{id}/complete
- GET /api/v1/real-project-engagements/{id}/workspace

شروع بدون Learning & Evidence Contract:
`422 EVIDENCE_CONTRACT_REQUIRED`

## 22. Responsibility APIs

Responsibility definitions versioned هستند.

Assessment:
`POST /api/v1/responsibility-assessments`

Output:
- READY
- READY_WITH_CONDITIONS
- DIFFERENT_SCOPE
- NOT_YET
- BLOCKED_BY_GATE

همراه rationale.

## 23. Flag Board APIs

- POST /api/v1/flag-board-cases
- POST /api/v1/flag-board-cases/{id}/freeze-evidence
- GET /api/v1/flag-board-cases/{id}
- POST /api/v1/flag-board-cases/{id}/reviews
- POST /api/v1/flag-board-cases/{id}/resolve-conflicts
- POST /api/v1/flag-board-cases/{id}/decision

Evidence Set پس از Board Decision تغییر نمی‌کند.

## 24. Appointment API

`POST /api/v1/appointments`

Appointment از Flag Board جداست.

اگر Human Decision خلاف Recommendation باشد، override_reason الزامی است.

## 25. Audit APIs

Authorized Governance users:
`GET /api/v1/audit/events`

Audit API read-only است.

## 26. AI Invocation Boundary

Frontend هیچ Domain Decisionی را مستقیماً از endpoint provider AI نمی‌گیرد.

AI از Internal Gateway Contract و Application Service عبور می‌کند.

Browser هیچ Provider credential ندارد.

## 27. PostgreSQL Schema Convention

Naming:
**snake_case + plural tables**

نمونه:
- mission_runtime.mission_instances
- mission_runtime.events
- mission_runtime.world_state_snapshots
- evidence.evidence_cases
- evidence.evidence_interpretations
- profile.flag_profiles
- governance.review_cases
- platform.outbox_events
- platform.inbox_events
- readmodel.candidate_home

## 28. Common DB Columns

Aggregate tables عموماً:
- id UUID PK
- version BIGINT NOT NULL
- created_at TIMESTAMPTZ
- updated_at TIMESTAMPTZ

Organization-aware tables:
- organization_context_id UUID

Versioned definitions:
- definition_id
- version_number
- status
- effective_from

## 29. JSONB Policy

JSONB فقط برای داده extensible و schema-validated مانند World State استفاده می‌شود.

> **Flexible data can be JSONB; important business state should remain queryable and constrained.**

Gate State، Evidence Review State و Capability Claim نباید فقط داخل JSONB دفن شوند.

## 30. Domain Event Store

`platform.domain_events` حداقل شامل:
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

## 31. Outbox / Inbox

`platform.outbox_events` علاوه بر Envelope شامل published_at، attempt_count و last_error است.

Worker فقط Eventهای Commit‌شده را publish می‌کند.

`platform.inbox_events` با unique constraint روی consumer_name + event_id deduplication انجام می‌دهد.

## 32. Event Schema Registry

Event Contractها Versioned و در Repository نگه‌داری می‌شوند.

Breaking change نیازمند Event Type جدید یا Version جدید است.

Core eventهای v1:
- candidate.admitted.v1
- mission.assigned.v1
- mission.started.v1
- mission.action_recorded.v1
- mission.completed.v1
- observation.sealed.v1
- evidence.accepted.v1
- evidence.rejected.v1
- pattern.updated.v1
- profile.claim_changed.v1
- gate.at_risk.v1
- gate.review_completed.v1
- learning.behaviour_commitment_created.v1
- replay.required.v1
- profile.snapshot_created.v1
- responsibility.assessed.v1
- flag_board.decided.v1
- appointment.recorded.v1

Event payload Aggregate Dump نیست؛ فقط Fact موردنیاز را حمل می‌کند.

## 33. PII in Events

Event Backbone به‌صورت پیش‌فرض ID حمل می‌کند، نه نام/ایمیل.

Data Classification در Envelope وجود دارد و RESTRICTED eventها Consumer allowlist دارند.

## 34. Authorization Context

Token هویت و Roleهای پایه را می‌دهد؛ Contextual authorization از Domain Policy می‌آید.

Assignment، Organization Context، Data Classification و Conflict-of-interest باید در Policy بررسی شوند.

## 35. OpenAPI

FastAPI OpenAPI یک CI artifact رسمی است.

CI باید Contract break، client regeneration و accidental breaking change را بررسی کند.

Deprecation باید در OpenAPI مشخص، replacement روشن و removal فقط در Major Contract change باشد.

## 36. File Upload & Artifact Contract

File upload flow:
1. Create Upload Session
2. Signed Upload URL
3. Direct upload to Object Storage
4. CompleteArtifactUpload
5. Validate hash/metadata

Artifact:
- artifact_id
- object_key
- content_type
- size
- content_hash
- classification
- created_by
- source_context
- version

Artifact تاریخی overwrite نمی‌شود؛ Version جدید ساخته می‌شود.

## 37. Async Processing State

Async flows باید State واضح داشته باشند:
- PENDING
- PROCESSING
- REVIEW_REQUIRED
- COMPLETE
- FAILED

Frontend نباید وضعیت را حدس بزند.

## 38. Retry Semantics

Client فقط retryable=true را خودکار Retry می‌کند و فقط برای Commandهای idempotent.

409 VERSION_CONFLICT نیازمند Refresh State است و نباید Blind Retry شود.

## 39. Retention / Rate Limits

داده‌ها باید classification و در صورت نیاز retention_policy_ref داشته باشند.

Rate limiting context-sensitive است و 429 یا network retry نباید به Assessment Evidence تبدیل شود.

## 40. External Connector Contract

Connectorها مستقیم Domain Table را Update نمی‌کنند.

Flow:
**Connector → ExternalSourceEvent → Validation → Domain Command / Observation**

ExternalSourceEvent حداقل source_system، external_event_id، received_at، payload_hash، classification و raw_payload_ref دارد.

Deduplication:
source_system + external_event_id

## 41. Contract Testing

سه Layer:
- Schema Contract Test
- Consumer Contract Test
- Domain Contract Test

Contract Tests باید Invariantهایی مانند no AI gate-fail، stale world-state rejection و no Board decision before Evidence Freeze را enforce کنند.

## 42. Contract Invariants

1. هیچ Profile direct-update endpoint وجود ندارد.
2. هیچ Gate direct-fail endpoint برای AI/System وجود ندارد.
3. Mission Workspace Hidden World Truth را expose نمی‌کند.
4. Decision reasoning قبل از Outcome freeze می‌شود.
5. Sealed Observation قابل Edit نیست.
6. Candidate Response Evidence را بازنویسی نمی‌کند.
7. Independent Reviewer قبل از Submit نظر دیگران را نمی‌بیند.
8. Flag Board بدون Evidence Freeze تصمیم نمی‌دهد.
9. Appointment از Flag Board جداست.
10. Eventها Aggregate Dump نیستند.
11. Cross-context write فقط از Contract/Event انجام می‌شود.
12. تصمیم‌های consequential دارای version، lineage، trace و accountable actor هستند.

## 43. Definition of Ready for Backlog

با تثبیت این Contract Specification، مسیر مادر توسعه وارد Product Backlog می‌شود:

**Business ✅ → Technical ✅ → Scrum/Product Backlog → Sprint → Code → Code Review → Stage → QA/Testing → Release Approval → Production → Monitoring → Improvement**

Epics اولیه:
- Foundation Platform
- Identity/Auth
- Curriculum Registry
- Candidate Journey
- Mission Design
- Mission Runtime
- Observation/Evidence
- Flag Profile
- Human Review
- Responsibility/Flag Board
- Parcham AI
- Reflection/Orchestrator

## تعریف نهایی

> **API & Data Contract v1 پرچم، مرز قابل کدنویسی میان Client، Domainها و Event Backbone است: Client فقط Intent ارسال می‌کند، Domain صاحب State است، تغییرات با Version و Idempotency محافظت می‌شوند، Contextها از Contract/Event ارتباط می‌گیرند و هیچ تصمیم consequential بدون Lineage، Audit و Human Accountability قابل اعمال نیست.**