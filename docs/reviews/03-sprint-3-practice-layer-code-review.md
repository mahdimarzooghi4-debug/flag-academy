# 03 — Sprint 3 Practice Layer Code Review

**Status:** PASS FOR CURRENT VERTICAL SLICE  
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
