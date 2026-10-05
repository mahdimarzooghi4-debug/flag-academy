# 67 — Sprint 15: Deterministic Scope Change

**Status:** IN PROGRESS  
**Date:** 2026-10-05

## Goal

Close the next Mission Runtime action gap by making `CHANGE_SCOPE` executable through the exact pinned Mission Version while preserving deterministic state mutation, auditability, Candidate truth boundaries, and separation from Evidence/Profile/Gate semantics.

## Product boundary

`CHANGE_SCOPE` changes the bounded execution scope inside the simulated Mission world. It is not an implicit decision score, not Evidence, and not a Profile/Gate mutation.

A scope change does **not** transfer Mission accountability. If a Mission exposes scope change, `mission.accountability_owner` must remain `CANDIDATE`.

## Runtime contract

A Mission Version may expose bounded `scope_change_options`. Each option pins:

- `code`
- Candidate-visible `label`
- Engine response
- deterministic `world_effect`

The Candidate submits only:

- `scope_change_code`
- rationale
- expected world version
- idempotency key

Candidate cannot submit raw state patches, consequence rules, Evidence claims, capability scores, or Gate changes.

## Execution

1. Lock Mission Instance.
2. Enforce RUNNING status and world optimistic concurrency.
3. Resolve the scope option only from the pinned Mission Version.
4. Validate its world effect through the existing reserved-namespace guard.
5. Enforce `mission.accountability_owner=CANDIDATE` before and after the effect.
6. Persist CandidateAction.
7. Emit `scope_change.requested`.
8. Apply the Engine-owned world effect.
9. Increment world state version.
10. Emit `scope_change.accepted`.
11. Persist factual `SCOPE_CHANGE_OBSERVED`.
12. Run scheduled-effect cancellation.
13. Run state-triggered fixed-point evaluation.
14. Record internal `mission.scope_change_processed.v1`.

## Candidate truth boundary

Candidate may see:

- scope option code and label
- accepted response
- world version before/after
- candidate-visible World projection
- factual scope-change Observation

Candidate must not see:

- raw `world_effect`
- hidden World truth
- hidden trigger/cancellation rules
- Evidence/Profile/Gate mutations

## Acceptance scenario

The recovery Mission starts with:

- `mission.accountability_owner=CANDIDATE`
- `delivery.scope=FULL_ROLLOUT`
- `delivery.recovery_coordinator=CANDIDATE`

Candidate chooses the bounded scope option `CRITICAL_CUSTOMERS_ONLY`.

Expected deterministic result:

- `delivery.scope=CRITICAL_CUSTOMERS_ONLY`
- `mission.scope_change_status=ACTIVE`
- `mission.accountability_owner=CANDIDATE` remains unchanged
- world state version advances exactly once for the scope change
- `SCOPE_CHANGE_OBSERVED` is factual and Candidate-visible
- raw effect payload remains audit-only
- Proof remains `UNPROVEN`

## Out of scope

- ALLOCATE_RESOURCE
- RUN_EXPERIMENT
- Evidence Engine
- Profile/Gate updates
- LLM-authored scope effects
- arbitrary Candidate-authored world patches
