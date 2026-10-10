# 104 — Classroom Evidence formal-review fail-closed foundation

**2026-10-10 — Sprint 23 / Technical boundary, NOT an authorized Evidence decision.**

Source/Interpretation submitted is not accepted. The final Evidence reviewer appointment, issuance/revocation authority, evidence-specific scope, live authorization checks, and binding audit contract have **not** been approved in the repository. Academy ASSESSOR role, organization access, a past class mandate, source reviewer appointment, or case ownership may not authorize the final reviewer. No public final-review command is added.

This technical package adds:

1. SQL-level classroom Evidence state barrier: only private DRAFT v1 creation and DRAFT v1 → SUBMITTED v2 are permitted. Changing source/tenant/provenance/facts or making the case candidate-visible is denied, and UNDER_REVIEW / ACCEPTED / REJECTED are blocked at DB level until a newly reviewed migration replaces this barrier after human policy approval.
2. Classroom interpretation and target links cannot be UPDATEd or DELETEd in PostgreSQL; submitted human meaning stays auditable, with future interpretation supersession requiring an explicit versioning contract rather than silent mutation.
3. The normal Accepted Evidence reader filters classroom source context in SQL and again in-memory. It must not reach Pattern/Profile/Gate just because someone created an ACCEPTED row out of band.
4. A pure, explicitly **necessary but insufficient** lineage validator for future review checks cross-tenant identity, source/review digest, version, the source reviewer and interpretation creator relationship, reviewer independence from the original observer, human source reviewer, interpretation author and subject, plus immutable provenance. It is NOT an authorization predicate: passing it cannot open a review or decide ACCEPTED.
5. Backend regressions check identity separation, stale/tampered data, Accepted reader exclusion, SQL barrier presence and absence of any open classroom decision route.

**Policy dependency — OPEN:** the Academy / Evidence governance owner must explicitly approve Evidence-owned final reviewer mandate lifecycle, issuer, active/revoked checks, separation and accountability. Only then may a follow-up slice implement SUBMITTED → UNDER_REVIEW → ACCEPTED/REJECTED with exact-head PostgreSQL/OIDC concurrency, revocation and audit acceptance. No model/API, numeric threshold or reviewer entitlement is inferred. No external AI, no automatic Pattern/Profile/Gate transition and no Production promotion.

**Review status:** technical self-review of this safety foundation is not independent Human Code Review. PR #21 stays Draft/Open. Do not merge, run Stage/QA/Release/Production or claim business acceptance.
