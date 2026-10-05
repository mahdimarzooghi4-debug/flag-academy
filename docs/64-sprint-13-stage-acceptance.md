# 64 — Sprint 13 Stage Acceptance

**Status:** PASS  
**Date:** 2026-10-05  
**Accepted Implementation Commit:** `c3bb447dec3e1c2c5c8968a78075bd171fd8976e`

## Accepted runs

- CI: `37304079338` — PASS
- Stage Acceptance: `37304079367` — PASS
- Evidence artifact: `stage-acceptance-evidence`
- Artifact ID: `11342967390`
- Artifact digest: `sha256:f6b29c2ab4e0f1eaa1e2ea94b8df242232740368a03c36aa1788bc590b37b1e3`

## State-trigger evidence

```text
commit=c3bb447dec3e1c2c5c8968a78075bd171fd8976e
scheduled_effects=6
scheduled_effect_created_events=6
scheduled_effect_applied_events=4
scheduled_effect_observations=4
cancelled_recovery_deadlines=1
scheduled_effect_cancelled_events=2
scheduled_effect_cancelled_observations=2
state_triggered_effects=2
applied_state_triggered_effects=1
cancelled_state_triggered_effects=1
state_triggered_apply_events=1
state_triggered_observations=1
broadcast_world_state_rows=1
timeout_unbroadcast_world_state_rows=1
pending_state_triggers_on_terminal_missions=0
invalid_scheduled_trigger_rows=0
state_trigger_execution=ENGINE_WORLD_STATE_RULE_ONLY
scheduled_effect_cancellation=ENGINE_WORLD_STATE_RULE_ONLY
no_action_time_advance=CANONICAL_OPTION_ONLY
timeout_transition=SCHEDULED_EFFECT_ONLY
profile_mutation_from_runtime=FORBIDDEN_BY_DOMAIN
browser_oidc_acceptance=PASS
```

## Verified success path

**Mission Assignment → Start → COMMUNICATE → ESCALATE → timed checkpoint → DECIDE(COMMITTED) → recovery deadline CANCELLED → state-triggered broadcast APPLIED → Mission COMPLETED**

Verified:
- `RECOVERY_COMMITMENT_BROADCAST = APPLIED`
- state trigger executed without simulation-clock advance
- `stakeholder.recovery_signal = BROADCAST`
- state-triggered RuntimeEvent persisted
- factual state-triggered Observation persisted
- internal `trigger_condition_matched` is retained for audit but hidden from Candidate
- Candidate remains UNPROVEN

## Verified timeout path

**Mission Assignment → Start → ESCALATE → NO_ACTION → timed deadline APPLIED → decision EXPIRED → state-triggered broadcast CANCELLED → TIME_EXPIRED**

Verified:
- `RECOVERY_COMMITMENT_BROADCAST = CANCELLED`
- `stakeholder.recovery_signal = NOT_BROADCAST`
- no state-triggered effect remains PENDING on terminal Missions
- timeout semantics remain driven only by the timed recovery deadline
- Candidate remains UNPROVEN

## Persistence verification

- `due_at` may be NULL only for a state-triggered effect.
- `trigger_condition` may be NULL only for a timed effect.
- PostgreSQL enforces exactly one trigger with `(due_at IS NOT NULL) <> (trigger_condition IS NOT NULL)`.
- Stage reports `invalid_scheduled_trigger_rows=0`.
- JSONB absence is persisted as SQL NULL via `JSONB(none_as_null=True)`.

## Governance verification

- Candidate cannot author or mutate trigger rules.
- Trigger rules come only from the pinned Mission Version.
- v1 trigger schema is bounded to deterministic `WORLD_STATE_EQUALS`.
- clock advance ignores state-triggered effects.
- NO_ACTION only reasons over timed effects.
- cancellation is evaluated before state-trigger application after the causing mutation.
- internal trigger/effect payloads are not exposed to Candidate.
- state-trigger consequences do not mutate Evidence, Proof State, Competency, Gate or Flag Profile.

## Result

> **Sprint 13 — State-triggered Scheduled Effects: ACCEPTED**

The Mission Runtime now supports both explicit consequence triggers:

**TIME → due_at**  
**WORLD STATE → trigger_condition**

with deterministic, auditable execution and explicit terminal outcomes:

**PENDING → APPLIED | CANCELLED**
