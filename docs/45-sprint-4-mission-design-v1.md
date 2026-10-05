# 45 — Sprint 4: Mission Design v1

**Status:** ACCEPTED — Stage Acceptance PASS on 2026-10-05  
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


## Sprint 4 Acceptance

Accepted implementation commit: `1fb9187a904fedf8d0d43853d3b67a9a9330c30f`

Validated end-to-end:
- Academy Admin authentication through live Keycloak;
- Mission Template creation in Academy Studio;
- exact Capability Version reference;
- structured Actors, Information, Constraints, Decision Points, Consequence Rules and Evidence Opportunities;
- Definition Validation;
- lifecycle DRAFT → PILOT → VALIDATED → ACTIVE;
- optimistic aggregate version checks;
- transactional Domain Events and Outbox;
- one ACTIVE Mission Version persisted in PostgreSQL;
- Mission Design remains separate from Mission Runtime, Evidence and Profile.

CI Run: `37260658807` — PASS  
Stage Acceptance Run: `37260658937` — PASS

Sprint 4 is **ACCEPTED** against its scoped Definition of Done.
