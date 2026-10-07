# Sprint 22 — Parcham AI Foundation

**Status:** ACTIVE  
**Parent:** Sprint 21 — Gate Assessment Foundation  
**Base branch:** `sprint-21-gate-assessment-foundation`  
**Working branch:** `sprint-22-parcham-ai-foundation`

## Goal

Build the first production-grade control-plane foundation for **Parcham-owned AI** without introducing an external AI provider, unmanaged learning, or autonomous consequential decisions.

This sprint establishes the governed chain:

**Approved Governed Data → Immutable Dataset Version → Training Run → Model Artifact / Model Version → Offline Evaluation → Human Promotion Decision**

It does **not** yet implement the final Gemma inference runtime.

## Non-negotiable rules

1. Parcham AI is Parcham-owned and self-hosted.
2. No OpenAI, Anthropic, hosted Foundation Model API, external inference endpoint, external training endpoint, or provider token may enter the production architecture.
3. AI may propose, summarize, interpret and assist, but may not directly decide or mutate:
   - Gate PASS / PASS_CONFIRMED / FAIL;
   - CapabilityClaim;
   - ResponsibilityRecommendation;
   - Flag Board decisions;
   - Appointment.
4. Production operational data must not directly change model weights.
5. Only data already approved for AI learning by an explicit governed source/policy may enter an AI Dataset.
6. Missing AI-learning approval must fail closed.
7. Dataset Versions are immutable and append-only.
8. Training must pin an exact immutable Dataset Version.
9. Model artifacts and Model Versions are immutable and content-attested.
10. Evaluation must pin exact Model Version and exact Evaluation Dataset Version.
11. Evaluation results never activate Production by themselves.
12. Model promotion requires an explicit accountable Human decision.
13. This sprint invents no numeric quality threshold, weighted score, fairness threshold, benchmark winner rule, or auto-promotion rule.
14. No AI model family is selected by a score inside this sprint.
15. The future baseline `Gemma 4 12B Unified` remains the intended first runtime candidate, but concrete runtime/training implementation is a later slice after these governance contracts exist.

## Bounded context

Sprint 22 introduces an independent `ai_control_plane` bounded context.

It owns:

- AI Dataset;
- Dataset Version;
- Dataset Item provenance;
- Model Artifact;
- Model Version;
- Training Run;
- Evaluation Run;
- Human Promotion Decision.

It must not own or mutate operational Evidence, Pattern, Flag Profile, Gate Assessment, Responsibility or Appointment persistence.

Cross-context source IDs are recorded as opaque provenance references, never cross-context foreign keys.

## Dataset contract

A Dataset Version must contain:

- immutable identity/version;
- purpose;
- source policy/version reference;
- creation timestamp;
- immutable ordered/set item membership;
- source type;
- source aggregate/reference ID;
- source version/reference version when available;
- source event or approval reference;
- data classification;
- provenance digest;
- dataset digest.

The Dataset Builder must be deterministic and idempotent for the same approved source set.

No raw unapproved record may be inserted through a generic public Dataset API.

## Training contract

A Training Run must pin:

- exact Dataset Version;
- model family identifier;
- training recipe/config digest;
- requested_by Human/System governance context;
- lifecycle state;
- immutable run lineage;
- produced artifact only after successful completion.

Initial lifecycle vocabulary:

**REQUESTED → RUNNING → SUCCEEDED / FAILED**

A failed Training Run creates no Model Version.

This sprint does not define a specific optimizer, learning rate, LoRA rank, epoch count, batch size, or numeric training threshold.

## Model registry contract

A Model Artifact must be immutable and content-addressed.

A Model Version must pin:

- Model Artifact;
- model family identifier;
- originating successful Training Run;
- originating Dataset Version;
- immutable semantic/version identifier;
- creation timestamp;
- lifecycle state.

No Model Version may be registered from an arbitrary external endpoint or provider token.

## Evaluation contract

An Evaluation Run must pin:

- exact Model Version;
- exact Evaluation Dataset Version;
- evaluation policy/version reference;
- immutable metrics payload/artifact reference;
- lifecycle state;
- started/completed timestamps.

Initial lifecycle vocabulary:

**REQUESTED → RUNNING → SUCCEEDED / FAILED**

Sprint 22 records evaluation evidence but defines no automatic pass threshold.

## Promotion contract

Promotion is a separate Human-governed command.

A Promotion Decision must pin:

- exact Model Version;
- exact successful Evaluation Run;
- reviewer;
- rationale;
- decision timestamp;
- target environment;
- prior active model version if any.

Initial decision vocabulary:

**APPROVED / REJECTED**

`APPROVED` records authorization only. Runtime activation is not part of the first persistence slice and may not be inferred from an Evaluation result.

## Planned slices

### P22-01 — AI Control Plane Vocabulary + Immutable Registry Foundation
- enums/vocabulary;
- relational persistence;
- immutable Dataset/Model/Training/Evaluation/Promotion records;
- no API;
- no worker;
- no training;
- no inference.

### P22-02 — Governed Dataset Builder
- consume only explicitly approved learning inputs;
- idempotent dataset item ingestion;
- immutable Dataset Version creation;
- provenance + digest;
- no manual arbitrary record upload.

### P22-03 — Training Run Control Plane
- Training Run lifecycle;
- exact Dataset Version pinning;
- artifact creation only after success;
- no external trainer endpoint.

### P22-04 — Model Registry + Artifact Attestation — COMPLETE
- immutable artifact identity;
- SHA-256 attestation;
- Model Version lineage;
- no arbitrary external model registration.

### P22-05 — Offline Evaluation — COMPLETE
- exact Model Version + independent Evaluation Dataset Version;
- tenant-scoped idempotent lifecycle;
- immutable live-attested evaluation evidence;
- DB-enforced Training/Evaluation Dataset Version separation;
- no auto-pass policy, auto-promotion, or runtime activation.

Completion evidence: CI run `37625122783` succeeded on implementation HEAD
`4c1af52e6fdfd0a28a2e13e2ab1bcd3764cbaf95`.

### P22-06 — Human Promotion Governance
- explicit Human decision;
- rationale;
- exact version pins;
- no automatic Production activation.

### P22-07 — Admin Read Models / UI
- lineage and governance visibility;
- no secret/provider credential surface.

### P22-08 — Stage Acceptance + Code Review

## Explicit exclusions

- final Gemma runtime;
- online inference;
- LoRA/PEFT training implementation;
- safetensors packaging/loading;
- automatic Production runtime activation;
- AI Mentor/Tutor/Simulation runtime;
- AI-generated Gate decisions;
- Responsibility matching activation;
- external AI providers;
- numeric quality thresholds;
- model benchmark winner selection;
- Production deployment.

## Acceptance

Sprint 22 is accepted only when:

- all AI control-plane records are versioned/immutable;
- no external AI endpoint/provider concept exists;
- Dataset membership is provenance-preserving and approval-gated;
- Training cannot run without exact Dataset Version;
- Model Version cannot exist without a successful Training Run/artifact;
- Evaluation cannot activate Production;
- Human Promotion is explicit and auditable;
- no Gate/Profile/Responsibility mutation exists;
- CI and Stage Acceptance are green;
- Code Review records no blocking finding.
