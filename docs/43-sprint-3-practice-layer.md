# 43 — Sprint 3: Practice Layer Vertical Slice

**Status:** IN PROGRESS  
**Backlog source:** Epic 07 — Practice Layer (approved Product Backlog v1)

## Goal

Turn Practice from a passive completion checkbox into an observable developmental attempt:

**Practice Activity → Candidate Attempt → Instructor Feedback**

while preserving:

> **Practice feedback is developmental and does not directly mutate Evidence or Proof.**

## First vertical slice

- guided Practice activity uses the existing PRACTICE Learning Unit definition;
- Candidate submits a structured free-text Practice Attempt;
- the attempt completes that Practice learning unit;
- Instructor sees the real attempt and records developmental feedback;
- Candidate receives that feedback;
- Capability Proof remains independent and unchanged.

## Explicit non-goals

- Evidence acceptance;
- Capability promotion;
- Simulator;
- AI Tutor;
- group orchestration;
- automated scoring.


## Second vertical slice — Feedback-driven Replay

Practice is extended from one submission into an immutable developmental history:

**Attempt 1 → Instructor Feedback → Replay Attempt 2 → New Feedback**

Rules implemented in this slice:

- an existing Practice Attempt is never overwritten;
- each new Attempt receives a monotonic `attempt_number`;
- Replay keeps lineage through `replay_of_attempt_id`;
- Candidate cannot create the next Attempt until the latest Attempt has Instructor Feedback;
- Candidate and Instructor can inspect the chronological Attempt/Feedback history;
- Practice Replay remains developmental and does not directly update Evidence or Proof.

This is Practice Replay, not Evidence Replay. Evidence/assessment replay remains owned by the later Evidence Engine.


## Third vertical slice — Practice modality

Practice now distinguishes the developmental format from the generic Learning Unit phase.

Supported Practice kinds in the domain contract:
- `GUIDED_EXERCISE`
- `CASE_STUDY`
- `WORKSHOP`
- `GROUP_EXERCISE`

The current executable UI demonstrates:
- Guided Exercise;
- Case Study.

Workshop and Group Exercise are now representable in the contract but remain future executable slices because group/session orchestration is not implemented yet.

Practice kind changes the learning experience, not the Proof rules. A completed Case Study or Guided Exercise still does not directly prove Capability.
