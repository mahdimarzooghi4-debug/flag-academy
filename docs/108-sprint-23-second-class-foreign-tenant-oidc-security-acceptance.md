# 108 — Sprint 23 second-class / foreign-tenant OIDC security acceptance

**Scope:** isolated CI test fixture and E2E only. No new product feature or business rule.

One additional ACTIVE ClassOffering and current Session are created under the existing CI tenant/cohort. A separate Organization, Cohort and ACTIVE ClassOffering are inserted for a foreign-tenant denial check. The fixtures are exclusive to `backend/scripts/observation_ci_session.py`, not Production seed.

The real browser test signs in as an ASSESSOR and proves no automatic access to the second class. An actual Academy Admin cannot read or create a grant for the foreign-tenant class, but can create the second-class grant with two concurrent identical idempotent requests resulting in one assignment. The appointed Assessor reads only the second-class roster and records one factual Observation; a mismatched Session from the original class is rejected. The Admin revokes the grant, after which the same Assessor cannot read the second-class roster or private Observation. All checks use live Keycloak tokens and PostgreSQL.

No Evidence acceptance, model learning, Class completion/reappointment, Council administration, cross-tenant scope, Gate/Profile updates, Stage, release or Production action is performed. PR #21 stays Draft/Open/Unmerged.
