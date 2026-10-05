# Sprint 15 — Deterministic Scope Change Code Review

**Status:** PASS  
**Date:** 2026-10-05  
**PR:** #13 — Sprint 15: deterministic scope change  
**Reviewed implementation head:** `d8624be643d1cf93cb652f7276109c1b0ef7e6f7`  
**CI:** Run `37314778713` — SUCCESS

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

The accepted event may retain `world_effect_applied` internally for auditability, but the candidate event allowlist exposes only code, response and world versions. Browser E2E confirms raw effects and hidden World truth remain absent.

### CR-15-005 — Evidence/Profile/Gate isolation

**Status:** PASS

Scope change creates factual `SCOPE_CHANGE_OBSERVED` only. It does not create Accepted Evidence, change Proof, compute Capability/Competency level, decide a Gate, mutate Flag Profile, or activate Responsibility.

### CR-15-006 — Post-mutation ordering

**Status:** PASS

After an accepted scope change, the Engine runs scheduled-effect cancellation and then state-triggered fixed-point evaluation, preserving the established deterministic runtime ordering.

## Verification

CI Run `37314778713` passed for implementation head `d8624be...`:

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

No blocking findings remain.

Sprint 15 implementation is approved for merge **only after** the CI run for the commit containing this review document is also fully Green.
