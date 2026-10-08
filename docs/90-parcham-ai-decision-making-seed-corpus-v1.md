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

## Next implementation contract

To move from repository Seed artifact to real Dataset creation, the next AI-data sub-slice must add a governed **Seed Learning Approval Bridge** that:

1. reads/pins an exact approved Seed artifact/version;
2. computes and records the exact source payload SHA-256;
3. requires an explicit accountable Human AI-learning approval;
4. emits/records the existing governed learning-source approval input expected by the Automatic Dataset Builder;
5. cannot bypass Dataset Builder provenance/idempotency;
6. cannot start Training by itself.

The exact API/UI shape for that approval is not defined by this document.
