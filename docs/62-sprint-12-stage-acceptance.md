# 62 — Sprint 12 Stage Acceptance

**Status:** PASS  
**Date:** 2026-10-05  
**Accepted Implementation Commit:** `3a18df5143b2808c8a828ba6dff701646d6c8b9d`

## Accepted runs

- CI: `37297220718` — PASS
- Stage Acceptance: `37297220786` — PASS
- Evidence artifact: `stage-acceptance-evidence`
- Artifact ID: `11340666557`
- Artifact digest: `sha256:a361d06516d130c5d746bf6cde1037124ca4a75f4296c69df8b77c0bdd6df68b`

## Cancellation evidence

```text
commit=3a18df5143b2808c8a828ba6dff701646d6c8b9d
scheduled_effects=4
applied_scheduled_effects=2
time_expired_mission_instances=1
applied_deadline_effects=1
cancelled_recovery_deadlines=1
scheduled_effect_cancelled_events=1
internal_cancel_condition_events=1
scheduled_effect_cancelled_observations=1
pending_deadlines_on_completed_missions=0
scheduled_effect_cancellation=ENGINE_WORLD_STATE_RULE_ONLY
profile_mutation_from_runtime=FORBIDDEN_BY_DOMAIN
browser_oidc_acceptance=PASS
```

## Verified success path

**Mission Assignment → Start → COMMUNICATE → ESCALATE → Executive Checkpoint → DECIDE → Recovery Deadline CANCELLED → Mission COMPLETED**

Verified:
- `RECOVERY_DECISION_DEADLINE = CANCELLED`
- reason = `DECISION_COMMITTED`
- cancellation event persisted
- internal matched condition persisted
- Candidate-safe cancellation Observation persisted
- no recovery deadline remains PENDING on a COMPLETED Mission

## Verified timeout path

**Mission Assignment → Start → ESCALATE → NO_ACTION WAIT_30_MINUTES → Executive Checkpoint APPLIED → Recovery Deadline APPLIED → TIME_EXPIRED**

Verified:
- timeout deadline remains applicable when no committed decision exists
- deadline becomes APPLIED, not CANCELLED
- Mission = TIME_EXPIRED
- Candidate remains UNPROVEN

## Governance verification

- Candidate cannot issue a cancellation command.
- Candidate cannot provide cancellation conditions.
- Cancellation condition comes from the exact pinned Mission Version.
- v1 cancellation schema is bounded to deterministic World State equality.
- Only PENDING + cancellable effects can be cancelled.
- Cancelled effects cannot later apply.
- Internal `cancel_condition_matched` is hidden from Candidate.
- `cancelled_at` uses simulation time while RuntimeEvent `occurred_at` remains wall-clock.
- Cancellation writes no Evidence, Proof State, Competency, Gate or Flag Profile.

## Result

> **Sprint 12 — ScheduledEffect Cancellation: ACCEPTED**

The temporal Mission Runtime now distinguishes all three future-effect outcomes explicitly:

**PENDING → APPLIED | CANCELLED**

with deterministic, auditable causality.
