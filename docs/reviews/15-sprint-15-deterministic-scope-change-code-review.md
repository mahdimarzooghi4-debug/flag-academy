# Sprint 15 — Deterministic Scope Change Code Review

**Status:** PASS  
**Date:** 2026-10-05  
**PR:** #13 — Sprint 15: deterministic scope change  
**Reviewed implementation head:** `ae60ce14f806657a148a8600f7e150e19a047153`  
**Baseline CI:** Run `37314778713` on pre-hardening head `d8624be...` — SUCCESS  
**Final-head CI:** required after this review commit

## Review scope

- bounded `scope_change_options` contract
- Candidate command boundary
- World State optimistic concurrency
- Engine-owned scope mutation
- Candidate accountability invariant
- no-op scope-change rejection
- event causality and idempotency
- factual Observation boundary
- candidate projection/leakage prevention
- scheduled-effect cancellation ordering
- state-trigger fixed-point evaluation
- Evidence/Profile/Gate isolation
- real frontend integration
- live OIDC E2E
- Stage evidence additions

## Findings

### CR-15-001 — Scope mutation source of truth

**Status:** PASS

Candidate submits only `scope_change_code`, rationale, expected world version and idempotency metadata. The world patch is resolved from the exact pinned Mission Version and applied only by Mission Engine.

### CR-15-002 — Candidate accountability

**Status:** PASS

Missions exposing scope change require canonical `mission.accountability_owner=CANDIDATE`. The post-effect World State is checked and any transfer is rejected with `SCOPE_CHANGE_ACCOUNTABILITY_TRANSFER_FORBIDDEN`.

### CR-15-003 — No-op version/event inflation

**Status:** PASS

A valid scope option must change canonical World State. If the resolved effect produces the current state unchanged, the command is rejected with `SCOPE_CHANGE_NO_EFFECT`; it cannot create an artificial World State version increment.

### CR-15-004 — Candidate leakage

**Status:** PASS

The accepted event may retain `scope_path` and `world_effect_applied` internally for auditability, while Candidate projection exposes only the bounded option identity, Candidate-visible `from_scope/to_scope`, response and world versions. Browser E2E confirms the internal canonical path, raw effects and hidden World truth remain absent. Precondition failures also omit the internal current canonical value.

### CR-15-005 — Evidence/Profile/Gate isolation

**Status:** PASS

Scope change creates factual `SCOPE_CHANGE_OBSERVED` only. It does not create Accepted Evidence, change Proof, compute Capability/Competency level, decide a Gate, mutate Flag Profile, or activate Responsibility.

### CR-15-006 — Post-mutation ordering

**Status:** PASS

After an accepted scope change, the Engine runs scheduled-effect cancellation and then state-triggered fixed-point evaluation, preserving the established deterministic runtime ordering.

### CR-15-007 — Generic world effect did not initially prove a canonical scope transition

**Severity:** Blocking before merge  
**Status:** RESOLVED

The first implementation proved that a bounded World effect ran, but did not require that the action represented a declared scope transition.

Resolution:

- each option pins an internal canonical `scope_path`;
- `from_scope` and `to_scope` are distinct and Candidate-visible;
- Engine requires the current value at `scope_path` to equal `from_scope`;
- Engine applies the pinned `world_effect`;
- Engine requires the post-effect value at `scope_path` to equal `to_scope`;
- the internal accepted event records `scope_path/from_scope/to_scope` for Stage audit;
- `scope_path` remains hidden from Candidate;
- precondition failure does not expose the internal current canonical value.

This makes `CHANGE_SCOPE` a real state transition contract rather than a generic alias for arbitrary World mutation.

## Verification

Baseline CI Run `37314778713` passed for the pre-hardening implementation head `d8624be...`:

- backend lint — PASS
- backend type check — PASS
- backend unit tests — PASS
- migrations — PASS
- OpenAPI export — PASS
- frontend type check — PASS
- frontend unit tests — PASS
- frontend build — PASS
- Live OIDC browser E2E — PASS

The E2E path verifies:

- initial `delivery.scope=FULL_ROLLOUT`
- Candidate submits bounded `CHANGE_SCOPE` through live UI
- `delivery.scope=CRITICAL_CUSTOMERS_ONLY`
- `mission.scope_change_status=ACTIVE`
- `mission.accountability_owner=CANDIDATE` remains unchanged
- `SCOPE_CHANGE_OBSERVED` is Candidate-visible
- raw `world_effect_applied` remains hidden
- later DELEGATE/ESCALATE/DECIDE flow remains operational
- Candidate Proof remains `UNPROVEN`

## Review conclusion

No blocking findings remain in the reviewed code. The canonical scope-transition hardening above still requires final-head CI.

Sprint 15 implementation is approved for merge **only after** the CI run for the commit containing this revised review document is fully Green.
