# 75 — Sprint 19: Pattern Engine Foundation

**Status:** IN PROGRESS  
**Date:** 2026-10-06

## Goal

Establish the first auditable Pattern Engine so human-reviewed Accepted Evidence can be assembled into Evidence Sets, proposed as Pattern Candidates, and closed as Reviewed Behaviour Patterns without mutating Profile, Gate, Capability Claim or Responsibility state.

The first executable chain is:

**Accepted Evidence → Evidence Set → Pattern Candidate → Human Review → Reviewed Behaviour Pattern**

## FINAL decision alignment

This Sprint implements the already-final architecture in:

- DEC-328 — Evidence Lifecycle: Raw Event → Observation → Candidate Evidence → Reviewed Evidence → Pattern → Profile Claim.
- DEC-390 — Evidence Engine chain continues Accepted Evidence → Pattern → Profile Claim → Gate Review → Responsibility Recommendation.
- DEC-392 — PatternCandidate and BehaviourPattern are first-class entities.
- DEC-399 — Evidence Strength remains multidimensional and must not collapse into one score.
- DEC-400 — Contradiction is first-class and must not be averaged away.
- DEC-401 — Pattern Engine path is Evidence → Evidence Set → Pattern Candidate → Reviewed Pattern; supported Pattern statuses are EMERGING, REPEATED, STABLE, CONTRADICTED, REGRESSED and RECOVERING.
- DEC-403 — Capability Claims consume supporting/contradictory Patterns later; Level and Scope remain independent.
- DEC-416 — complete lineage Claim → Pattern → Evidence → Interpretation → Observation → Source is mandatory.
- DEC-432 — consequential review remains human-accountable.
- DEC-466 — BehaviourPattern is an independent aggregate.
- DEC-492 — logical backbone contains EvidenceCase → BehaviourPattern → ProfileUpdate.
- DEC-547 — future Capability Lineage must expose Claim → Pattern → Evidence → Interpretation → Observation → Source.
- DEC-567 — `pattern.updated.v1` is a core event contract.

## Scope boundary

Sprint 19 starts **after Accepted Evidence**.

It does not reinterpret immutable Mission Runtime Observation truth and does not reopen Evidence review. It uses only Evidence that already crossed the Sprint 18 human-review boundary.

Rejected or non-accepted Evidence must not enter a Reviewed Behaviour Pattern.

## Evidence Set

An Evidence Set is an explicit, versioned collection of accepted Evidence references selected for one Pattern Candidate.

It must preserve, per Evidence member:

- EvidenceCase id;
- accepted Interpretation id/version;
- subject person id;
- organization context;
- target links;
- signal;
- scope;
- confidence;
- context difficulty;
- prompt contamination;
- source-independence group;
- accepted-at timestamp;
- source lineage reference.

Evidence Set membership is append/audit safe. Historical membership used by a reviewed Pattern must remain reconstructable.

## Pattern Candidate

A Pattern Candidate is a proposal that a defined set of accepted Evidence expresses a recurring or material behavioural pattern.

It must include:

- subject person id;
- organization context;
- behaviour code;
- behaviour description;
- evidence set reference/version;
- candidate pattern status from the DEC-401 vocabulary;
- scope;
- supporting Evidence refs;
- contradictory Evidence refs, when present;
- rationale;
- lineage metadata;
- created-by actor;
- created-at timestamp.

A Pattern Candidate is **not** a Capability Claim, Gate Assessment or proof state.

## Reviewed Behaviour Pattern

A BehaviourPattern is created or updated only through accountable human review.

Allowed Pattern statuses are exactly:

- `EMERGING`
- `REPEATED`
- `STABLE`
- `CONTRADICTED`
- `REGRESSED`
- `RECOVERING`

Sprint 19 does not invent automatic numeric thresholds for moving between these statuses.

Reviewer must be able to inspect all Evidence members and their source lineage before closing the Pattern review.

A reviewed Pattern emits `pattern.updated.v1`.

## Contradiction boundary

Contradictory accepted Evidence must remain explicit.

Sprint 19 must not:

- average contradictory Evidence into a single score;
- delete inconvenient Evidence;
- hide contradictory scope/context;
- silently resolve contradiction by recency alone.

