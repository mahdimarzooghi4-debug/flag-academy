# 08 — Sprint 8 Actor State & COMMUNICATE Code Review

**Status:** PASS — CODE REVIEW  
**Date:** 2026-10-05

## Reviewed vertical slice

**Mission Actor Definition → ActorInstance → Candidate COMMUNICATE → Deterministic Engine Effect → Actor Response → Observation**

Reviewed PR: **#4 — Sprint 8: actor state and deterministic communicate**

## Blocking findings

None.

## Review findings and checks

1. Actor state mutation is engine-owned. Candidate payload supplies only `communication_code`, target actor and utterance; canonical reply/effect are resolved from the pinned Mission Version.
2. ActorInstance is locked with `FOR UPDATE` before mutation.
3. `expected_actor_version` provides actor-level optimistic concurrency and stale writes return conflict.
4. Mission World State optimistic concurrency remains independently enforced through `expected_world_version`.
5. Candidate Action idempotency remains instance-scoped; a successful retry cannot apply the actor effect twice.
6. Reserved actor-state keys cannot be mutated by canonical actor effects.
7. Candidate-visible Actor State is an explicit projection and private actor fields are omitted.
8. Internal `actor.responded.actor_effect_applied` remains available for audit but is not in the Candidate event payload allowlist.
9. Actor response Observation is factual and records the state-version transition; it does not interpret capability or proof.
10. COMMUNICATE does not write Evidence, Proof State, Gate, Competency or Flag Profile.

## Authorization / isolation

- ActorInstance lookup is constrained to the already candidate-owned Mission Instance.
- actor_key must exist on that Mission Instance.
- actor runtime configuration is resolved from the exact pinned Mission Version.
- Candidate cannot choose an arbitrary effect or arbitrary reply.

## Determinism

Acceptance communication:
- Actor: `business_sponsor`
- Strategy: `OWN_AND_ALIGN_RECOVERY`
- Initial candidate-visible state:
  - trust_toward_candidate = 35
  - current_frustration = 70
  - commitment = CONDITIONAL
- Result:
  - trust_toward_candidate = 60
  - current_frustration = 40
  - commitment = SUPPORTIVE

The private field `private_escalation_threshold=LOW` remains canonical/internal.

## CI evidence

Reviewed implementation head: `146f7f05f564b11d7ffedf18bcf6986c9a967979`  
CI Run: `37271115302` — **SUCCESS**

Passed:
- Ruff
- Pyright
- Pytest
- Alembic migration validation through `0010`
- Development seed
- OpenAPI export
- generated frontend API contract
- TypeScript typecheck
- frontend unit tests
- production frontend build
- Live OIDC browser E2E

Live browser acceptance proves:
1. Actor starts at state version 1.
2. candidate-visible state is rendered.
3. private actor state is absent.
4. Candidate writes a real utterance.
5. deterministic communication strategy executes.
6. Actor moves to state version 2.
7. trust/frustration/commitment change to the canonical expected values.
8. canonical reply is visible.
9. `ACTOR_RESPONSE_OBSERVED` appears.
10. internal `actor_effect_applied` is not exposed.
11. Mission still completes through the existing Decision path.
12. Candidate Proof remains UNPROVEN.

## Stage gate

Official Ephemeral Stage Acceptance is pending merge to `main`.

## Review result

> **PASS — eligible for merge after this review-document commit itself receives Green CI.**
