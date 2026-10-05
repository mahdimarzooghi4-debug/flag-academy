# 05 — Sprint 5 Mission Runtime Code Review

**Status:** PASS — CODE REVIEW  
**Date:** 2026-10-05

## Reviewed vertical slice

**Active Mission Version → Mission Instance → Candidate Information Request → Candidate Decision → Deterministic Consequence → World State Transition → Observation → Replayable Audit**

Reviewed PR: **#1 — Sprint 5: deterministic Mission Runtime v1**

## Blocking findings

None.

## Invariants verified

- Runtime starts only from an ACTIVE Mission Version in the same organization context.
- Mission Instance is pinned to the exact mission_version_id.
- Candidate access is scoped by contextual CANDIDATE role, organization context and instance ownership.
- Runtime lifecycle is explicit and skips are rejected by the domain transition map.
- simulation_seed is persisted on the Mission Instance.
- Candidate Action has an idempotency key with a database uniqueness constraint.
- State-changing actions lock the Mission Instance row and require expected_world_version.
- stale actions return WORLD_STATE_VERSION_CONFLICT instead of silently overwriting state.
- World mutation is deterministic and comes only from machine-readable decision_effects in the Mission Version.
- reserved world namespaces profile, evidence, competency and gate cannot be mutated by Runtime effects.
- Mission Runtime imports no Flag Profile / Evidence write model and exposes no endpoint that marks capability as Proven.
- Decision Record is frozen as a separate immutable audit record.
- Runtime Events are ordered per Mission Instance and append-only from the exposed API surface.
- Observations are factual statements tied to exact Runtime Events; they are not Accepted Evidence.
- Information disclosure returns canonical content already stored in Mission Design; Runtime does not ask an LLM to invent canonical facts.
- core Runtime correctness has no LLM dependency.
- Candidate UI explicitly states that Observation is not Evidence/Profile change.
- Live browser acceptance verifies UNPROVEN remains visible after mission completion.

## v1 scope reviewed

Executable end-to-end:
- REQUEST_INFORMATION
- DECIDE

Contract-visible but intentionally non-executable in this vertical slice:
- COMMUNICATE
- ESCALATE
- DELEGATE
- CHANGE_SCOPE
- ALLOCATE_RESOURCE
- RUN_EXPERIMENT
- NO_ACTION

This is a scoped Sprint boundary, not a relaxation of the FINAL Mission Runtime contract.

## CI evidence

PR head reviewed: 471a48bd0ce281cc0ca908b053af2f126c204dae  
CI Run: 37262957218 — **SUCCESS**

Passed:
- Ruff
- Pyright
- Pytest
- Alembic upgrade
- Development seed
- OpenAPI export
- generated frontend API contract
- TypeScript typecheck
- frontend unit tests
- production frontend build
- Live OIDC browser E2E

## Stage gate

Stage is intentionally **PENDING** at Code Review time because the project process requires merge to main before official Ephemeral Stage Acceptance.

## Review result

**PASS — eligible for merge after the new documentation commit itself receives Green CI.**
