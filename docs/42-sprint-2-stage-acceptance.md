# 42 — Sprint 2 Stage Acceptance

**Status:** PASS  
**Date:** 2026-10-04  
**Accepted Commit:** `3a7e253213936a2d340bde17ca0458e594d8cb67`

## Gate evidence

- CI run: `37227435115` — PASS
- Ephemeral Stage run: `37227435125` — PASS
- Stage Artifact: `stage-acceptance-evidence`
- Artifact Digest: `sha256:fdaa9e1eebd028536c18355293a13843478c80506e5b2b06460ab10ac86e5a9d`

## Captured Stage evidence

```text
commit=3a7e253213936a2d340bde17ca0458e594d8cb67
published_outbox_events=11
processed_inbox_events=11
candidate_home_rows=1
instructor_home_rows=1
completed_learning_units=2
feedback_provided_submissions=1
learning_completed_capabilities=1
unproven_capabilities=5
browser_oidc_acceptance=PASS
```

## Accepted behavior

The Stage browser flow verified:

**Candidate Login → Pre-work Start/Complete → Practice Start/Complete → Assignment Submission → Instructor Login → Submission Review → Instructor Feedback → Candidate Login → Feedback Visible**

It additionally verified that the learning flow can reach `LEARNING_COMPLETED` while Proof remains `UNPROVEN`.

## Result

> **Sprint 2 — Learning Experience v1: ACCEPTED**

This completes Product Milestone **M1 Learning Loop** for the current vertical slice. Evidence/Proof remains a separate later milestone.
