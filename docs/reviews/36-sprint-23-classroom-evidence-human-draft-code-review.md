# 36 — Sprint 23 explicit classroom Evidence Draft technical self-review

**Date:** 2026-10-10
**Reviewed head:** `d4b0e97470b15c934f87c658b78b88c66d297ae5`
**Exact-head CI:** https://github.com/mahdimarzooghi4-debug/flag-academy/actions/runs/38030862000 — Backend, Frontend and live OIDC/PostgreSQL E2E SUCCESS.
**Review status:** Scoped technical **self-review PASSED for the private human-requested Draft foundation**. Not independent human Code Review, Evidence acceptance, Stage, Figma FINAL or Production approval.

## Files reviewed
- `backend/app/evidence/classroom_evidence_draft_api.py` and route registration in `backend/app/main.py`.
- `backend/app/evidence/consumer.py` (legacy `observation.sealed.v1` does not ingest reserved classroom context).
- `backend/tests/test_classroom_evidence_draft.py`, `frontend/tests/e2e/class-workspaces.spec.ts`, `backend/scripts/observation_integrity_acceptance.py`.
- `docs/102-classroom-evidence-human-draft-foundation.md`.

## Findings

1. **Explicit human action:** Only the actual independent reviewer of a `VERIFIED`, immutable, SHA-256-attested Academy classroom Observation may send the exact human creation command. Original observing Assessor cannot self-review or create from their own source; viewer requires current independent live Academy grant and tenant Assessor membership.
2. **Immutable provenance:** Client binds source digest and review ID. Original source grant/version, class, session, subject, observer, review and current reviewer-grant lineage are re-attested under source/grant row locks; no inferred identity or missing-data defaults.
3. **Exactly once:** Source ID is an existing unique EvidenceCase constraint. Two concurrent OIDC POSTs across independent DB transactions return the same Draft case ID and produce one database row and one create event. Conflicting reason, review ID or source digest fails closed.
4. **Private access:** Reserved `CLASSROOM_OBSERVATION` stays filtered from generic org-wide Evidence list/get/mutation and Candidate list/response. Dedicated GET requires exact creating reviewer, current class appointment and refreshed source+review lineage. Guessed IDs/other Assessor/revocation fail with 404.
5. **No implicit decision:** Result is `status=DRAFT`, `integrity_state=SOURCE_REVIEWED`, `candidate_visible=false`, empty candidate projection; no Evidence interpretation, Evidence ACCEPT, CapabilityClaim, Gate, Profile or AI learning action. Independence group correlates same Academy class rather than claiming independent proof.
6. **Audit confidentiality:** DomainEvent/Outbox atomically persist source/review metadata and Actor; neither the raw observed_fact nor submission_reason is emitted. The private reason is stored only in Evidence provenance.
7. **Legacy event separation:** `observation.sealed.v1` cannot ingest a classroom-context case through its old system consumer. Classroom Draft requires the new human request.
8. **Coverage:** Contract tests include changed/stale digest, reviewer identity, rejected source, revoked mandate, replay/conflict, private read, provenance tamper and legacy event rejection. Full CI includes two real OIDC identities, actual browser POST/GET/revoke and committed PostgreSQL/outbox assertions.

## Residual product and governance gates

- This **does not** implement formal `DRAFT → SUBMITTED → UNDER_REVIEW → ACCEPTED/REJECTED` for classroom cases. Existing generic case mutation routes deny the private source by design; next slice must provide dedicated Evidence-owned, class-scoped human interpretation/submission/review commands with separately accountable reviewer independence, exact version checks and candidate-safe handling, *without relaxing generic privacy guards*.
- The original Source reviewer cannot be assumed sufficient to provide the consequential formal Evidence decision; any additional reviewer/appointment policy must derive from approved product contracts and independent role rules, not be invented.
- Real human Academy Evidence admission remains unperformed. Synthetic CI identities, reviewed source and Draft are not operational decisions.
- Security tests are implementation/CI evidence, not external penetration testing or human approval.
- Knowledge Council, Figma reconciliation and independent Code Review remain open; Stage/QA/Release/Production were not run. PR #19, #20, #21 remain Draft/Open/unmerged.

**Disposition:** Accept this technical foundation for further feature work, not for formal evidence acceptance, independent approval or Stage.
