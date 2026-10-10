# Sprint 23 — Scoped technical Code Review: governed offline Training content

**Date:** 2026-10-09
**Reviewed code HEAD:** `05817d76577be394465301fc4a29fca8211c7808`
**Exact-head CI:** https://github.com/mahdimarzooghi4-debug/flag-academy/actions/runs/37945110867 — Backend, Frontend, E2E SUCCESS.
**Verdict:** Scoped technical self-review ACCEPTED for the read-only, first-party synthetic Seed content materialization foundation. NOT independent Human Code Review, Trainer acceptance, Stage, Production, or Dataset approval.

## Reviewed

- `backend/app/ai_control_plane/training_content.py`
- `backend/tests/test_ai_training_content.py`
- `docs/94-parcham-ai-governed-training-content.md`

## Findings

1. The method consumes only an existing tenant-scoped RUNNING TrainingRun and MODEL_TRAINING Dataset, pinned by exact UUID. It cannot start, complete or auto-promote a run and does not add a route.
2. Dataset ancestry is checked from the requested version to its initial parent, with cycle/size defenses, strict contiguous version numbers, existing builder's one-item delta layout and recomputed immutable digests.
3. Each item must match its stored approval. The original tenant-scoped DomainEvent must have PERSON actor identity, the canonical Seed approval aggregate, matching payload metadata, classification, approval reference and timestamp. No test or operator is treated as proof of real Human approval.
4. The only supported content resolver is the packaged canonical Decision-Making Seed v1, with complete known source identity and SHA-256 verified against approved bytes. Unknown future content types and changed package contents fail closed.
5. Contract tests cover happy-path in-memory source bytes and negative lineage/policy/event/source access. Ruff, Pyright, Backend, Frontend and live OIDC E2E CI are green after fixing unused import and fixture-only type annotations.
6. The adapter is deliberately read-only and emits neither Training artifact nor Model Version. It does not invoke torch, a model, any external AI endpoint, or Promotion.

## Residuals and explicit blocked gates

- The new DB read path is tested with session stubs. A targeted live PostgreSQL tenant isolation/ancestry test remains open; existing CI's OIDC E2E does not prove this particular new query end-to-end.
- P22 persisted DatasetItems hold approvals and provenance, not independently stored generic source bytes. Source retrieval for approved *real* Academy content needs its own immutable storage, authorization, versioning and access contract; unsupported items fail closed.
- Packaged source integrity is checked when materialized, but runtime host image immutability and the handoff boundary to a future Trainer are separate controls. No checkpoint, GPU training, real Dataset Version 1, independent Evaluation or Tutor authorization is demonstrated.
- Training recipe, base checkpoint revision, hyperparameters, model optimization, output immutability and executable Trainer remain future governed work. No defaults are asserted.
- The 24-sample Seed still needs real accountable approval in the Academy; CI fixtures must never be presented as authorization.
- PR #21 remains Draft/Open/Unmerged. Dependent Sprint PRs remain unmerged; independent Human Review, Stage, QA Gate, Release and Production were neither executed nor authorized.
