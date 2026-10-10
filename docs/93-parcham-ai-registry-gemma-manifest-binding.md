# 93 — Offline Gemma Checkpoint Binding to Governed Model Registry

**Date:** 2026-10-09  
**Status:** Backend preflight implementation and contract tests; NOT an approved Training Engine, usable inference or Production model.  
**Reviewed code SHA:** 1954db0054cd7950ea563847395dd61c54ca84d2  
**Code CI:** https://github.com/mahdimarzooghi4-debug/flag-academy/actions/runs/37942872782 — SUCCESS Backend, Frontend, E2E.

## Authoritative lineage

The existing append-only AIModelVersion → AIModelArtifact → SUCCEEDED AITrainingRun → AIDatasetVersion → AIDataset is the only model provenance. The read-only preflight resolves ModelVersion by exact UUID and constrains both the Training Run and Dataset to the supplied organization. It also checks all relevant foreign-key lineage identities in memory, model family and attestation metadata. It does not create or alter Model Versions or Training Runs.

The registered artifact format GEMMA4_CHECKPOINT_MANIFEST_V1 is a future Trainer output contract. It is a local UTF-8 JSON manifest whose digest and byte length are attested through both the AIModelArtifact record and immutable AIModelVersion record. Registry registration still uses its existing independent artifact reader. There is no second manual registry or external model provider.

Exact JSON v1 fields:

- schema_version: integer 1 (not boolean)
- training_run_id: string equal to registered Training Run UUID
- training_dataset_version_id: string equal to registered Training Run Dataset Version UUID
- model_family: Gemma 4 12B Unified
- checkpoint_revision: 40 lowercase hexadecimal characters (syntactic validation does not establish the upstream provenance)
- files: nonempty list of objects with exactly path (string), sha256 (string) and byte_size (integer)

Additional fields, duplicate JSON keys, unsupported format, missing data, 1 MiB overflow, more than 4096 file records, or any registry digest/size mismatch fail closed. The existing checkpoint attestor then verifies the relative file paths, private absolute canonical mount, no symlinks, exact inventory, SHA-256/size, tokenizer and safetensors presence.

Private checkpoint_directory is provided by the trusted host and is never accepted from registered JSON. Both the manifest and weights must be provisioned on immutable, private read-only storage. Rehashing cannot prevent a privileged host from mutating files between preflight and model loading; such operational attestation remains an external gate.

## Read-only API boundary

The internal function attest_registered_offline_checkpoint(db, organization_context_id, model_version_id, checkpoint_directory) only returns process-local AttestedGemmaCheckpoint after fresh registry and filesystem checks. It does not authorize inference, run a Trainer, select a runtime model, use the evaluation result, promote a version or expose any HTTP route. Human dataset approval, independent Evaluation, model promotion and a role/purpose-specific AI Tutor safety contract are separate prerequisites.

## Test scope and exclusions

Offline tests use deliberately false model-weight bytes and a stub database result. Coverage includes good lineage, changed registered manifest bytes, tampering, substituted registry attestation, mismatched training dataset, duplicate keys, invalid field types, unknown fields, symlink denial, absent/non-SUCCEEDED training state and absence of new public inference APIs. Existing full Backend/Frontend/real OIDC E2E pipelines remain green. These tests do NOT establish a real approved Dataset Version 1, a registered Gemma artifact from real Trainer execution, a genuine checkpoint, GPU compatibility, actual text-generation quality, a PostgreSQL live integration specifically for this new read-only query, or Production readiness.

**Next permitted code slice:** build an internal Trainer adapter that consumes only approved and versioned Training Dataset contents under a separately governed recipe, then emits an immutable attested manifest artifact through the existing TrainingRun workflow. No arbitrary hyperparameters, hardware assumptions, endpoint/token, real training claim, merge, Stage or Production.