EvidenceConflict automation is still out of scope, but contradictory Evidence references must be preserved in Pattern lineage so DEC-400 can be implemented without data loss.

## Human review boundary

Pattern review is human-accountable.

Parcham AI may become a future proposal source under DEC-397, but Sprint 19 does not invoke Parcham AI and does not introduce any external or internal AI-provider dependency.

No model or automation may autonomously close a Reviewed Behaviour Pattern in this Sprint.

## Parcham AI architecture constraint

Future Pattern assistance must use the proprietary Parcham AI path only:

**Governed Parcham Data → Curated Dataset → Parcham Training → Offline Evaluation → Versioned Parcham Model → Controlled Promotion → Parcham AI Runtime**

No OpenAI, Anthropic, provider LLM, managed AI service, third-party model router or provider adapter may become a source of Pattern intelligence.

Sprint 19 stores enough governed Pattern lineage to become future Parcham-owned training/evaluation material only after a separate curation contract.

## Candidate transparency

Candidate-facing Pattern visibility is permission-sensitive and must not expose hidden Assessment triggers or reviewer-only notes.

Sprint 19 may expose reviewed Pattern facts that are explicitly candidate-visible, but it must not derive Candidate visibility from hidden raw payloads.

## No downstream mutation

Sprint 19 must not directly mutate:

- CapabilityClaim;
- CompetencyClaim;
- Flag Profile;
- GateAssessment;
- ResponsibilityRecommendation;
- proof state;
- Candidate `UNPROVEN` state.

A reviewed Pattern is an input to a later Profile Update / Claim workflow, not the workflow itself.

## Idempotency and concurrency

All Pattern state-changing commands must:

- require optimistic-concurrency `expected_version`;
- reject stale commands with `409 VERSION_CONFLICT`;
- use idempotency keys for retry-safe creation/review commands;
- record domain event + outbox atomically.

Duplicate accepted-Evidence event delivery must not duplicate Evidence Set membership or Pattern Candidates.

## Acceptance scenario

1. Sprint 18 produces accepted reviewed Evidence for a Candidate.
2. Assessor opens the Pattern workspace.
3. Assessor creates an Evidence Set containing only accepted Evidence.
4. Assessor creates a Pattern Candidate with explicit supporting and contradictory Evidence.
5. Reviewer inspects full lineage back to accepted Interpretation and Observation source.
6. Reviewer closes the Pattern as one allowed DEC-401 status.
7. System emits `pattern.updated.v1`.
8. Candidate/Assessor projections enforce their separate visibility rules.
9. No Capability Claim, Profile, Gate, Responsibility or proof state is changed.
10. Candidate remains `UNPROVEN`.

## Out of scope

- automatic Pattern threshold/ranking logic;
- EvidenceConflict automation;
- multi-review CalibrationCase;
- CapabilityClaim creation;
- CompetencyClaim creation;
- ProfileUpdate;
- FlagProfile mutation;
- GateAssessment;
- ResponsibilityRecommendation;
- Parcham AI-generated Pattern proposal;
- Pattern-driven replay scheduling;
- implementation of Pattern-to-training-dataset curation / Automatic Dataset Builder in Sprint 19.

Future Pattern-to-training ingestion is governed by DEC-625 through DEC-627: once Pattern/Learning data becomes approved and policy-eligible for Parcham AI, ingestion and Dataset creation must be event-driven and automatic rather than an Admin-managed manual batch workflow. Sprint 19 only preserves the governed lineage needed by that future pipeline.

## Release gates

Sprint 19 is accepted only if:

- migration succeeds from clean PostgreSQL;
- backend lint/type/unit/API tests pass;
- OpenAPI/client regeneration passes;
- live OIDC browser acceptance covers Assessor Pattern workflow;
- only ACCEPTED Evidence can join the Evidence Set;
- contradictory Evidence remains explicit;
- stale Pattern commands return 409;
- duplicate accepted-Evidence delivery is idempotent;
- reviewed Pattern emits `pattern.updated.v1`;
- full Pattern → Evidence → Interpretation → Observation → Source lineage is queryable;
- Candidate-safe projection does not expose hidden review/source fields;
- no Capability/Profile/Gate/Responsibility mutation occurs;
- Candidate remains `UNPROVEN`;
- Stage artifact proves Pattern counts, lineage and zero downstream mutation.
