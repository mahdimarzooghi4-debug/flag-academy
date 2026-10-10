# Sprint 23 — Scoped Code Review: Model Registry → Offline Gemma

**Date:** 2026-10-09  
**Reviewed code SHA:** 1954db0054cd7950ea563847395dd61c54ca84d2  
**Exact-head CI:** https://github.com/mahdimarzooghi4-debug/flag-academy/actions/runs/37942872782 — SUCCESS (Backend, Frontend, live OIDC E2E).  
**Verdict:** Scoped technical self-review ACCEPTED for the read-only, offline registry-manifest preflight only. This is not independent human review, Training acceptance, real-model runtime admission, Stage acceptance or a Production approval.

## Reviewed files

- backend/app/ai_control_plane/local_gemma.py — DB-scoped immutable lineage, strict JSON manifest parsing, registered SHA/size checks, existing local checkpoint attestation. No database write, AI endpoint, GPU loader invocation or model auto-promotion from this new path.
- backend/tests/test_ai_local_gemma.py — successful bridge fixture and negative cases for tamper, format, structural type, registry substitution and Training state; static assertion of tenant-scoped selection.
- docs/93-parcham-ai-registry-gemma-manifest-binding.md — trust assumptions and explicit missing real-world acceptance gates.

## Findings and controls

1. **Registry authority, not caller-supplied manifest:** the checkpoint manifest is read only from registered AIModelArtifact bytes, pinned to AIModelVersion attestation and immutable SUCCEEDED Training Run lineage. Arbitrary caller-supplied expected hashes cannot replace the authoritative artifact in this new entry point.
2. **Organization boundary:** both AITrainingRun and AIDataset are filtered by organization_context_id. The backend entry point remains internal, with no new route. The mock-database tests do not replace an eventual live PostgreSQL tenant-isolation test.
3. **Strict manifest parsing:** bounded file size and record count, duplicate-key rejection, exact fields, revision syntax, digest and byte-size check, no remote artifact reference or symlinked/canonical path bypass. The offline attestor also validates all checkpoint bytes and file types.
4. **No autonomous activation:** SUCCEEDED Training is a provenance gate but NOT permission for Tutor execution. Explicit Evaluation, Human Promotion, approved Knowledge retrieval, scoped prompt/output safety, and runtime authorization remain blocked requirements.
5. **Residual TOCTOU:** file-stat and SHA checks are not a substitute for a truly immutable read-only host mount. The host must attest it and later confirm it remains unchanged across model loading. Local tests do not establish such a mount.
6. **Honest model readiness:** fake safetensors bytes and stub DB records are only contract fixtures. No real Gemma checkpoint, actual Trainer, GPU run, model benchmark, approved synthetic seed or Production model is claimed.
7. **CI remediation:** two short lint corrections (import ordering and missed qualified private helper), and explicit type casts of testing-only stubs for Pyright, were fixed. Exact-head full CI subsequently succeeded.

**Independent gate still open:** PR #21 is Draft/Open/Unmerged, with dependent PR #19 and #20 also unmerged. Human Code Review sign-off, Stage, QA Gate, Release and Production are not requested or authorized.
