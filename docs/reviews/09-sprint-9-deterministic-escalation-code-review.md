# 09 — Sprint 9 Deterministic Escalation Code Review

**Status:** PASS — CODE REVIEW  
**Date:** 2026-10-05

## Reviewed vertical slice

**Candidate ESCALATE → Engine Validation → Canonical Escalation Rule → World Effect + Actor Effect → Runtime Events → Factual Observation**

Reviewed PR: **#5 — Sprint 9: deterministic escalation**

## Blocking findings

None.

## Review findings

1. ESCALATE is a real CandidateAction, not a frontend-only state change.
2. Client payload contains only actor target, escalation_code, rationale and optimistic concurrency versions.
3. Candidate cannot submit arbitrary World Effect or Actor Effect.
4. Canonical response and both effects are resolved from the exact pinned Mission Version.
5. Mission World State concurrency remains enforced through `expected_world_version`.
6. Actor State concurrency is independently enforced through `expected_actor_version`.
7. ActorInstance is locked with `FOR UPDATE` before mutation.
8. World State and Actor State mutations occur in the same database transaction.
9. Candidate Action idempotency is checked before mutation, preventing successful retry from applying effects twice.
10. `apply_world_effect` still rejects Profile/Evidence/Competency/Gate namespaces.
11. `apply_actor_effect` still rejects governance-reserved actor keys.
12. Internal `world_effect_applied` and `actor_effect_applied` remain audit-only and are not Candidate-visible.
13. `ESCALATION_OBSERVED` stores factual identity/version transitions and no capability judgment.
14. ESCALATE creates no Evidence, Proof State, Gate, Competency or Flag Profile write path.

## Deterministic acceptance rule

Escalation:
- code: `EXECUTIVE_RECOVERY_ESCALATION`
- actor: `business_sponsor`

Before:
- World v1
- Actor v2
- commitment = `SUPPORTIVE`

Canonical effects:
- `stakeholder.executive_attention = ENGAGED`
- `mission.escalation_status = EXECUTIVE_REVIEW`
- Actor `commitment = EXECUTIVE_SPONSORSHIP`

After:
- World v2
- Actor v3

The existing Decision then advances World State from v2 to v3 and completes the Mission.

## Candidate visibility review

Candidate-visible Runtime Events:
- `escalation.requested`
- `escalation.accepted`

Allowed escalation response fields are explicit and fail-closed.

Candidate does **not** receive:
- `world_effect_applied`
- `actor_effect_applied`

Candidate-visible Observation:
- `ESCALATION_OBSERVED`

No hidden World Truth or private Actor State is introduced by this slice.

## CI evidence

Reviewed implementation head: `da8dd005faaf24043323bb0542253b696bd361c6`  
CI Run: `37273727209` — **SUCCESS**

Passed:
- Ruff
- Pyright
- Pytest
- Alembic validation
- development seed
- OpenAPI export
- generated frontend API types
- TypeScript typecheck
- frontend unit tests
- production frontend build
- Live OIDC browser E2E

Live browser acceptance proves:
1. Mission starts with the existing assignment and eligibility gates.
2. Candidate communicates with Business Sponsor and reaches Actor v2.
3. Candidate submits a real escalation rationale.
4. ESCALATE executes against Business Sponsor.
5. Actor reaches v3 and `EXECUTIVE_SPONSORSHIP`.
6. Candidate-visible World State shows `executive_attention=ENGAGED`.
7. Candidate-visible World State shows `escalation_status=EXECUTIVE_REVIEW`.
8. Canonical escalation response is visible.
9. `ESCALATION_OBSERVED` appears.
10. internal applied effects remain hidden.
11. Candidate then requests discoverable information and commits the final Decision.
12. Decision advances World State from v2 to v3.
13. Mission and Assignment reach COMPLETED.
14. Candidate remains UNPROVEN.

## Stage gate

Official Ephemeral Stage Acceptance remains pending until merge to `main`.

## Review result

> **PASS — eligible for merge after this review-document commit itself receives Green CI.**
