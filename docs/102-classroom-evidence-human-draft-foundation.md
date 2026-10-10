# 102 — Explicit private Classroom Evidence Draft admission foundation

**Date:** 2026-10-10  
**Scope:** Evidence-owned Draft only, no submission or formal decision.

**POST** `/api/v1/classroom-observations/{observation_id}/evidence-draft`: only the exact independent human reviewer of a VERIFIED classroom source can request a Draft. They must still hold the same LIVE Academy class grant and organization ASSESSOR membership. Client supplies the expected immutable review ID, SHA-256 of source content, and a nonblank explicit submission reason. Source + current grant are locked in a single transaction to serialize requests and revocation. Reviewer identity, same-class original observer/learner/session, reviewed digest, reviewer grant and source version are re-attested.

A single EvidenceCase is created as `DRAFT` with `integrity_state=SOURCE_REVIEWED` and `candidate_visible=false`. Source, reviewer/subject/class/session, SHA-256, human reason, and both grant IDs/versions are preserved as versioned provenance, but private reason and factual content never enter the event/outbox payload. Source uniqueness ensures idempotent identical replay and fail-closed conflicting replay. `source_independence_group` groups the class; it never asserts evidence independence or accepted capability.

**GET** `/api/v1/classroom-evidence-drafts/{case_id}` is deliberately narrow: ONLY the exact creator/reviewer holding a CURRENT eligible class appointment can read the private Draft, and all source and reviewer attestation is rechecked. Guessed IDs, cross-tenant access, revoked appointments, changed source, rejected source and stale review fail closed. Legacy org-wide Assessor/Candidate Evidence APIs continue to exclude all `CLASSROOM_OBSERVATION` cases.

The legacy `observation.sealed.v1` consumer explicitly ignores `CLASSROOM_OBSERVATION` payloads; no system event may bypass human Draft initiation. No independent Evidence interpretation or submission/decision command is exposed for classroom cases yet. Formal Evidence review, CapabilityClaim, Gate, Profile and AI governance remain unchanged. This is the *foundation*, not completion of P23-09C. Dedicated OIDC/PostgreSQL API acceptance, private Draft authorization regression, and independent human Code Review are required before final acceptance. PR #21 remains Draft/Open; no Stage or Release.
