# 45 — Sprint 4: Mission Design v1

**Status:** IN PROGRESS  
**Backlog source:** Epic 08 — Mission Design (approved Product Backlog v1)

## Goal

Create the first real Academy Studio vertical slice for versioned Mission authoring:

**Academy Admin → Mission Template → Draft Version → Validate → Pilot → Validated → Active**

without introducing Mission Runtime yet.

## Invariants

- Mission Template and Mission Version are separate.
- Historical Mission versions are immutable in meaning.
- Activation follows the lifecycle DRAFT → PILOT → VALIDATED → ACTIVE.
- Active versions are not edited in place; a new definition requires a new version.
- Mission Design references an exact capability_version_id.
- Definition includes actors, information, constraints, decision points, consequence rules, evidence opportunities, replay policy and safety policy.
- No hidden single correct answer field exists.
- Mission Design does not mutate Candidate Profile or Evidence.
- Academy Studio access requires ACADEMY_ADMIN.

## First vertical slice

- mission_design schema and aggregate model;
- Studio business APIs;
- optimistic aggregate version check on lifecycle transitions;
- transactional Domain Event + Outbox;
- Academy Admin identity in development/stage;
- real Studio UI;
- live OIDC browser acceptance;
- clean migration and Stage verification.

## Explicit non-goals

- Mission Runtime;
- World State execution;
- Candidate mission assignment;
- Observation generation;
- Evidence review;
- AI actors;
- adaptive difficulty.
