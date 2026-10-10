# Scoped technical Code Review — Gemma 4 12B offline adapter

**Date:** 2026-10-09
**Code reviewed at:** `683c426beed24708daf6b9f965ccc60c03b716dd`
**Exact code CI:** [37939193485](https://github.com/mahdimarzooghi4-debug/flag-academy/actions/runs/37939193485) — SUCCESS Backend, Frontend, live OIDC E2E.
**Verdict:** The low-level **off-network attestation and local text adapter** passes bounded tests. **NOT accepted** as working Gemma inference on a real checkpoint, AI Tutor, Gemma Training implementation, Human promotion, independent PR sign-off, Stage or Production.

## Files reviewed

- `backend/app/ai_control_plane/local_gemma.py`: requires pinned model family, model/dataset identity and checkpoint revision; refuses network locations/relative paths, symlinks, unsafe/extra/missing files and any digest/size mismatch; local-only Transformers adapter has no public route.
- `backend/tests/test_ai_local_gemma.py`: proves fail-closed on malformed or changed manifest, optional missing runtime dependencies, explicit generation limits and fake-backend contract execution only; fake weights cannot validate model compatibility.
- `backend/tests/test_ai_control_plane.py`: keeps prior Sprint 22 governance foundation free of model execution and allows only the **separate** prospective `local_gemma.py` adapter while enforcing that no new FastAPI model runtime endpoint exists.
- `docs/92-parcham-ai-offline-gemma-preflight.md`: covers operational and missing real-model acceptance gates.

## Findings / mitigations

1. **No outward AI transport:** verified code contains no URL, Provider SDK or external-inference endpoint; `local_files_only`, `trust_remote_code=False`, `use_safetensors=True` are explicit. Model dependencies load lazily so server/API CI does not install heavy GPU packages. External downloading credentials and training are not introduced.
2. **No fabricated readiness:** tests use placeholder bytes, never call real `AutoModelForMultimodalLM.from_pretrained` on checkpoint assets, and do not assert usable actual model performance. No GPU evaluation, checkpoint release verification or real dataset exists on this CI runner.
3. **Artifact lineage not yet authoritative:** model/dataset UUID and expected hash are supplied by the caller; the adapter has no link to an actual immutable approved ModelVersion/Registry, validated benchmarked runtime configuration or Human Promotion. These must be checked by an owning policy service before any production call. Inferences are not exposed and cannot silently enable a model.
4. **Filesystem race remains an operations requirement:** SHA-256 is calculated before loader use; the mount must be trusted and truly read-only between attestation and loading. No false claim that path checks prove immutability of running infrastructure.
5. **Multimodal semantics intentionally excluded:** only text prompts are handled at the low-level. Candidate/Assessor/Instructor mode policies and hidden assessment content are not yet safe to expose. No Model Version/Gate/Flag Profile/Responsibility mutation.
6. **Staged development:** initial Lint and optional-import Type Check findings were corrected. The legacy Sprint 22 foundation no-runtime test originally rejected *any* model dependency in the whole directory; updated it to exclude the isolated adapter only. The final code SHA passes full CI.
7. **Independent reviewer and actual Runtime acceptance pending:** this technical self-review is not a Human Code Review approval. No Stage/QA/Release/Production performed. PR #21 remains Draft/Open/Unmerged.

**Gate:** Proceed with future offline adapter/dataset integration only after an independently trusted checkpoint manifest and strict model registry/evaluation/promotion evidence are available; do not invent LoRA, generation thresholds, weights or resource sizing.
