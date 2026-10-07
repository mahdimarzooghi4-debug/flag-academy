# P22-04 — Model Registry + Artifact Attestation

**Status:** IMPLEMENTED — acceptance requires green CI on this record  
**Date:** 2026-10-07  
**Sprint:** 22 — Parcham AI Foundation  
**PR:** #20 — Draft/Open/Unmerged

## Goal

Close the immutable lineage from a successful Training Run to an attested Model Version
without introducing external model registration, hosted providers, runtime inference, or
automatic Production activation.

The governed chain is now:

**Governed Dataset Version → SUCCEEDED Training Run → Model Artifact → Live Artifact
Attestation → Immutable Model Version**

## Registration contract

The Model Registry accepts only organization context, Model Artifact ID, semantic version,
accountable actor type/reference, and trace ID.

The caller cannot supply Training Run ID, Dataset Version ID, model family, artifact
reference, artifact digest, or artifact byte size. Those facts are derived from immutable
AI control-plane records.

## Lineage validation

Registration joins the exact ModelArtifact → TrainingRun → DatasetVersion → Dataset
lineage and requires both Training Run and Dataset ownership to match the requested
organization context. The latest Training Run state must be exactly SUCCEEDED.

The created Model Version pins the exact Model Artifact, Training Run, Dataset Version,
model family, semantic version, attested SHA-256, attested byte size, attestation
timestamp, and creation timestamp.

No arbitrary external model registration path is added.

## Artifact attestation

P22-04 introduces an internal ArtifactReader contract and a concrete local-file reader
used by CI. The local reader accepts only local filesystem references, rejects remote URI
references, streams the artifact in chunks, recomputes SHA-256 from actual bytes, and
recomputes exact byte size.

Registration fails closed with AI_MODEL_ARTIFACT_ATTESTATION_FAILED if observed content
does not exactly match the immutable Model Artifact metadata.

The Registry itself contains no HTTP/S3/provider client and no endpoint/token concept.
A future private artifact-store adapter may implement the same internal reader contract
without changing Model Registry governance.

## Idempotency

One Model Artifact may produce at most one Model Version. Retry with the same artifact
and the same semantic version returns the existing Model Version after live
re-attestation. Retry of the same artifact under a different semantic version fails
closed. Reuse of the same model_family + semantic_version by another artifact also
fails closed.

Because re-attestation occurs before idempotent return, mutation of artifact bytes after
registration is detected rather than silently accepted.

## Database enforcement

Migration 0027 adds immutable attestation evidence to Model Version:

- attestation_sha256;
- attestation_byte_size;
- attested_at.

It deliberately refuses to migrate pre-existing unattested Model Versions rather than
inventing attestation evidence.

PostgreSQL independently checks every new Model Version against an existing Model
Artifact, the artifact's exact Training Run, latest state SUCCEEDED, exact Dataset
Version and model family from that Training Run, and exact artifact SHA-256 and byte
size. This is enforced by ai_control_plane.require_valid_model_version_lineage().

Model Version rows remain protected by the existing immutable UPDATE/DELETE trigger.

## Event

Successful first registration records ai.model_version_registered.v1 as Domain Event +
transactional Outbox in the caller transaction. The event contains lineage and
attestation facts but performs no runtime activation.

## CI acceptance

CI executes backend/scripts/ai_model_registry_acceptance.py after the Dataset Builder and
Training Control Plane acceptance steps.

The acceptance uses a real local artifact file and proves SHA-256 and byte size are
recomputed from bytes, Model Version lineage points to the successful Training Run,
first registration creates exactly one Model Version, exact retry is idempotent,
modifying artifact bytes causes registration retry to fail closed, and the registration
event is written.

## Explicit exclusions

P22-04 does not add OpenAI, Anthropic, hosted model APIs, external training or inference
endpoints, external model registry endpoints, S3/provider credentials, Gemma runtime,
Transformers, PyTorch, PEFT, LoRA, safetensors runtime, Offline Evaluation, automatic
thresholds, automatic promotion, Production activation, Gate/Profile/Responsibility/
Appointment mutation, or a public HTTP Model Registry write API.

## Result

When CI is green on this record, **P22-04 — Model Registry + Artifact Attestation is
COMPLETE**.

The next planned slice is **P22-05 — Offline Evaluation**.
