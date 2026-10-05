# 67 — Sprint 15: Deterministic Scope Change

**Status:** ACCEPTED  
**Date:** 2026-10-05  
**Acceptance Date:** 2026-10-05

## Goal

Close the next Mission Runtime action gap by making `CHANGE_SCOPE` executable through the exact pinned Mission Version while preserving deterministic state mutation, auditability, Candidate truth boundaries, and separation from Evidence/Profile/Gate semantics.

## Product boundary

`CHANGE_SCOPE` changes the bounded execution scope inside the simulated Mission world. It is not an implicit decision score, not Evidence, and not a Profile/Gate mutation.

A scope change does **not** transfer Mission accountability. If a Mission exposes scope change, `mission.accountability_owner` must remain `CANDIDATE`.

Runtime execution scope is not the immutable Mission Version target scope and is not Evidence scope. `CHANGE_SCOPE` mutates only Canonical Simulation State owned by Mission Runtime; it cannot rewrite Mission Design or create/update Proven Scope.

## Runtime contract

A Mission Version may expose bounded `scope_change_options`. Each option pins:

- `code`
- Candidate-visible `label`
- Candidate-visible `from_scope`
- Candidate-visible `to_scope`
- internal canonical `scope_path`
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
4. Require distinct `from_scope` and `to_scope` plus an internal canonical `scope_path`.
5. Require the current canonical value at `scope_path` to equal `from_scope`.
6. Validate its world effect through the existing reserved-namespace guard.
7. Require the post-effect canonical value at `scope_path` to equal `to_scope`.
8. Enforce `mission.accountability_owner=CANDIDATE` before and after the effect.
9. Persist CandidateAction.
10. Emit `scope_change.requested`.
11. Apply the Engine-owned world effect.
12. Increment world state version.
13. Emit `scope_change.accepted`.
14. Persist factual `SCOPE_CHANGE_OBSERVED`.
15. Run scheduled-effect cancellation.
16. Run state-triggered fixed-point evaluation.
17. Record internal `mission.scope_change_processed.v1`.

## Candidate truth boundary

Candidate may see:

- scope option code and label
- bounded `from_scope → to_scope`
- accepted response
- world version before/after
- candidate-visible World projection
- factual scope-change Observation

Candidate must not see:

- raw `world_effect`
- internal canonical `scope_path`
- hidden World truth
- hidden trigger/cancellation rules
- Evidence/Profile/Gate mutations

## Acceptance scenario

The recovery Mission starts with:

- `mission.accountability_owner=CANDIDATE`
- `delivery.scope=FULL_ROLLOUT`
- `delivery.recovery_coordinator=CANDIDATE`
- canonical scope path is pinned internally as `delivery.scope`

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
- immutable Mission target-scope mutation
- Evidence-scope / Proven-Scope mutation


## Acceptance Record

- Accepted implementation commit: `45a32a3661db06339078750c141bb9703bad110d`
- Sprint 15 product PR: #13
- Main CI Run: `37318314937` — PASS
- Ephemeral Stage Run: `37318314988` — PASS
- Code Review: `docs/reviews/15-sprint-15-deterministic-scope-change-code-review.md` — PASS
- Stage evidence: `docs/68-sprint-15-stage-acceptance.md`
- Stage artifact: `stage-acceptance-evidence`, ID `11348452540`
- Stage artifact digest: `sha256:f864c49ea18442fcc9c3ded107a75b30d26b46883b76b85a11b45ecf849db9cd`

> **Sprint 15 is accepted only as deterministic Mission Runtime capability. Evidence interpretation and Profile/Gate mutation remain out of scope.**
