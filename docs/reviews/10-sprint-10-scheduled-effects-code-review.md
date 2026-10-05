# 10 — Sprint 10 Scheduled Effects & Simulation Clock Code Review

**Status:** PASS — CODE REVIEW  
**Date:** 2026-10-05

## Reviewed vertical slice

**Immediate Action → ScheduledEffect → Simulation Clock Advance → Due Effect → World State Transition → Factual Observation**

Reviewed PR: **#7 — Sprint 10: scheduled effects and simulation clock**

## Blocking findings

None.

## Review findings

1. `due_at` and delayed effect payload come only from the exact pinned Mission Version.
2. Candidate cannot submit arbitrary simulation time or delayed effect data.
3. `advance-to-next-event` selects the earliest PENDING ScheduledEffect and advances only to that canonical due time.
4. MissionInstance is locked before clock/world mutation; stale `expected_world_version` returns 409.
5. Command idempotency is anchored on an instance-scoped RuntimeEvent key before mutation.
6. All effects due at the selected timestamp are applied in deterministic order.
7. Each applied World mutation increments `world_state_version`.
8. ScheduledEffect status transition PENDING → APPLIED occurs in the same DB transaction as World mutation.
9. Causality links applied events to both the origin event and the time-advance event.
10. Internal `effect_applied` remains stored for audit but is excluded from Candidate payload allowlists.
11. INTERNAL ScheduledEffects do not create Candidate-visible observations.
12. Candidate-visible ScheduledEffects expose only id/code/label/due/status.
13. Reserved Profile/Evidence/Competency/Gate namespaces are still rejected through `apply_world_effect`.
14. `SCHEDULED_EFFECT_OBSERVED` is factual and carries no judgment.
15. ScheduledEffect execution does not mutate Evidence, Proof State, Gate, Competency or Flag Profile.

## Acceptance timeline

- World v1: Mission starts.
- COMMUNICATE: Actor v1→v2.
- ESCALATE: World v1→v2, Actor v2→v3.
- `EXECUTIVE_CHECKPOINT_DUE` created as PENDING.
- Candidate-visible checkpoint remains `NOT_SCHEDULED`.
- Engine advances simulation clock exactly to the next due event.
- Scheduled effect applies: World v2→v3.
- Candidate-visible checkpoint becomes `DUE`.
- `SCHEDULED_EFFECT_OBSERVED` is recorded.
- Decision advances World v3→v4 and completes the Mission.
- Candidate remains UNPROVEN.

## CI evidence

Reviewed implementation head: `95d3fb1614f063222cf97dfa305a5ecc27232dd7`  
CI Run: `37281067862` — **SUCCESS**

Passed:
- Ruff
- Pyright
- Pytest
- migration validation through `0011`
- development seed
- OpenAPI export
- generated frontend API types
- TypeScript typecheck
- frontend unit tests
- frontend build
- Live OIDC browser E2E

## Review result

> **PASS — eligible for merge after this review-document commit itself receives Green CI.**
