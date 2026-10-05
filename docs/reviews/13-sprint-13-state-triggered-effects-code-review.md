# 13 — Sprint 13 State-triggered Scheduled Effects Code Review

**Status:** PASS — CODE REVIEW  
**Date:** 2026-10-05

## Reviewed vertical slice

**Canonical World Mutation → Deterministic Trigger Condition → ScheduledEffect APPLIED/CANCELLED → World Mutation → Runtime Event → Factual Observation**

Reviewed PR: **#10 — Sprint 13: deterministic state-triggered effects**

## Blocking findings

None after the fixes described below.

## Review findings

1. Every ScheduledEffect is DB-constrained to exactly one trigger source: `due_at XOR trigger_condition`.
2. `trigger_condition=None` is persisted as SQL NULL via `JSONB(none_as_null=True)`; JSON `null` cannot accidentally violate or bypass the XOR invariant.
3. Candidate has no API to author, mutate, force or directly execute a trigger condition.
4. Trigger conditions come only from the exact pinned Mission Version.
5. v1 accepts only bounded `WORLD_STATE_EQUALS` with an explicit path and literal equality target.
6. Arbitrary scripts, expression trees, external callbacks, probabilistic rules and LLM trigger decisions are out of scope.
7. Clock advancement reads only PENDING effects with non-null `due_at`.
8. NO_ACTION checks only timed consequences; state-triggered effects cannot satisfy a wait-window consequence requirement.
9. State-triggered effects are locked and selected in deterministic creation order.
10. A matching effect transitions from PENDING to APPLIED once; the fixed-point loop terminates because applied/cancelled effects are no longer eligible.
11. Cancellation is evaluated before state-trigger application after the causing World mutation, so an effect whose cancel condition becomes true cannot be applied afterward.
12. State-trigger application does not advance simulation time.
13. Internal `trigger_condition_matched` and `effect_applied` remain audit-only and are excluded from Candidate payloads.
14. Candidate sees only `trigger_mode`, effect identity/status, optional `due_at`, and factual observations.
15. State-triggered terminal `TIME_EXPIRED` remains rejected in v1; terminal timeout semantics remain timed-only.
16. `RECOVERY_COMMITMENT_BROADCAST` is a real dual-path acceptance consequence:
    - decision committed → APPLIED → `stakeholder.recovery_signal=BROADCAST`
    - decision expired → CANCELLED → `stakeholder.recovery_signal=NOT_BROADCAST`
17. Initial `recovery_signal=NOT_BROADCAST` is explicit in Canonical World State, avoiding an ambiguous missing-field state.
18. State-trigger execution produces no Evidence, Proof State, Competency, Gate or Flag Profile mutation.

## Findings discovered by CI and resolved

### Finding A — JSONB null versus SQL NULL

First E2E run failed during Escalation because Python `None` on PostgreSQL JSONB was serialized as JSON `null`. The DB constraint therefore saw `trigger_condition IS NOT NULL` for a timed effect and rejected the row.

Resolution:
- `trigger_condition` now uses `JSONB(none_as_null=True)`.
- absent trigger condition is persisted as SQL NULL.
- migration/seed/type/unit checks remain Green.

### Finding B — explicit baseline state

Second E2E run proved the timeout state-trigger effect was correctly CANCELLED, but `stakeholder.recovery_signal` was absent rather than explicitly `NOT_BROADCAST`.

Resolution:
- initial World State now contains `recovery_signal=NOT_BROADCAST`.
- success path changes it to `BROADCAST`.
- timeout path leaves it explicitly `NOT_BROADCAST`.

## Acceptance paths

### Success path

**Start → COMMUNICATE → ESCALATE → timed checkpoint → DECIDE(COMMITTED) → timed deadline CANCELLED → state-triggered broadcast APPLIED → COMPLETED**

Verified:
- `RECOVERY_COMMITMENT_BROADCAST = APPLIED`
- `trigger_mode = STATE_TRIGGERED`
- `recovery_signal = BROADCAST`
- internal trigger condition is hidden
- Candidate remains UNPROVEN

### Cost-of-delay path

**Start → ESCALATE → NO_ACTION → timed deadline APPLIED → decision EXPIRED → state-triggered broadcast CANCELLED → TIME_EXPIRED**

Verified:
- `RECOVERY_COMMITMENT_BROADCAST = CANCELLED`
- `recovery_signal = NOT_BROADCAST`
- no state-triggered effect remains PENDING on the terminal Mission
- Candidate remains UNPROVEN

## CI evidence

Reviewed implementation head before review-document commit: `dc67f0a39a1ca4b68ca9331cfa587a8d5dec488b`  
CI Run: `37300878701` — **SUCCESS**

Passed jobs:
- backend
- frontend
- Live OIDC E2E

Backend job includes:
- Ruff
- Pyright
- Pytest
- migration validation
- development seed
- OpenAPI export

Frontend job includes:
- generated API types
- TypeScript typecheck
- frontend unit tests
- production build

Live OIDC E2E verifies both APPLIED and CANCELLED state-trigger outcomes.

## Review result

> **PASS — eligible for merge after this review-document commit itself receives Green CI.**
