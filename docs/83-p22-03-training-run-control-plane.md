# P22-03 — Training Run Control Plane

**Status:** IMPLEMENTED — acceptance requires green CI on this record  
**Date:** 2026-10-07  
**Sprint:** 22 — Parcham AI Foundation  
**PR:** #20 — Draft/Open/Unmerged

## Goal

Implement the governed Training Run lifecycle on top of exact immutable Dataset Versions
created by P22-02, without adding an external trainer, model runtime, or automatic model
promotion.

The lifecycle is exactly:

**REQUESTED → RUNNING → SUCCEEDED / FAILED**

Training Run headers and lifecycle history remain immutable. State changes are append-only
rows in `training_run_states`.

## Request contract

A Training Run pins:

- organization context;
- exact immutable Dataset Version;
- request key;
- model family identifier;
- training recipe SHA-256 digest;
- requester actor type/reference;
- data classification;
- request timestamp.

Request identity is tenant scoped by:

`organization_context_id + request_key`

The same request key with the same semantic request is idempotent. Reuse with different
Dataset Version, model family, recipe digest, requester, or classification fails closed
with `AI_TRAINING_REQUEST_KEY_REUSED`.

The exact Dataset Version must belong to the same organization context.

## Concurrency

Request creation is serialized with a PostgreSQL transaction advisory lock over the
tenant-scoped request identity.

Lifecycle transitions are serialized with a PostgreSQL transaction advisory lock derived
from the immutable Training Run ID.

The application service does not commit independently; event, state and artifact changes
remain in the caller's transaction.

## Lifecycle rules

### Start

Only `REQUESTED` may transition to `RUNNING`.

A retry while already `RUNNING` is idempotent.

A terminal Training Run cannot return to `RUNNING`.

### Completion

Only `RUNNING` may complete.

Completion is exactly one of:

- `SUCCEEDED`;
- `FAILED`.

A terminal outcome cannot be changed.

Terminal retries are accepted only when their exact recorded semantics match. A success
retry must match the existing artifact format, reference, SHA-256 and byte size. A failure
retry must match the recorded failure code and must contain no artifact fields.

## Artifact boundary

P22-03 allows a Model Artifact record to be produced only as part of successful Training
completion.

For `SUCCEEDED`:

- artifact format is required;
- artifact reference is required;
- content SHA-256 is required;
- non-negative byte size is required;
- success state is flushed before the artifact row.

For `FAILED`:

- failure code is required;
- artifact fields are forbidden;
- no Model Artifact is created.

PostgreSQL independently enforces this rule with
`ai_control_plane.require_succeeded_training()`: direct insertion of a Model Artifact
for a Training Run whose latest state is not `SUCCEEDED` is rejected.

P22-03 does **not** create a Model Version. Model Registry lineage and stronger artifact
attestation remain P22-04.

## Events

The caller transaction writes Domain Event + Outbox records for:

- `ai.training_run_requested.v1`;
- `ai.training_run_started.v1`;
- `ai.training_run_succeeded.v1`;
- `ai.training_run_failed.v1`.

No event activates a runtime or Production model.

## Explicit exclusions

P22-03 does not add:

- OpenAI, Anthropic, or any hosted model provider;
- external trainer endpoint;
- training API/token/credential;
- Transformers, PyTorch, PEFT, LoRA or safetensors;
- optimizer, learning rate, epoch count, batch size or other invented hyperparameters;
- Gemma runtime;
- Model Version creation;
- Evaluation;
- model selection threshold;
- automatic promotion;
- Production activation;
- Gate/Profile/Responsibility/Appointment mutation;
- public HTTP Training API.

## CI acceptance

CI includes `backend/scripts/ai_training_control_acceptance.py` after the governed
Dataset Builder acceptance.

The acceptance proves on a real PostgreSQL migration chain:

- exact governed Dataset Version can create a Training Run;
- successful lifecycle is `REQUESTED → RUNNING → SUCCEEDED`;
- failed lifecycle is `REQUESTED → RUNNING → FAILED`;
- successful run produces exactly one Model Artifact;
- failed run produces no Model Artifact;
- PostgreSQL rejects a direct Model Artifact insert before success;
- lifecycle events are persisted;
- no external trainer endpoint participates.

## Result

When CI is green on this document commit, **P22-03 — Training Run Control Plane is
COMPLETE**.

The next planned slice is **P22-04 — Model Registry + Artifact Attestation**.
