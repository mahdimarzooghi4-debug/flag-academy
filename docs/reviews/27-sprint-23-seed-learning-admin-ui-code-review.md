# Sprint 23 — P23-10 Seed learning approval Admin UI: scoped technical review

**Review date:** 2026-10-09
**Reviewed implementation HEAD:** `4c63a18fc3bc9e6a393f23f67832109438b26f3c`
**Exact-head CI:** [37925534341](https://github.com/mahdimarzooghi4-debug/flag-academy/actions/runs/37925534341) — **SUCCESS** Backend, Frontend and Live Keycloak/OIDC E2E, including the prior governed AI Dataset Builder, Training, Model Registry, Evaluation and Promotion regression checks.
**Verdict:** P23-10 **Admin Seed Learning Approval workspace — CODE/CI VERIFIED**, limited to the approved synthetic Decision-Making Seed v1; **not** evidence that an Academy-environment approval or persistent Dataset Version has been created. This is a technical self-review, not independent human PR approval, Stage, Release or Production approval.

## Review scope

- `frontend/src/components/SeedLearningApprovalWorkspace.tsx`: new separate Admin action surface, deliberately NOT added as a mutation to the existing read-only `AIGovernanceWorkspace`. The source preview comes exclusively from the existing authenticated `GET /api/v1/admin/ai/seed-learning/decision-making-v1` backend contract.
- `frontend/src/App.tsx`: mounts the new action only for authenticated `ACADEMY_ADMIN`, keyed by actual `organization_context_id` and `person_id`. The existing backend independently requires that role on both read and write routes. No generic Dataset upload or tenant-selected source is introduced.
- Explicit approval is *not automatic*: reviewed-file acknowledgement, a separately meaningful Human approval reference, and a manually matched **full** SHA-256 are all required before the button becomes active. Invalid source type, source path, digest or purpose fails closed. A changed preview digest/version resets all Human confirmations.
- The submit action pins `expected_source_payload_digest` to the exact displayed source and posts only the existing approved `approval_reference` contract. It does not expose a training API, arbitrary artifact or model activation command.
- Approval receipts are checked against source name, source digest, dataset name and the signed-in reviewer. UI state and cache are separated by organization/person/source; a failed/refreshing preview blocks approval and is not treated as a cached authorization.
- After successful response, relevant preview/governance queries are invalidated, but the UI explicitly says **Dataset Version creation remains pending** until the transactional Outbox event is delivered and the NATS automatic Dataset Builder consumes the approved input.

## Evidence / tests

- `frontend/src/components/SeedLearningApprovalWorkspace.test.tsx`: verifies metadata and full digest, disabled-by-default approval, explicit independent review/reference/digest matching, invalid source/digest denial, revocation of approval confirmation after a digest change, approved-preview read-only state, receipt vs persistent Dataset separation, and failure/busy handling.
- `frontend/tests/e2e/class-workspaces.spec.ts`: signed-in development Academy Admin sees the real Seed preview from FastAPI under live Keycloak/OIDC, with the exact SHA-256 and disabled approval command; Assessor identity cannot fetch the Admin-only Seed preview (403). This **does not** invoke human approval in CI through the Admin UI or create a persistent target-environment Dataset.
- The existing isolated acceptance `backend/scripts/ai_seed_learning_approval_acceptance.py` remains the evidence for the **ephemeral** approved Seed → NATS → automatic Dataset Version 1 contract; not for a real organization Dataset.
- The exact-head CI run succeeded. No Production server, GPU, external model API, OpenAI, standalone inference endpoint or invented hyperparameter has been added.

## Explicit residual work / governance

1. A real Academy Admin must inspect the exact source bytes and SHA-256, record an actual independent AI-learning approval reference, and explicitly approve the Seed in the authorized target Academy environment. The tool did **not** manufacture or execute that Human decision.
2. The real running environment requires PostgreSQL, Outbox delivery/NATS and Dataset Builder consumers to materialize the first **persistent** immutable Dataset Version; successful approval HTTP alone does not prove that creation.
3. The 24 synthetic Decision-Making records are **initial source material only**, not an independently approved Evaluation Dataset and not representative evidence sufficient for model quality, fairness, or Production use.
4. Gemma 4 12B model training/execution, governed evaluation with an independent dataset, Academy role-scoped approved Knowledge retrieval and a functioning AI Tutor remain unimplemented. Do not claim runtime readiness, auto-training, automatic Production learning or release authorization.
5. P23-09C and remaining Sprint 23 product/technical gates are still outstanding; PR #21 remains Draft/Open/Unmerged. No Stage, QA Gate, Release, Production or independent Human Code Review approval.

**Next appropriate work package:** versioned and role-scoped Academy Knowledge read/retrieval contract, plus a separate offline Gemma training/executor integration plan and tests on authorized immutable Dataset Versions. Do not select optimizer, LoRA settings, model checkpoint, deployment provider or numeric thresholds without a benchmark/explicit decision.
