# 94 — Offline governed Training Dataset content materialization

**Date:** 2026-10-09
**Status:** Internal code foundation only; no real approved dataset, no Trainer run or model activation.

An internal read-only adapter `materialize_training_dataset` accepts an existing tenant-scoped RUNNING TrainingRun and returns bytes for each append-only DatasetVersion ancestor, never arbitrary caller-provided files. It validates tenant, MODEL_TRAINING purpose, full version chain/digests, one-item-per-version builder contract, item/approval lineage, independent original PERSON approval DomainEvent and the source-policy/source SHA-256. The only recognized content source is Parcham's packaged Decision-Making Seed v1, independently compared to the immutable approved digest; unsupported sources fail closed. An approval event is not manufactured or implied by tests.

This allows designing a future offline Trainer while avoiding the false claim that P22 DatasetItem metadata contains training payloads. No new HTTP route, automatic Training start/completion, GPU dependency, external LLM, Dataset approval, Evaluation, Model Version or Promotion is added.

**Current limitations:** The 24 synthetic records remain not human-approved in a real Academy. No operational Dataset V1 exists. This adapter cannot serve future real data until a separately approved, immutable versioned content storage/retrieval contract exists; mixed Dataset Versions containing unsupported sources fail closed. The current builder records one item per version, so this adapter deliberately rejects other layouts rather than inferring new semantics. Approved data bytes are returned in memory, not automatically fed to a model. Filesystem immutability and runtime source integrity remain hosting gates.

**Next:** Pin a fully specified, externally approved versioned training recipe and immutable offline output store; implement Trainer and emit the existing `GEMMA4_CHECKPOINT_MANIFEST_V1` only after a real successful run, without inventing hyperparameters, model revision or hardware.
