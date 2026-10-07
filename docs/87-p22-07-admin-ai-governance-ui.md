# P22-07 — Admin AI Governance Read Model / UI

**Status:** ACTIVE  
**Date:** 2026-10-07  
**Sprint:** 22 — Parcham AI Foundation  
**PR:** #20 — Draft/Open/Unmerged

## Goal

Expose the governed AI control-plane lineage to Academy Admins as a read-only product surface:

**Dataset Version → Training Run → Model Version → Offline Evaluation → Human Promotion Decision**

The UI is an audit and governance workspace. It does not perform training, evaluation,
promotion, runtime activation, routing, deployment, Gate decisions, Profile mutation,
Responsibility mutation, Flag Board actions, or Appointment actions.

## Backend read contract

P22-07 adds:

`GET /api/v1/admin/ai/governance`

The endpoint:

- requires `ACADEMY_ADMIN`;
- is tenant-scoped to the authenticated organization context;
- is GET-only;
- reads the existing immutable AI control-plane records;
- exposes no mutation command.

The read model returns:

- immutable Dataset Versions and item counts;
- Training Runs and their latest lifecycle state;
- produced Model Artifact identity and Model Version identity where present;
- attested Model Version metadata;
- Evaluation Runs, latest state, policy/version, and attested result digest/size;
- Human Promotion Decisions and exact reviewer/rationale/target lineage.

## Secret and infrastructure boundary

The admin read model intentionally does not expose:

- model artifact storage reference/path;
- evaluation metrics artifact storage reference/path;
- provider credentials;
- provider token;
- API key;
- inference endpoint;
- training endpoint;
- storage credentials;
- secret values.

Artifact identity, SHA-256 and byte size are sufficient for governance visibility.

## UI

The Academy Admin receives a new `AIGovernanceWorkspace` in the existing Persian RTL
frontend.

The workspace includes:

- governance summary metrics;
- five-stage lineage view;
- Dataset Version cards;
- Training Run cards;
- Model Registry attestation table;
- Offline Evaluation evidence cards;
- Human Promotion Decision cards.

Every Promotion Decision explicitly states that the authorization record does not activate
runtime.

The surface contains no mutation buttons and no provider/credential controls.

## Acceptance

P22-07 acceptance must prove:

- admin route is GET-only;
- Academy Admin role is required;
- organization context scopes every control-plane source;
- Dataset → Training → Model → Evaluation → Promotion lineage is preserved;
- SUCCEEDED Evaluation result evidence is visible through digest/size only;
- no artifact location or credential field is present in the read response;
- UI renders the governance boundary;
- UI contains no runtime activation control;
- backend, frontend, browser E2E and read-model acceptance are green.

## Explicit exclusions

- runtime activation;
- model deployment;
- active-model pointer;
- routing policy;
- training/evaluation mutation UI;
- promotion mutation UI;
- external AI provider settings;
- API keys/tokens/endpoints;
- final Gemma runtime;
- Stage Acceptance / Code Review completion (P22-08).

## Next

After green CI and completion recording, the next slice is:

**P22-08 — Stage Acceptance + Code Review**
