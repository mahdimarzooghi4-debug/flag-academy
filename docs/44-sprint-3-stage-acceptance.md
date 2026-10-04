# 44 — Sprint 3 Stage Acceptance

**Status:** PASS  
**Date:** 2026-10-04  
**Accepted Commit:** `490c644d0ed5e8239ef440279826388624fc5067`

## Gate

Sprint 3 required a clean Ephemeral Stage and real browser acceptance through live Keycloak before acceptance.

## Accepted runs

- CI: `37231700807` — PASS
- Stage Acceptance: `37231700888` — PASS
- Evidence Artifact: `stage-acceptance-evidence`
- Artifact Digest: `sha256:37bb4d0508dccfdafdbba05170d70e589b43937b8a0218c311c2191af936ebbc`

## Acceptance evidence

```text
commit=490c644d0ed5e8239ef440279826388624fc5067
published_outbox_events=14
processed_inbox_events=14
candidate_home_rows=1
instructor_home_rows=1
completed_learning_units=3
feedback_provided_submissions=1
learning_completed_capabilities=1
unproven_capabilities=5
practice_attempts=3
practice_feedback_rows=2
practice_feedback_provided_attempts=2
practice_replay_attempts=1
practice_kind_count=2
case_study_attempts=1
browser_oidc_acceptance=PASS
```

## Verified product behavior

Candidate:
- completes Pre-work;
- performs a Guided Exercise;
- performs a Case Study;
- submits an Assignment;
- receives Instructor feedback;
- sees immutable Practice history;
- performs a feedback-driven Replay.

Instructor:
- sees Candidate Practice Attempts;
- distinguishes Practice modality;
- records developmental feedback per Attempt;
- sees Attempt/Feedback history.

Governance invariant:
- Learning completion, Practice, Replay and Instructor feedback remain developmental;
- Capability Proof remains independent and `UNPROVEN` in this slice.

## Result

> **Sprint 3 — Practice Layer: ACCEPTED**

Workshop and Group Exercise orchestration remain future Epic 07 scope.
