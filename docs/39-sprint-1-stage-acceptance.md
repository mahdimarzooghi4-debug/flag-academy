# 39 — Sprint 1 Stage Acceptance

**Status:** PASS  
**Date:** 2026-10-04  
**Accepted Commit:** `c7405e6658afe6d3e26ec6ec268eb0e3fd91c489`

## Gate

Sprint 1 required a clean Stage environment and end-to-end acceptance before completion.

Stage v1 uses the approved Ephemeral Stage workflow in GitHub Actions.

## Accepted Run

- CI: `37223606979` — PASS
- Stage Acceptance: `37223607002` — PASS
- Evidence Artifact: `stage-acceptance-evidence`
- Artifact Digest: `sha256:cc9e3f1fd26873e4ef3cc1f482c1aef17da6f3cb879df406cb68d6c861444697`

## Acceptance Evidence

```text
commit=c7405e6658afe6d3e26ec6ec268eb0e3fd91c489
published_outbox_events=3
processed_inbox_events=3
candidate_home_rows=1
instructor_home_rows=1
browser_oidc_acceptance=PASS
```

## Verified

- clean PostgreSQL migration;
- live Keycloak OIDC + PKCE;
- Candidate browser login and Candidate Home;
- Instructor browser login and Instructor Home;
- NATS JetStream event publication;
- durable Inbox processing;
- Candidate/Instructor read-model projection;
- acceptance evidence artifact creation;
- ephemeral environment cleanup.

## Result

> **Sprint 1 — Academy Foundation Vertical Slice: ACCEPTED**

This closes the Stage/QA acceptance gate for Sprint 1. Release Approval remains a separate parent-process gate before Production.
