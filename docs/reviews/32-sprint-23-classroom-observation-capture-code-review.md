# 32 — Sprint 23 P23-09C factual classroom Observation technical self-review

**Date:** 2026-10-09  
**Reviewed code SHA:** `05a7ee30708a5ca5387c6ed19c19e6f7b1d80703`  
**Exact-head CI:** https://github.com/mahdimarzooghi4-debug/flag-academy/actions/runs/37952962348 — Backend, Frontend, E2E SUCCESS.  
**Status:** Scoped technical self-review ACCEPTED **only** for immutable Academy Observation capture. Independent human review, Evidence admission, UX and Stage acceptance are NOT approved.

## Positive findings

- New Academy-owned factual `ClassAssessorObservation` retains authoritative tenant, class, Session, Candidate member and Observer identities; grant ID/version, observed_at/recorded_at, note and idempotency key. No duplicate or forged cross-context links to Evidence/Flag Profile/Gate.
- Every write uses the current tenant/Assessor identity, transaction-scoped idempotency advisory lock, locked Academy grant and ClassOffering, current ACTIVE class/cohort, current real organization role and CANDIDATE membership. The observed-at timestamp must be inside both the real Session and original grant interval, and must not be in the future. No invented after-revocation authorization.
- Database append-only trigger and unique idempotency key are deployed through migration `0033_class_assessor_observations.py`; normal and replay paths never rewrite the source record.
- DomainEvent and Outbox are part of the same transaction, contain metadata but **not** the raw private observed_fact. Event says only that an Observation was recorded, never accepted as Evidence.
- GET requires current live class mandate and limits the list to the current Observer. Grant expiration/revocation means no historic classroom read through this endpoint.
- New negative/positive tests, migration and OpenAPI passed; unrelated live OIDC browser regression also passed. Earlier Ruff and Pyright issues were fixed at exact HEAD without feature expansions.

## Remaining acceptance and security work

1. This is **factual capture only**; separate, independently governed review and Evidence-domain ingestion are not implemented. A raw Academy Observation cannot become Evidence by event routing or heuristic.
2. POST and GET have focused stubbed-DB contract tests, not yet a dedicated real PostgreSQL + live OIDC API integration test. A concurrent create/revoke race test and append-only DB UPDATE/DELETE rejection test should be added before P23-09C acceptance.
3. Post-expiry/revocation historical entry authority remains undefined. Current behavior fails closed; only a future explicitly approved, separately audited endpoint could permit it.
4. ClassOffering terminal transition and end-of-class timestamp remain undefined; only explicit ACTIVE class/cohort are permitted now.
5. The independent Evidence reviewer identity/independence rules and decision audit contract must be defined before Evidence admission; do not assign Academy Admin or Assessor as universal reviewer by assumption.
6. Review output does not grant model learning eligibility, CapabilityClaim update, Gate decision or Responsibility mutation.

**Disposition:** technical foundation accepted for further development; Sprint 23, Figma final sign-off, independent human Code Review, Stage and Production remain open. PR #21 must remain Draft/Open and unmerged.
