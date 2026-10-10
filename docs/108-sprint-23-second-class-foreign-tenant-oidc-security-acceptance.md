# 108 — Sprint 23 second-class / foreign-tenant OIDC security acceptance

**Scope:** isolated CI test fixture and E2E only. No new product feature or business rule.

One additional ACTIVE ClassOffering and current Session are created under the existing CI tenant/cohort. A separate Organization, Cohort and ACTIVE ClassOffering are inserted for a foreign-tenant denial check. The fixtures are exclusive to `backend/scripts/observation_ci_session.py`, not Production seed.

The real browser test signs in as an ASSESSOR and proves no automatic access to the second class. An actual Academy Admin cannot read or create a grant for the foreign-tenant class, but can create the second-class grant with two concurrent identical idempotent requests resulting in one assignment. The appointed Assessor reads only the second-class roster and records one factual Observation; a mismatched Session from the original class is rejected. The Admin revokes the grant, after which the same Assessor cannot read the second-class roster or private Observation. All checks use live Keycloak tokens and PostgreSQL.

No Evidence acceptance, model learning, Class completion/reappointment, Council administration, cross-tenant scope, Gate/Profile updates, Stage, release or Production action is performed. PR #21 stays Draft/Open/Unmerged.

## P23-12C — real concurrent and stale commands (2026-10-10)

The second-class Academy Admin races two **different-key, different-end-time** extension commands against grant version 1. PostgreSQL accepts exactly one (version 2); the other gets `409 GRANT_VERSION_CONFLICT`. A fresh-key stale extension and version-1 revoke also return 409. The accepted extension's exact replay reproduces historical version 2 even after the Admin's subsequent explicit version-2 revocation creates version 3; it does not revive permission, and the live Admin discovery still reports revoked version 3.

The second CI-only session receives simultaneous contradictory PRESENT and ABSENT commands with `expected_version=0`. One creates version 1, one fails with 409. An explicit corrected status creates version 2, while an obsolete version-1 command gets `409 ATTENDANCE_VERSION_CONFLICT`. Replaying the original accepted command returns its *historical* version-1 response rather than overwriting the current version-2 status. The Admin's authenticated attendance read verifies only one authoritative record at version 2.

No inferred attendance state, grading, ProofState, auto-Evidence or AI promotion is introduced. These are synthetic CI-only OIDC/PG acceptance tests, not Stage/Production.
