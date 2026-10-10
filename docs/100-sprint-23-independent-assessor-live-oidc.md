# 100 — Real OIDC independent Assessor and PostgreSQL source review acceptance

**Date:** 2026-10-09

This CI-only package adds a *second* temporary Keycloak assessor identity to the already isolated GitHub Actions environment, with a matching temporary Identity membership in the seeded PostgreSQL database. It is NOT a Production or real Academy user, and no source is approved outside CI.

The existing chromium scenario must prove: creator Assessor cannot self-review, independent Assessor is denied prior to a class-specific Admin appointment; same reviewer is allowed to read exactly the recorded source after appointment and sees its SHA-256; parallel POSTs create one VERIFIED review; replay returns the same review; stale digest and changed decision fail 409; Admin revocation instantly closes the reviewer read access. The original Observation's P23-09C tests continue independently.

The PostgreSQL verification after browser E2E asserts exactly one reviewed source decision, one domain event and outbox message, no raw notes/review rationale in either event, zero automatic EvidenceCase records and actual privileged UPDATE/DELETE rejection by immutable DB triggers on **both** source and review.

This is not evidence of a real operational human review nor a formal Evidence ACCEPT decision. In particular the Evidence listing and case APIs currently have different permissions from the Academy classroom scope. Explicit Evidence Draft ingestion remains blocked until that broader Evidence read/write boundary is made classroom-aware, tested and approved.
