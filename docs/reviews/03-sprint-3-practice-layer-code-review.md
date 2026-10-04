# 03 — Sprint 3 Practice Layer Code Review

**Status:** PASS — SPRINT 3  
**Date:** 2026-10-04

## Reviewed slice

**Practice Activity → Candidate Attempt → Instructor Developmental Feedback**

## Invariants verified

- Practice Attempt is distinct from Assignment Submission.
- Practice feedback is stored append-only.
- Candidate must belong to the Cohort/Class that owns the Practice Unit.
- Instructor must be assigned to that Class.
- Practice submission completes only the Learning Unit progress.
- Practice Attempt and feedback emit transactional Domain Events.
- Read models update asynchronously through Outbox/Inbox.
- Practice feedback does not mutate Proof State.
- Candidate remains `UNPROVEN` after Practice + Feedback.

## Scope note

This review passes the current guided-practice vertical slice. It does **not** close all of Epic 07: Workshop, Case Study, Group Exercise, multiple/replay Practice Attempts and AI Tutor remain future scope.


## Replay and Practice-kind review

Verified:
- Attempt history is append-only; previous attempts are never overwritten.
- Each Attempt has a monotonic `attempt_number`.
- Replay lineage is explicit through `replay_of_attempt_id`.
- A new Replay is blocked until the latest Attempt has Instructor Feedback.
- Guided Exercise and Case Study are first-class Practice kinds.
- Workshop and Group Exercise are represented in the domain contract but are not executable in this sprint.
- Practice completion and feedback never mutate Proof.

## Final Sprint 3 Review

Code Review: **PASS**  
CI: **PASS** — Run `37231700807`  
Ephemeral Stage Acceptance: **PASS** — Run `37231700888`

Accepted commit: `490c644d0ed5e8239ef440279826388624fc5067`.
