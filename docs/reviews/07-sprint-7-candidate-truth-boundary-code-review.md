# 07 — Sprint 7 Candidate-visible Truth Boundary Code Review

**Status:** PASS — CODE REVIEW  
**Date:** 2026-10-05

## Reviewed vertical slice

**Canonical World Truth → Candidate Visibility Policy → Candidate Projection → Sanitized Runtime Events/Observations → Live Mission Workspace**

Reviewed PR: **#3 — Sprint 7: candidate-visible truth boundary**

GitHub review: **5410301553**

## Blocking findings

None.

## Review finding fixed before PASS

Initial implementation sanitized unknown Runtime Event payloads but still returned the unknown `event_type` when an event had `visibility=CANDIDATE`.

That could create a metadata side-channel for hidden runtime behavior.

Fix applied before PASS:
- Candidate event visibility is now an explicit event-type allowlist.
- Unknown Runtime Event types are omitted entirely from Candidate response.
- Unknown Observation types are also omitted entirely.

## Governance invariants verified

- Candidate API never serializes canonical `MissionInstance.world_state` directly.
- Candidate World State is derived exclusively through `candidate_visible_paths`.
- Missing/invalid visibility configuration fails closed to an empty state projection.
- Hidden canonical state remains persisted internally.
- Acceptance Mission stores `technical.root_cause_code=DOWNSTREAM_DEPENDENCY` internally while omitting it from Candidate projection.
- `simulation_seed` remains persisted on Mission Instance for replay/debug/audit but is removed from Candidate API and UI.
- Runtime Event DB payload remains richer than Candidate payload where needed for internal audit.
- `decision.committed.effect_applied` remains internal and is not serialized to Candidate.
- Candidate event types require both `visibility=CANDIDATE` and explicit event-type allowlisting.
- Candidate Event payloads are allowlisted per event type.
- Candidate Observation types are explicit allowlist only.
- Candidate Observation payloads are allowlisted per observation type.
- REQUEST_INFORMATION reveals only canonical InformationItem content allowed by Mission Design.
- No Evidence, Proof State, Gate or Flag Profile write path is introduced.

## Assessment Integrity review

The following are internal-only:
- hidden canonical world fields;
- internal consequence effects;
- simulation seed;
- unknown/internal event types;
- unknown/internal observation types.

Candidate-visible:
- explicitly allowed World State paths;
- explicitly disclosed InformationItem content;
- approved Runtime Event metadata/payload;
- approved factual Observations;
- world_state_version required for optimistic concurrency.

## CI evidence

Reviewed implementation head: `31849515cd1d307d01a312943f5f59cc6ff07523`  
CI Run: `37267312422` — **SUCCESS**

Passed:
- Ruff
- Pyright
- Pytest
- Alembic validation
- Development seed
- OpenAPI export
- generated frontend API contract
- TypeScript typecheck
- frontend unit tests
- production frontend build
- Live OIDC browser E2E

Live browser acceptance explicitly proves:
1. Candidate-visible World State is rendered.
2. visible error-rate state is available.
3. `root_cause_code` is absent.
4. raw hidden value `DOWNSTREAM_DEPENDENCY` is absent.
5. simulation seed is absent.
6. discoverable Dependency trace appears only after explicit REQUEST_INFORMATION.
7. hidden root cause remains absent after World State mutation.
8. Candidate Proof remains UNPROVEN.

## Stage gate

Official Ephemeral Stage Acceptance is pending merge to `main`.

## Review result

> **PASS — eligible for merge after this review-document commit receives Green CI.**
