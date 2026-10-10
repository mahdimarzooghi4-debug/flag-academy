# 92 — Offline Gemma 4 12B Local Execution Adapter — technical preflight

**Date:** 2026-10-09
**Status:** Code + tests verified, **NOT a Production AI runtime**, Training Engine or trained model.
**Baseline:** Approved first candidate **Gemma 4 12B Unified** (DEC-617–623); system remains Parcham-owned and fully internal.
**Implementation:** `backend/app/ai_control_plane/local_gemma.py`, tests `backend/tests/test_ai_local_gemma.py`.
**Reviewed code HEAD:** `683c426beed24708daf6b9f965ccc60c03b716dd`
**Exact-head CI:** [37939193485](https://github.com/mahdimarzooghi4-debug/flag-academy/actions/runs/37939193485) — **SUCCESS** (Backend, Frontend, OIDC Browser E2E + AI governance regression).

## Boundary and invariants

- This **offline infrastructure-only adapter** provides `OfflineGemmaCheckpoint`, `CheckpointFile`, `attest_offline_checkpoint`, `ExplicitTextGeneration`, `TransformersLocalGemmaBackend` and `generate_offline_text`. It is deliberately **not included in FastAPI routes**, not wired to Academy Tutor/Instructor/Assessor, not a Training worker and never invoked as a side effect of Dataset creation or Human Promotion.
- Every attempt to invoke this low-level path requires an exact, existing private **absolute local checkpoint directory** rather than a repository name/URL/cloud endpoint. No symlinks, noncanonical path traversal, missing or extra files, unpinned digest/size, unsafe executable or pickle formats. Manifest requires config, local tokenizer, and safetensors. Every file is hashed with SHA-256 and checked against an externally supplied expected manifest; a content-manifest digest also pins the supplied 40-hex upstream revision. UUIDs for model and Training Dataset lineage must be nonzero.
- The **expected manifest is not a source of truth by itself**: it must eventually come from an independently trusted immutable model-artifact record and versioned checkpoint evidence. Regex validation of revision is *not proof* of its origin. Current code does not query the Model Registry, Evaluation, Promotion or artifact store. A **read-only private checkpoint mount** and trustworthy manifest provisioning are operational prerequisites, not assumptions established by local unit tests.
- The optional local-only loader uses `AutoProcessor` + `AutoModelForMultimodalLM` and sets `local_files_only=True`, `trust_remote_code=False` and `use_safetensors=True`. This is a prospective text-only interface over the Gemma Unified multimodal architecture; other modalities have no Parcham contract. `torch` and `transformers` are optional runtime-only dependencies and are **not** installed as default application/API dependencies; absence fails closed.
- No GPU, CPU, memory, revision, concrete checkpoint digest, dependency matrix, precision, quantization, device placement or generation hyperparameter is selected by this slice. Deployment must provide a benchmarked `device_map` and a deliberate generation `max_new_tokens` and `do_sample`. No arbitrary default generation settings are invented.
- Prompt ingestion has **no** end-user input path in this slice. Before real AI invocation, an owning application-level role/purpose/mode/class policy, data-classification redaction, approved Knowledge retrieval, output safety validation, versioned audit and explicitly promoted environment model must be integrated. Therefore this adapter is **not permitted for live Candidate, Instructor, Assessor or Admin AI requests**.
- There is no external AI API, OpenAI dependency, external inference service, custom AI endpoint/token, model download, direct model weight update, hidden automatic Dataset learning, or Production change. The existing Training → independent Evaluation → Human Promotion governance remains intact and separate.

## Tests and known limits

- New tests verify exact digest, version/dataset lineage pinning, deterministic manifest, changed revision, tampered/missing/extra/unlisted weights, invalid and duplicate entries, symlink denial, missing generation input/limits, fail-closed missing local backend, denial of unusable output, and re-attestation before every injected test-backend invocation. Test safetensors bytes are intentionally **fake fixtures**; no claim of GPU model execution.
- Existing Sprint 22 no-runtime foundation test is preserved for its original modules and explicitly excludes the newly isolated `local_gemma.py`; the new adapter test asserts there is **still no public inference or training API**.
- **Remaining real acceptance:** actual read-only local Gemma checkpoint + trusted SHA-256 manifest; complete runtime dependency version pins; GPU/resource sizing and a benchmark; live offline text-generation smoke; ModelVersion/Evaluation/Human Promotion + routing policy admission, audited role-scoped Tutor mode and data safety; non-mock real model tests. These are not green merely because the stub-backend unit tests and unrelated OIDC regressions passed.
- **TOCTOU boundary:** preflight hashes before local model loading and the checkpoint must be immutable/read-only across both operations. The application code cannot prove mount immutability by checking file metadata; host/storage attestation is required.
- **Training is still separate:** no LoRA/PEFT trainer, Dataset preparation or evaluation runner for Gemma has been built here. No model was trained, approved, promoted, activated or deployed in this slice.

## Workflow

This slice follows Business → Technical → Code/Tests → CI → scoped technical Code Review. Stage/QA Gate/Release/Production and independent human PR review are blocked until separately authorized. PR #21 remains Draft/Open/Unmerged, stacked on Sprint 22; no merge or deployment was performed.

**Next safe step:** connect an independently owned *versioned* checkpoint-artifact manifest to the offline adapter, then add an isolated training-adapter contract pinned to a real APPROVED Dataset Version, without picking LoRA settings, hardware or activating Production. No new model training is possible without actual approved data and local runtime assets.
