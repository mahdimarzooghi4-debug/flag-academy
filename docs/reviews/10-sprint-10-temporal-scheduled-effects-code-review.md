# 10 — Sprint 10 Temporal Scheduled Effects Code Review

**Status:** PASS — CODE REVIEW  
**Date:** 2026-10-05

## Reviewed vertical slice

**ESCALATE → transactional ScheduledEffect → Outbox → NATS → Temporal starter → Workflow timer → Activity → deterministic World Effect → Runtime Event → factual Observation**

Reviewed PR: **#6 — Sprint 10: Temporal scheduled effects**

## Blocking findings

None.

## Review findings and checks

1. ScheduledEffect is created in the same PostgreSQL transaction as the canonical ESCALATE result.
2. Delayed effects are read only from the exact pinned Mission Version; Candidate cannot submit arbitrary due_at or world_effect.
3. Scheduling leaves the command path through Transactional Outbox only after commit.
4. NATS starter uses a durable consumer and Inbox idempotency.
5. Temporal Workflow ID is deterministically derived from ScheduledEffect ID.
6. Temporal Workflow owns durable waiting; FastAPI contains no fixed sleep for consequence timing.
7. Temporal Activity locks ScheduledEffect and MissionInstance before applying state.
8. APPLIED and CANCELLED effects are idempotent terminal outcomes for the Activity.
9. If configured cancellation requires the Mission to remain RUNNING, terminal Missions cancel the pending delayed effect rather than mutating completed world state.
10. Delayed World mutation reuses `apply_world_effect`; Profile/Evidence/Competency/Gate namespaces remain forbidden.
11. World state version advances only when the delayed effect is actually applied.
12. `scheduled_effect.applied` retains internal `effect_applied` for audit but Candidate serialization excludes it.
13. Candidate result text is withheld until APPLIED, so future World truth is not leaked while PENDING/SCHEDULED.
14. `SCHEDULED_EFFECT_OBSERVED` is factual and performs no capability interpretation.
15. `WAITING_FOR_WORLD` is derived from persisted effect state rather than a client timer.
16. Backend blocks final DECIDE while a ScheduledEffect is PENDING/SCHEDULED; frontend mirrors the restriction but is not the authority.
17. Frontend semantic polling runs only while unresolved ScheduledEffects exist.
18. Standalone Temporal worker/scheduler load the complete SQLAlchemy model registry, including cross-domain FK metadata.
19. Temporal CI/Stage bootstrap uses the maintained Temporal CLI Development Server, which is appropriate only for ephemeral development/CI; production Temporal deployment remains a separate infrastructure concern.
20. This slice creates no direct Evidence, Proof State, Gate, Competency or Flag Profile write path.

## Failure-driven review history

### Finding A — invalid Temporal bootstrap image

Initial E2E failed before application startup because `temporalio/auto-setup:1.32.0` did not exist.

Resolution:
- replaced deprecated auto-setup usage with `temporalio/temporal:1.9.1`;
- Ephemeral CI/Stage uses `temporal server start-dev --ip 0.0.0.0`;
- documented that this is an ephemeral development/CI harness, not the production deployment model.

### Finding B — incomplete standalone SQLAlchemy registry

After Temporal startup succeeded, the Workflow reached Activity execution but the Activity failed with:

`NoReferencedTableError: mission_instances.mission_version_id → mission_design.mission_versions`

Root cause:
- standalone Temporal Activity process imported mission-runtime models but not the complete application model registry.

Resolution:
- Temporal Activity and scheduler import `app.models` for complete cross-domain metadata registration;
- regression test `test_temporal_activity_process_loads_cross_domain_model_registry` launches a fresh Python process and proves required tables are loaded.

## CI evidence

Reviewed implementation head: `497ec193d6568c581ec903f1a2d862289e843c87`  
CI Run: `37279444249` — **SUCCESS**

Passed:
- Temporal SDK installation
- Ruff
- Pyright
- Pytest, including standalone Temporal registry regression test
- Alembic migration `0011`
- development seed
- OpenAPI export
- generated frontend API types
- TypeScript typecheck
- frontend unit tests
- production frontend build
- Temporal development server startup
- PostgreSQL readiness
- Live Keycloak
- NATS Outbox + scheduler
- Temporal worker
- Live OIDC browser E2E

Live browser acceptance proves:
1. Mission starts in `RUNNING · ACTIVE`.
2. Candidate COMMUNICATEs with Business Sponsor.
3. Candidate ESCALATEs.
4. ScheduledEffect appears and Runtime enters `WAITING_FOR_WORLD`.
5. Scheduler moves effect through Temporal.
6. Temporal timer fires.
7. Activity applies the delayed consequence.
8. ScheduledEffect reaches `APPLIED`.
9. Runtime returns to `RUNNING · ACTIVE`.
10. Candidate-visible World State shows `checkpoint_status=ARRIVED`.
11. Candidate-visible World State shows `delayed_consequence_status=CHECKPOINT_READY`.
12. `SCHEDULED_EFFECT_OBSERVED` appears.
13. internal `effect_applied` remains hidden.
14. Candidate can then commit the final Decision.
15. Mission completes and Candidate remains UNPROVEN.

## Stage gate

Official Ephemeral Stage Acceptance is pending merge to `main`.

## Review result

> **PASS — eligible for merge after this review-document commit itself receives Green CI.**
