# 41 — Sprint 2: Learning Experience v1

**Status:** IN PROGRESS  
**Approved scope source:** DEC-607

## Goal

Turn the Sprint 1 Academy shell into a real classroom learning loop:

**Class → Pre-work/Material → Assignment → Submission → Instructor Feedback → Practice**

while preserving the hard boundary:

> **Learning Completion / Instructor Feedback ≠ Proven Capability**

## Vertical Slice

Candidate:
- sees pre-work and learning materials;
- sees an assignment;
- submits work;
- receives instructor feedback;
- sees practice activity.

Instructor:
- sees class learning units and assignment;
- sees candidate submission;
- records feedback;
- cannot mark Capability as Proven.

## Technical scope

- Learning bounded context;
- version-safe Assignment/Submission data;
- append-only Instructor Feedback;
- business-intent write APIs;
- transactional Domain Event + Outbox;
- event-driven Candidate/Instructor projection refresh;
- Candidate and Instructor real UI;
- browser E2E through live Keycloak;
- CI + Ephemeral Stage gate.

## Explicit non-goals

- Evidence Engine;
- Capability promotion;
- grading as proof;
- Simulator;
- AI Tutor;
- file upload/object-storage workflow;
- quiz engine beyond foundation types;
- attendance completion automation.
