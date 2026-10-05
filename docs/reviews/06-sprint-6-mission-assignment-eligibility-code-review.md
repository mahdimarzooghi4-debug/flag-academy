# 06 — Sprint 6 Mission Assignment & Eligibility Code Review

**Status:** PASS — CODE REVIEW  
**Date:** 2026-10-05

## Reviewed vertical slice

**Active Mission Version → Academy Admin Assignment → Candidate Eligibility Check → Mission Instance → Runtime → Assignment Completion**

Reviewed PR: **#2 — Sprint 6: mission assignment and eligibility**

## Blocking findings

None.

## Review fixes applied before PASS

1. Runtime domain spacing was normalized before final Ruff gate.
2. Candidate selector was tightened to Candidates with both contextual CANDIDATE membership and ACTIVE Candidate Journey.
3. Start retry semantics were tightened so an already-created assignment-bound Mission Instance remains retrievable even if its Mission Version is retired later; only a genuinely new Start requires ACTIVE Mission Version.

## Governance invariants verified

- ACTIVE Mission Version alone does not authorize Candidate execution.
- Mission Assignment creation requires ACADEMY_ADMIN.
- Assignment Candidate is resolved inside the same Organization Context.
- Assignment creation requires contextual CANDIDATE membership.
- Assignment creation requires ACTIVE Candidate Journey.
- Candidate mission catalog is sourced from MissionAssignment, not the global set of ACTIVE Mission Versions.
- An unassigned Mission is not returned to Candidate Runtime Workspace.
- Start requires assignment_id belonging to the same Candidate, Organization and exact Mission Version.
- Eligibility is re-evaluated at Start; a historical Assignment alone is insufficient.
- Mission Assignment row is locked during Start.
- Each Mission Assignment can bind to at most one Mission Instance.
- Mission Instance preserves exact assignment_id and mission_version_id lineage.
- Assignment lifecycle is explicit: ASSIGNED → STARTED → COMPLETED, with CANCELLED reserved by the domain lifecycle.
- Runtime records mission.eligibility_passed in the immutable Runtime timeline.
- Domain events use mission.assigned.v1, mission.started.v1 and mission.completed.v1.
- Mission completion transitions the bound Assignment to COMPLETED in the same transaction.
- Mission Assignment and Eligibility expose no write path to Evidence, Proof State, Competency, Gate or Flag Profile.
- Candidate remains UNPROVEN after Mission completion.

## Authorization / isolation review

- Admin candidate discovery is scoped to the current Organization Context.
- Candidate discovery requires both CANDIDATE membership and ACTIVE Candidate Journey.
- Assignment listing is organization-scoped.
- Candidate catalog is candidate-scoped and organization-scoped.
- Forged assignment_id for another Candidate, Organization or Mission Version cannot satisfy the Start query.
- Existing Mission Instance access remains candidate-owned and organization-scoped.

## Idempotency / concurrency review

- Assignment create has organization-scoped idempotency key uniqueness.
- Reuse of an idempotency key with different Candidate/Mission inputs returns conflict.
- Mission Start uses assignment row locking.
- Mission Instance has a unique assignment_id constraint.
- Existing assignment-bound instance is returned instead of creating a second instance.
- Candidate Action world-state optimistic concurrency remains enforced independently through expected_world_version.

## CI evidence

Reviewed implementation head: `8c0f80ca04c7ed370322d0e2384da6f24f9789db`  
CI Run: `37265248418` — **SUCCESS**

Passed:
- Ruff
- Pyright
- Pytest
- Alembic upgrade through migration 0009
- Development seed
- OpenAPI export
- generated frontend API contract
- TypeScript typecheck
- frontend unit tests
- production frontend build
- Live OIDC browser E2E

Live browser acceptance explicitly proves:
1. Active but unassigned Mission is not visible to Candidate.
2. Academy Admin assigns the Mission to Candidate Demo.
3. Candidate then sees and starts the Mission.
4. Runtime reaches COMPLETED.
5. Assignment state reaches COMPLETED in the UI.
6. Candidate Proof remains UNPROVEN.

## Stage gate

Stage is intentionally **PENDING** at Code Review time. Official Ephemeral Stage Acceptance runs only after merge to `main`.

## Review result

**PASS — eligible for merge after this review-document commit itself receives Green CI.**
