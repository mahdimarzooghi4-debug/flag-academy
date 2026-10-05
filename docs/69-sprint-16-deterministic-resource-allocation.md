# 69 — Sprint 16: Deterministic Resource Allocation

**Status:** IN PROGRESS  
**Date:** 2026-10-05

## Goal

Close the next Mission Runtime action gap by making `ALLOCATE_RESOURCE` executable as a bounded, Mission-Version-pinned resource commitment with deterministic scarcity accounting.

## Product boundary

Resource allocation changes Canonical Simulation State and consumes a limited Mission resource. It is not Evidence, Proof, a hidden score, or a Profile/Gate mutation.

**Resource Allocation ≠ Evidence**  
**Resource Allocation ≠ Proven Capability**  
**Resource Allocation ≠ Profile/Gate mutation**

Priority becomes meaningful only when it is connected to real resource commitment. Candidate may choose among bounded allocation options, but cannot author arbitrary quantities or state patches.

## Runtime contract

A Mission Version may expose `resource_allocation_options`. Each option pins:

- `code`
- Candidate-visible `label`
- Candidate-visible `resource_type`
- Candidate-visible `unit`
- Candidate-visible positive integer `quantity`
- Candidate-visible `target`
- internal `available_path`
- internal `allocated_path`
- canonical `from_available` / `to_available`
- canonical `from_allocated` / `to_allocated`
- Engine-owned `resource_cost`
- Engine response
- deterministic `world_effect`

Candidate submits only:

- `resource_allocation_code`
- rationale
- expected World State version
- idempotency key

Candidate cannot submit quantity, resource balance, resource cost, world patch, Evidence claim, or Gate mutation.

## Arithmetic invariant

For every accepted allocation:

- `quantity > 0`
- `to_available = from_available - quantity`
- `to_allocated = from_allocated + quantity`
- `to_available >= 0`
- current canonical values must match both `from_*` values
- post-effect canonical values must match both `to_*` values

This prevents over-allocation, resource creation, resource destruction, and no-op allocation.

## Execution

1. Lock Mission Instance.
2. Enforce RUNNING and World optimistic concurrency.
3. Resolve allocation only from exact pinned Mission Version.
4. Validate option schema and arithmetic invariant.
5. Verify canonical current availability/allocation preconditions.
6. Apply Engine-owned world effect through reserved namespace guard.
7. Verify canonical postconditions and Candidate accountability invariant.
8. Replace Candidate-supplied `resource_cost` with the pinned Engine-owned cost.
9. Emit `resource_allocation.requested`.
10. Emit `resource_allocation.accepted`.
11. Persist factual `RESOURCE_ALLOCATION_OBSERVED`.
12. Run scheduled-effect cancellation.
13. Run state-triggered fixed-point evaluation.
14. Record internal `mission.resource_allocation_processed.v1`.

## Acceptance scenario

Initial Candidate-visible World State:

- `resources.engineering_capacity.available_units=3`
- `delivery.recovery_capacity_units=0`
- `mission.resource_allocation_status=NOT_ALLOCATED`
- `mission.accountability_owner=CANDIDATE`

Candidate chooses a bounded option to allocate two engineering-capacity units to recovery.

Expected deterministic result:

- available engineering capacity: `3 → 1`
- recovery allocation: `0 → 2`
- resource allocation status: `ACTIVE`
- Candidate accountability remains `CANDIDATE`
- CandidateAction stores Engine-pinned resource cost `{"engineering_capacity_units": 2}`
- factual `RESOURCE_ALLOCATION_OBSERVED`
- internal canonical paths and raw world effect remain hidden
- later Mission actions remain operational
- Proof remains `UNPROVEN`

## Out of scope

- RUN_EXPERIMENT
- Evidence Engine
- Profile/Gate updates
- arbitrary Candidate-authored quantities
- arbitrary Candidate-authored resource cost
- probabilistic allocation
- LLM-authored resource effects
