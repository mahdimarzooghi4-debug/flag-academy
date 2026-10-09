# Sprint 23 — P23-10 Academy Knowledge Draft Registry: scoped technical review

**Date:** 2026-10-09
**Reviewed code HEAD:** `b973d8a622f3b5bbef0804e2fa83dd947c2c7f59`
**Exact-head CI:** [37929363329](https://github.com/mahdimarzooghi4-debug/flag-academy/actions/runs/37929363329) — SUCCESS (Backend, Frontend, live Keycloak/OIDC/PostgreSQL E2E, existing AI governance).
**Scope verdict:** **Draft-only authoring foundation Code/CI verified**, not independent human PR approval, Council approval, Academy publication, Stage or Production readiness.

## Contract and ownership

- The independent `knowledge` bounded context owns `KnowledgeSource` and `KnowledgeSourceVersion`, in the new `knowledge` PostgreSQL schema via migration `0032_knowledge_draft_registry.py`. There are no cross-domain foreign keys to Identity, Curriculum, Evidence, AI or Gate.
- A source belongs to exactly one organization and source key; the initial responsible Instructor owns proposals for that source. New version numbers are persisted, with source version identity, author, timestamp, fixed `INTERNAL` classification and SHA-256 of the exact UTF-8 text.
- A PostgreSQL trigger forbids updating/deleting existing versions. Every version is constrained by PostgreSQL to `DRAFT`; no `APPROVED`, `PUBLISHED`, `RETIRED` or AI learning state is guessed or writeable through this slice.
- POST `/api/v1/knowledge/draft-versions` requires authoritative current same-organization Instructor membership; bounded source key, payload and idempotency key. Multi-replica-safe PostgreSQL advisory locks serialize both `organization+person+idempotency_key` and `organization+source_key` in sorted order to prevent duplicate/version races and lock-order deadlocks. An exact replay returns the historical version, while changed payload or key reuse for another source fails with 409. A different Instructor cannot mutate another Instructor-owned source.
- Version creation, `knowledge.draft_version_proposed.v1` Domain Event and transactional Outbox are written in one transaction, carrying **only non-sensitive source/version metadata and content digest**, never the draft body. This event **is not** a Knowledge-use approval, AI-learning approval, or Dataset trigger.
- Instructor `GET /api/v1/knowledge/my-drafts` is author- and tenant-scoped; Academy Admin `GET /api/v1/admin/knowledge/draft-versions` is tenant-scoped. Both return bounded metadata only; neither returns draft body. Candidate/Assessor receive no route permission and cannot retrieve knowledge drafts. The content remains private pending an independently designed Council review contract.
- The initial Academy Knowledge Pack v1 remains an authored, approved-for-authoring canonical document, not a silently published runtime KnowledgeSource. A synthetic Decision Making seed approved for AI-learning follows its existing *different* pipeline and is not imported as a draft through this interface.

## Test evidence

- `backend/tests/test_knowledge_draft_registry.py` covers OpenAPI role/security/bounds, tenant and author predicates, source ownership, initial and new version, exact historical replay, changed-key 409, cross-source idempotency conflict, absent current Instructor membership 403, metadata-only Admin read, append-only migration and event/outbox atomicity.
- Existing backend migration and smoke checks validate the `0032` schema and initialization against PostgreSQL in CI.
- `frontend/tests/e2e/class-workspaces.spec.ts` now exercises actual signed-in Instructor POST against FastAPI/PostgreSQL for Draft v1, retry, 409 conflict, Draft v2 and private author-scoped listing. It then signs in as Academy Admin and verifies the org-scoped metadata list contains two Draft versions, no `content_text` and no published state. OIDC is live and API calls are not mocked. Existing classroom, AI and role regression tests remain green.
- An early code Lint issue and an overbroad test assertion about SQL SELECT columns were fixed; the final exact-head CI is green. SQL authorization checks assert bound predicates rather than fragile compiled SQL formatting.

## Blocking contracts deliberately NOT implemented

1. **Scientific Council review:** membership, reviewer identity/role, quorum, delegation, conflict-of-interest and Council approval state machine remain undecided. No synthetic approval, bypass or guessed `SCIENTIFIC_COUNCIL` JWT role.
2. **Academy Admin final publication:** no publish/withdraw API, approval shortcut or automatic `ACTIVE` state. Draft content is unavailable to any Candidate, AI Tutor, public search or Retrieval index.
3. **Knowledge access:** DEC-650 requires role/mode/purpose/class-permission and hidden-assessment protection. No retrieval route, embedding, index, similarity or shared raw content exposure exists in this slice, regardless of separate architectural DEC-512's intended future search technologies.
4. **AI Data:** Knowledge-use approval, AI-learning approval and Training Dataset governance remain distinct. A `DRAFT` does not feed Training/Automatic Dataset Builder; no Gemma runtime/trainer/evaluation/evidence/promotion changes.
5. **Operational gates:** PR #21 remains Draft/Open/Unmerged on stacked Sprint 22 base; no independent human review, Stage, QA Gate, Release, Production or external infrastructure was performed.

**Next safe slice:** Design the actual Council reviewer roster/quorum and its authenticated public-reader contract, then implement Human Council Review → explicit Academy Admin publication with immutable provenance and status. Only *published* source versions may later enter separately approved role/purpose/mode-aware retrieval. Alternatively, build isolated Gemma training harness tests without any Production/GPU/hyperparameter assumptions.
