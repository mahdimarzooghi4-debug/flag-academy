# 90 — Parcham AI Decision-Making Seed Corpus v1

**Status:** CURATED SEED ARTIFACT — NOT YET INGESTED INTO AI DATASET  
**Date:** 2026-10-08  
**Corpus file:** `docs/ai/seed/decision-making-v1.jsonl`  
**Record count:** 24  
**Language:** fa-IR  
**Capability focus:** Decision Making  
**Synthetic:** yes

## Purpose

This corpus gives Parcham AI a minimum, explicit behavioural starting point for Decision Making before enough reviewed real Academy data exists.

It is not intended to prove model quality or replace future real data.

It is intended to teach initial behaviour such as:
- clarify the decision question;
- distinguish Evidence from Assumption;
- expose Trade-offs;
- reason about Risk and Cost of Delay;
- distinguish reversible from hard-to-reverse decisions;
- define Revisit Triggers;
- revise decisions when new Evidence warrants it;
- separate Decision Quality from Outcome Quality;
- avoid Confirmation Bias and Hindsight Bias;
- express uncertainty instead of inventing certainty;
- preserve LEARN / PRACTICE / ASSESSMENT boundaries;
- preserve Human Review boundaries for Evidence/Profile/Gate.

## Canonical sources

The corpus is authored from approved Parcham contracts, including:

- `docs/08-parcham-ai-architecture.md`
- `docs/12-capability-problem-framing.md`
- `docs/13-capability-decision-making.md`
- `docs/14-capability-data-thinking.md`
- `docs/18-capability-prioritization.md`
- `docs/19-capability-metrics-experimentation.md`
- `docs/21-capability-delivery.md`
- `docs/22-capability-stakeholder-alignment.md`
- `docs/25-capability-reflection-learning.md`
- `docs/26-curriculum-operating-model.md`
- `docs/27-prerequisite-gates-evidence-graph.md`
- `docs/88-sprint-23-class-simulator-foundation.md`

## Record schema

Each JSONL record contains:

- `id` — immutable seed record identifier;
- `schema_version`;
- `language`;
- `capability`;
- `mode`;
- `task_type`;
- `input`;
- `preferred_response`;
- `prohibited_behavior`;
- `labels`;
- `source_refs`;
- `synthetic=true`.

This schema is an authoring format. It does not override the existing P22 Dataset Builder persistence contract.

## Coverage in v1

The 24 examples intentionally cover:

1. Decision Quality vs Outcome Quality
2. Decision Question
3. Missing Data / Value of Information
4. Bad-options Trade-off
5. Executive Pressure
6. New Evidence / Revisit Trigger
7. Reversibility
8. Assessment no-hint boundary
9. Assessment requested-data boundary
10. Instructor feedback drafting
11. Replay / scenario variation
12. Cost of Delay
13. Option Set
14. Confirmation Bias
15. Confidence / uncertainty
16. Misleading Metrics
17. Quality vs Deadline
18. Stakeholder pressure
19. Post-decision Reflection
20. Missing-data / inactivity boundary
21. Decision Log
22. Supply disruption scenario
23. Budget-cut scenario
24. Formal Evidence/Profile/Gate boundary

## What this Seed is and is not

### It is

- synthetic;
- authored;
- source-linked;
- small by design;
- intended to bootstrap basic Decision-Making behaviour;
- suitable to be considered for governed AI-learning approval.

### It is not

- production classroom data;
- an Evaluation Dataset;
- a benchmark proving model quality;
- a complete Product Manager curriculum;
- sufficient evidence for choosing a final Production model;
- authorization to start Training;
- authorization to activate runtime.

## Required review before AI-learning ingestion

Before this Seed enters the governed Dataset Builder, an accountable human must review at least:

- source references are still current;
- no sample violates current Parcham governance;
- ASSESSMENT samples do not leak decisive hints;
- no sample invents numeric thresholds or readiness scores;
- no sample implies automatic Evidence/Profile/Gate mutation;
- synthetic records are clearly classified as synthetic;
- exact source payload bytes are hashed;
- AI-learning approval is explicit and separate from knowledge-use approval.

The existing P22 governed intake must remain authoritative.

## Initial Dataset strategy

The intended first governed learning Dataset may begin with this approved Seed corpus.

Conceptually:

**Seed Corpus v1**
→ explicit Human AI-learning approval
→ existing Automatic Dataset Builder
→ **Decision-Making Dataset Version 1**

No Dataset Version is considered created merely because this file exists in the repository.

## Controlled enrichment over time

After Academy operations begin, new Dataset Versions should grow from reviewed, policy-eligible learning inputs.

The intended loop is:

**Synthetic Seed v1**
→ **Dataset v1**
→ reviewed eligible real examples
→ **Dataset v2**
→ more reviewed eligible examples
→ **Dataset v3**
→ ...

Every version remains immutable and keeps provenance.

New real data must not silently overwrite Seed examples.

## Candidate future real-data sources

Possible sources may include only data that has already passed the relevant product/human governance, for example:

- explicitly approved Instructor feedback examples;
- reviewed Decision Logs;
- reviewed Reflection + Replay pairs;
- reviewed behavioural observations eligible for AI learning;
- approved content corrections;
- reviewed examples of good/weak Decision reasoning;
- explicitly approved simulator interactions.

This list is not automatic eligibility.

Each source category still needs an approved source policy and AI-learning approval before it may enter a Dataset.

## Excluded raw data

These must not flow directly into training:

- raw Attendance;
- inactivity alone;
- unreviewed free text;
- private Assessor notes;
- hidden Gate rationale outside permitted policy;
- raw Candidate conversations without approval;
- arbitrary production logs;
- AI output simply because AI generated it.

## Enrichment principle

