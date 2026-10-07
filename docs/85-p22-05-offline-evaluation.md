# P22-05 — Offline Evaluation

**Status:** IMPLEMENTED — acceptance requires green CI on this record  
**Date:** 2026-10-07  
**Sprint:** 22 — Parcham AI Foundation  
**PR:** #20 — Draft/Open/Unmerged

## Goal

Extend the existing Parcham-owned AI control plane with governed Offline Evaluation:

**Immutable Model Version + Independent Immutable Evaluation Dataset Version +
Pinned Evaluation Policy → Offline Evaluation Run → Immutable Attested Evaluation Result**

This slice records evidence only. It defines no automatic quality threshold, winner
selection, promotion, runtime activation, Gate decision, Profile mutation, Responsibility
mutation, Flag Board decision, or Appointment action.

## Evaluation request contract

An Evaluation Run pins:

- organization context;
- deterministic request key;
- exact Model Version;
- exact Evaluation Dataset Version;
- exact evaluation policy key and version;
- requesting governance actor;
- data classification;
- request timestamp.

Model training lineage is derived from the immutable Model Version and Training Run.
The caller cannot supply Training Run ID, Training Dataset Version, model family, model
artifact identity, model artifact digest, or model artifact byte size.

The Model Version and Evaluation Dataset Version must both belong to the requested
organization context.

## Training and evaluation data separation

The exact Dataset Version used to train the Model Version is forbidden as the Evaluation
Dataset Version.

P22-05 intentionally does not invent household-overlap, sample-overlap, semantic-overlap,
or percentage thresholds because no authoritative product contract defines them yet.

PostgreSQL independently enforces tenant ownership and exact Training/Evaluation Dataset
Version separation for every Evaluation Run insert.

## Lifecycle

Evaluation lifecycle is append-only:

**REQUESTED → RUNNING → SUCCEEDED / FAILED**

Only REQUESTED may enter RUNNING. Only RUNNING may enter a terminal state. Terminal
outcomes cannot change.

Exact retries are idempotent. The request identity is:

`organization_context_id + request_key`

Reuse of the same request key with different semantics fails closed. PostgreSQL advisory
transaction locks serialize both request creation and per-run transitions across replicas.

## Evaluation Result attestation

A successful Evaluation Run requires a metrics/result artifact. P22-05 persists:

- artifact reference;
- recomputed SHA-256 digest;
- recomputed byte size;
- attestation timestamp;
- creation timestamp.

The local CI reader accepts only local filesystem references, reads bytes in chunks, and
recomputes SHA-256 and exact byte size from the artifact itself.

Caller-supplied digest and byte size are treated only as expected metadata and are never
trusted without byte-level recomputation. Mismatch fails closed.

An exact retry of successful completion re-attests the artifact before returning the
existing result, so mutation after the first successful evaluation is detected.

A failed Evaluation Run cannot produce Evaluation Result evidence.

## Database enforcement

Migration `0028_offline_evaluation_control_plane.py`:

- adds organization context, request key, and data classification to Evaluation Run;
- adds the unique request identity;
- adds result byte size and attestation timestamp;
- refuses to harden pre-existing Evaluation Runs rather than inventing lineage;
- enforces Model Version and Evaluation Dataset tenant ownership;
- enforces exact Training/Evaluation Dataset Version separation;
- requires latest Evaluation state `SUCCEEDED` before Evaluation Result insert.

Existing immutable UPDATE/DELETE triggers continue to protect Evaluation Run, state, and
result history.

## Events and outbox

Lifecycle changes record Domain Event + transactional Outbox entries:

- `ai.evaluation_run_requested.v1`
- `ai.evaluation_run_started.v1`
- `ai.evaluation_run_succeeded.v1`
- `ai.evaluation_run_failed.v1`

Event payloads preserve exact Model Version, derived Training Dataset Version, Evaluation
Dataset Version, policy key/version, and terminal evidence or failure code.

No event in this slice activates a runtime or creates a Human Promotion Decision.

## CI acceptance

CI runs `backend/scripts/ai_offline_evaluation_acceptance.py` after Model Registry
acceptance.

The acceptance uses a governed independent Evaluation Dataset and a real filesystem
metrics artifact. It proves:

- exact Model Version lineage;
- exact independent Evaluation Dataset Version;
- request idempotency;
- REQUESTED → RUNNING → SUCCEEDED;
- REQUESTED → RUNNING → FAILED;
- successful result uniqueness;
- failed run has no result;
- result SHA-256 recomputation;
- result byte-size recomputation;
- tamper detection on retry;
- database rejection of premature result insertion;
- rejection of the Training Dataset Version as Evaluation Dataset;
- lifecycle outbox evidence.

## Explicit exclusions

P22-05 adds no OpenAI, Anthropic, external model API, external inference endpoint,
external evaluation endpoint, provider token, public Evaluation write API, Gemma runtime,
Transformers, PyTorch, PEFT, LoRA, safetensors runtime, optimizer, learning rate, batch
size, epoch count, numeric pass threshold, weighted score, fairness threshold, benchmark
winner rule, automatic pass/fail policy, automatic promotion, Production activation,
Gate/Profile/Responsibility/Appointment mutation, or deployment.

## Result

When full CI is green on this implementation, **P22-05 — Offline Evaluation is
COMPLETE**.

The next planned slice is **P22-06 — Human Promotion Governance**.
