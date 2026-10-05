# 04 — Sprint 4 Mission Design Code Review

**Status:** PASS — SPRINT 4  
**Date:** 2026-10-05

## Reviewed vertical slice

**Academy Admin → Mission Template → Draft Version → Validate → Pilot → Validated → Active**

## Invariants verified

- Academy Studio requires contextual `ACADEMY_ADMIN`.
- Mission Template and Mission Version are separate.
- Mission references an exact `capability_version_id`.
- Mission definition owns no hidden correct-answer field.
- Actors, information access, constraints, decisions, consequences and evidence opportunities are structured data.
- Definition validation runs before lifecycle progression.
- Lifecycle skips are rejected.
- Lifecycle writes use optimistic `expected_version` checks.
- Activation produces an ACTIVE version without changing Candidate Profile or Evidence.
- Definition updates are version-oriented; no generic PATCH/direct-state endpoint was introduced.
- Mission Design emits transactional Domain Events through the Outbox.

## Gate results

- Backend lint/type/unit/migration/OpenAPI: PASS.
- Frontend generated contract/type/test/build: PASS.
- Live OIDC browser E2E: PASS.
- Ephemeral Stage: PASS.

Accepted implementation commit: `1fb9187a904fedf8d0d43853d3b67a9a9330c30f`.  
CI Run: `37260658807`.  
Stage Run: `37260658937`.
