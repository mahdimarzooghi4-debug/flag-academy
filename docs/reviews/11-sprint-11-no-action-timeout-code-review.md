# 11 — Sprint 11 Explicit NO_ACTION & Timeout Code Review

**Status:** PASS — CODE REVIEW  
**Date:** 2026-10-05

## Reviewed vertical slice

**Candidate NO_ACTION → Canonical Wait Policy → Simulation Time Advance → Due Effects → Recovery Deadline → TIME_EXPIRED → Factual Observation**

Reviewed PR: **#8 — Sprint 11: explicit no-action and timeout**

## Blocking findings

None.

## Review findings

1. `NO_ACTION` is persisted as a real CandidateAction and is not inferred from missing activity.
2. Candidate provides only `no_action_code` plus the standard Action `reasoning`; duration and consequences are never client-controlled.
3. `wait_seconds` is resolved from the exact pinned Mission Version.
4. The shared time engine is used by both next-event advance and NO_ACTION; there is no second competing clock implementation.
5. World optimistic concurrency remains enforced before NO_ACTION execution.
6. CandidateAction idempotency is checked before simulation time or World State mutation.
7. All due ScheduledEffects through the canonical target time are locked and applied in deterministic due-time/id order.
8. Scheduled terminal status is persisted explicitly via migration `0012`; v1 accepts only `TIME_EXPIRED`.
9. TIME_EXPIRED is reached only through an Engine-owned ScheduledEffect, not a client status mutation.
10. Deadline World mutation, ScheduledEffect APPLIED status and Mission terminal transition occur in the same transaction.
11. Mission/Assignment operational `completed_at` uses wall-clock `now`; simulated deadline remains in `simulation_time` / `expired_at`, preventing clock-domain confusion.
12. `NO_ACTION_OBSERVED` and `MISSION_TIME_EXPIRED` contain factual timing/version data and no capability judgment.
13. Candidate-visible event/observation allowlists remain fail-closed.
14. Profile/Evidence/Competency/Gate namespaces remain protected by the existing World mutation invariant.
15. TIME_EXPIRED does not create Evidence, Proof or Candidate Failure.

## Dual-path acceptance

### Success regression
**Start → COMMUNICATE → ESCALATE → Executive Checkpoint → Information Request → DECIDE → COMPLETED**

### Cost-of-delay path
**Start → ESCALATE → NO_ACTION WAIT_30_MINUTES → Checkpoint Due → Recovery Deadline → TIME_EXPIRED**

The second path proves:
- `risk.level = CRITICAL`
- `mission.decision_status = EXPIRED`
- `mission.escalation_status = DEADLINE_MISSED`
- Assignment = COMPLETED
- Candidate = UNPROVEN

## CI evidence

Reviewed head: `54d7740271d988381fdbbdf59b1aa4c8bf827e72`  
CI Run: `37292733375` — **SUCCESS**

Passed:
- Ruff
- Pyright
- Pytest
- Alembic validation through `0012`
- development seed
- OpenAPI export
- generated frontend API types
- TypeScript typecheck
- frontend unit tests
- production frontend build
- Live OIDC browser E2E

## Non-blocking residual gap

A Mission that completes before a later deadline may retain a PENDING ScheduledEffect row. Runtime commands already reject non-RUNNING Mission instances, so that effect cannot mutate a completed Mission through current APIs.

However, audit hygiene should explicitly close/cancel unreachable pending effects when a Mission enters a terminal state.

Recommended next gap:

> **ScheduledEffect cancellation / terminal cleanup**

This is intentionally not hidden or treated as completed work.

## Stage gate

Official Ephemeral Stage Acceptance is pending merge to `main`.

## Review result

> **PASS — eligible for merge after this review-document commit itself receives Green CI.**
