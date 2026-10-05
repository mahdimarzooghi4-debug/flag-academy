# 65 — Sprint 14: Deterministic Delegation

**Status:** ACCEPTED  
**Date:** 2026-10-05  
**Acceptance Date:** 2026-10-05

## Goal

Close the next Mission Runtime action gap by making `DELEGATE` executable through the pinned Mission Version while preserving the deterministic, auditable, candidate-safe runtime boundary.

## Product boundary

Delegation changes execution responsibility inside the simulated world; it does **not** transfer the Candidate's accountability for the Mission outcome. Any Mission that exposes delegation must declare the canonical `mission.accountability_owner=CANDIDATE`, and the Engine rejects a delegation effect that changes it.

**Delegation ≠ Proven Capability**  
**Delegation ≠ Evidence**  
**Delegation ≠ Profile/Gate mutation**

The Mission Engine may produce a factual Observation from the accepted delegation. Evidence interpretation remains out of scope.

## Runtime contract

A Mission Version may expose bounded `delegation_options`. Each option pins:

- `code`
- Candidate-visible `label`
- target `actor_key`
- Engine response
- deterministic `world_effect`
- deterministic `actor_effect`

The Candidate submits only:

- target Actor
- `delegation_code`
- rationale
- expected world version
- expected Actor state version
- idempotency key

The Candidate cannot submit state patches or consequence rules.

## Execution

1. Lock Mission Instance and target Actor.
2. Enforce RUNNING status, world optimistic concurrency, and Actor optimistic concurrency.
3. Resolve the delegation only from the pinned Mission Version.
4. Validate world/actor effects through existing reserved-namespace guards.
5. Enforce that canonical `mission.accountability_owner` remains `CANDIDATE`.
6. Persist CandidateAction.
7. Emit `delegation.requested`.
8. Apply Engine-owned world and Actor effects.
9. Increment world and Actor state versions.
10. Emit `delegation.accepted`.
11. Persist factual `DELEGATION_OBSERVED`.
12. Run scheduled-effect cancellation and state-trigger fixed-point evaluation after the world mutation.
13. Record internal `mission.delegation_processed.v1`.

## Candidate truth boundary

Candidate may see:

- delegation option code/label/target
- accepted response
- world version before/after
- Actor state version before/after
- candidate-visible World/Actor projections
- factual Observation

Candidate must not see:

- raw `world_effect`
- raw `actor_effect`
- hidden Actor state
- hidden World truth
- Evidence/Profile/Gate mutation

## Acceptance scenario

The recovery Mission includes a `Delivery Lead` Actor.

Initial truth:
- Candidate remains `accountability_owner`.
- Candidate is initially the `recovery_coordinator`.
- Delivery Lead has no delegated responsibility.

Candidate delegates recovery coordination to Delivery Lead.

Expected deterministic result:
- `accountability_owner` remains `CANDIDATE`.
- `recovery_coordinator` becomes `DELIVERY_LEAD`.
- delegation status becomes `ACTIVE`.
- Delivery Lead state records accepted recovery coordination.
- Candidate sees the bounded outcome and factual Observation.
- internal effect payloads remain hidden.
- Proof remains `UNPROVEN`.

## Out of scope

- CHANGE_SCOPE
- ALLOCATE_RESOURCE
- RUN_EXPERIMENT
- Evidence Engine
- Profile/Gate updates
- probabilistic delegation decisions
- LLM-authored runtime effects


## Acceptance Record

- Accepted implementation commit: `a716b7e002bc3a46ea1a017acafa666c81a6c007`
- Sprint 14 product merge: `19accae98fea1f5ffcb94812a8af7831c130bba0`
- Stage infrastructure recovery: PR #12, merged into accepted commit
- Main CI Run: `37312765807` — PASS
- MinIO Image Smoke Run: `37312765917` — PASS
- Ephemeral Stage Run: `37312765996` — PASS
- Code Review: `docs/reviews/14-sprint-14-deterministic-delegation-code-review.md` — PASS
- Stage evidence: `docs/66-sprint-14-stage-acceptance.md`
- Stage artifact: `stage-acceptance-evidence`, ID `11345534784`
- Stage artifact digest: `sha256:b97a91eaa1de7374c925190605699b5a7a2d0907a4bc44d9473b44a3598b795e`

> **Sprint 14 is accepted only as deterministic Mission Runtime capability. Evidence interpretation and Profile/Gate mutation remain out of scope.**
