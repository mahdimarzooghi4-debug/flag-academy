# Sprint 16 — Deterministic Resource Allocation Code Review

**Status:** PASS  
**Date:** 2026-10-05  
**PR:** #14 — Sprint 16: deterministic resource allocation  
**Reviewed implementation head:** `6dd2bf83cead01e5cee7ae30883fa9cb15dd52f0`  
**CI:** Run `37320739079` — SUCCESS

## Review scope

- pinned `resource_allocation_options`
- Candidate command boundary
- canonical resource-balance paths
- arithmetic conservation and scarcity
- World optimistic concurrency
- Engine-owned `resource_cost`
- Candidate leakage allowlists
- factual Observation boundary
- Candidate accountability invariant
- reserved Evidence/Profile/Gate namespaces
- scheduled-effect cancellation ordering
- state-trigger fixed-point evaluation
- real Candidate UI
- live OIDC E2E
- Stage SQL evidence

## Findings

### CR-16-001 — Canonical resource balances must be strict integers

**Severity:** Blocking before merge  
**Status:** RESOLVED

Python equality allows `True == 1`. The first hardening pass validated the declared arithmetic as strict integers, but canonical pre/post-condition comparison could still accept a boolean World State value as an integer balance.

Resolution:

- introduced `canonical_resource_balance_matches`
- both actual and expected balances must be integer and explicitly not boolean
- precondition and postcondition checks use the strict comparator
- unit tests cover valid integer, boolean rejection, and string rejection

This keeps resource accounting fail-closed.

### CR-16-002 — Resource arithmetic and over-allocation

**Status:** PASS

`resource_allocation_transition_valid` requires:

- positive integer quantity
- nonnegative before/after balances
- `to_available = from_available - quantity`
- `to_allocated = from_allocated + quantity`

Tests cover valid allocation, over-allocation/negative availability, resource creation mismatch and bool-as-int rejection.

### CR-16-003 — Candidate cannot author quantity or cost

**Status:** PASS

Candidate submits only `resource_allocation_code` and rationale. Quantity, canonical balances, paths and resource cost are resolved from the pinned Mission Version. The persisted CandidateAction `resource_cost` is overwritten with the Engine-pinned cost before commit.

### CR-16-004 — Candidate leakage boundary

**Status:** PASS

Candidate-visible option exposes bounded decision metadata only: code, label, resource type, unit, quantity and target.

Internal fields remain hidden:

- `available_path`
- `allocated_path`
- `resource_cost_applied`
- `world_effect_applied`

The accepted event and Observation expose factual balance changes without exposing internal mutation rules.

### CR-16-005 — Evidence/Profile/Gate isolation

**Status:** PASS

Resource allocation changes Canonical Simulation State and produces factual `RESOURCE_ALLOCATION_OBSERVED`. It does not create Accepted Evidence, change Proof, update Capability/Competency scores, decide a Gate, mutate Flag Profile, or assign Responsibility.

### CR-16-006 — Post-mutation ordering

**Status:** PASS

After accepted allocation, the runtime preserves the existing ordering:

1. scheduled-effect cancellation
2. state-triggered fixed-point evaluation

### CR-16-007 — Real workflow verification

**Status:** PASS

CI Run `37320739079` passed on reviewed head:

- backend lint — PASS
- backend type check — PASS
- backend unit tests — PASS
- migrations — PASS
- OpenAPI export — PASS
- frontend type check — PASS
- frontend unit tests — PASS
- frontend build — PASS
- live OIDC browser E2E — PASS

The browser path verifies:

- initial available engineering capacity = 3
- initial recovery allocation = 0
- Candidate submits bounded `ALLOCATE_RESOURCE`
- available capacity becomes 1
- recovery allocation becomes 2
- resource allocation status becomes ACTIVE
- Candidate accountability remains CANDIDATE
- `RESOURCE_ALLOCATION_OBSERVED` is visible
- internal paths/cost/effect payloads are hidden
- later DELEGATE / ESCALATE / DECIDE flow remains operational
- Candidate remains UNPROVEN

## Review conclusion

No blocking findings remain.

Sprint 16 implementation is approved for merge **only after** CI for the commit containing this review document is fully Green.