The model should become richer through **reviewed diversity**, not volume alone.

Useful enrichment should add coverage across:
- different Contexts;
- contradictory Evidence;
- reversible and irreversible decisions;
- time pressure;
- resource constraints;
- stakeholder pressure;
- incomplete data;
- changing Evidence;
- negative outcomes after good decisions;
- positive outcomes after weak decisions;
- different learner mistakes;
- instructor corrections;
- Replay showing actual behaviour change.

## Anti-collapse requirement

Future Dataset growth must not turn the model into a pattern-matcher that always gives one preferred answer.

For Decision Making, multiple defensible decisions may exist.

Training examples should teach:
- quality of reasoning;
- explicit assumptions;
- trade-offs;
- uncertainty;
- evidence use;
- revisability;

not one canonical option choice for every scenario.

## Evaluation separation

Training and Evaluation data must remain distinct.

A synthetic scenario used for training must not be reused unchanged as the only evidence of Evaluation success.

Future Evaluation Dataset construction remains under the P22 independent evaluation contract.

## Seed Learning Approval Bridge — COMPLETE

The governed bridge is implemented.

Runtime Seed artifact:
- `backend/app/ai_control_plane/seeds/decision-making-v1.jsonl`
- exact CI assertion keeps it byte-identical to `docs/ai/seed/decision-making-v1.jsonl`;
- artifact SHA-256 is computed from runtime bytes at approval time;
- the backend package explicitly includes `seeds/*.jsonl`.

Admin API:
- `GET /api/v1/admin/ai/seed-learning/decision-making-v1`
  - ACADEMY_ADMIN only;
  - returns exact Seed metadata, record count and SHA-256;
  - reports whether this organization context already has a Seed learning approval.
- `POST /api/v1/admin/ai/seed-learning/decision-making-v1/approve`
  - ACADEMY_ADMIN only;
  - requires the exact reviewed `expected_source_payload_digest`;
  - requires an explicit `approval_reference`;
  - records a PERSON actor from the authenticated Academy Admin;
  - fails closed if the Seed changed after preview;
  - is multi-replica serialized and idempotent for an exact retry;
  - conflicts if the same Seed version already has different Human approval semantics.

The Bridge has no arbitrary Dataset/source upload parameters. Dataset name, purpose, policy, source type and source reference are fixed by the approved Seed contract.

The Bridge does **not** call the Dataset Builder directly. It records the existing:

`ai.learning_input_approved.v1`

Domain Event + transactional Outbox. The existing NATS consumer and Automatic Dataset Builder remain authoritative for Dataset creation.

The Bridge does not:
- start Training;
- create a Model Version;
- start Evaluation;
- promote a Model;
- activate runtime.

### Acceptance evidence

Implementation HEAD before this completion-record update:

`36ce527916c2824f35290f9b6f367d3851e8b217`

CI:

`37825433611` — SUCCESS

Verified:
- Backend — SUCCESS
- Frontend — SUCCESS
- Live OIDC E2E — SUCCESS
- Human Seed Learning Approval Bridge acceptance — SUCCESS
- exact Seed artifact SHA-256 — PASS
- Human approval — PASS
- exact retry idempotency — PASS
- Outbox → NATS → existing Dataset Builder — PASS
- ephemeral acceptance Dataset Version 1 — created successfully
- Training started — NO
- Runtime activation — NO

The Dataset Version 1 above is CI acceptance evidence in an ephemeral test database. It is **not** a real Academy-environment learning approval or persistent product Dataset.

## Next AI-data step

The next product operation is a real authenticated Academy Admin review and approval of the exact Seed digest in the target environment.

Only after that explicit Human action may the existing Dataset Builder create that organization context's first persistent Decision-Making Dataset Version.

After real Academy activity exists, future enrichment remains:

**reviewed + policy-eligible + explicitly AI-learning-approved source**
→ **Automatic Dataset Builder**
→ **new immutable Dataset Version**

Raw classroom activity remains forbidden from direct Training ingestion.

## P23-10: human Seed approval UI — Code/CI verified (2026-10-09)

- An Academy-Admin-only `SeedLearningApprovalWorkspace` is mounted beside the existing **read-only** AI Governance workspace, using the real signed-in organization and person.
- The existing preview API is the source of truth for exact Seed v1 identity, policy, content count, SHA-256, and current Human approval status. The Admin must explicitly review the original source content and confirm the *full* displayed SHA-256 with a separately recorded approval reference.
- The form fails closed on invalid source identity/purpose/digest, missing Human acknowledgement, rejected API responses, and changed preview digest/version. The backend revalidates the digest and authenticated ACADEMY_ADMIN authority and appends the domain event/outbox entry in the same transaction.
- The UI **does not** directly create a Dataset Version or start Training; approval merely authorizes the existing `ai.learning_input_approved.v1` → Outbox → NATS → automatic Dataset Builder path. A receipt from the approval API means the event was recorded, **not** that the first persistent Dataset Version exists.
- Frontend tests and live Keycloak/OIDC Browser E2E cover exact preview and administrator/Assessor role isolation. The browser acceptance does **not** press the Human approval button or impersonate a real independent Academy approval.
- Implementation HEAD `4c63a18fc3bc9e6a393f23f67832109438b26f3c`; [CI #37925534341](https://github.com/mahdimarzooghi4-debug/flag-academy/actions/runs/37925534341) **SUCCESS**. Scoped technical review: `docs/reviews/27-sprint-23-seed-learning-admin-ui-code-review.md`.
- **Remaining real gate:** in an actual Academy target environment, a logged-in Academy Admin must review the exact fixed 24-item Seed and deliberately approve its digest, then verify an immutable Dataset Version exists from the live governed builder. Neither real approval nor persistent Dataset creation occurred during this implementation.

