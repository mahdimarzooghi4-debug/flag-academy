# 99 — Independent source attestation before Classroom Evidence

**Date:** 2026-10-09  
**Status:** Evidence-owned review foundation, no EvidenceCase creation or acceptance.

A different Assessor, appointed by an Academy Admin to exactly the same operational class, may read a single immutable classroom observation and explicitly record one independent decision: `VERIFIED` or `REJECTED`, with a reason. **VERIFIED means only that the reviewer attests the factual source for possible later Evidence assessment. It is not Evidence accepted, a formal claim, a score, or eligibility for AI learning.**

The reviewer must have a live class grant, current organization Assessor membership, and not be the original observing Assessor nor the subject. The source's class/session linkage and archived grant revision must support the actual observed-at time, independently of the current grant's later status. The source is SHA-256 attested from canonical tenant/class/session/person/grant/time/factual bytes; clients provide the digest they reviewed. Stale digests fail with 409. Two concurrent reviews serialize on the immutable source row, and conflicting review/replay fails 409. The evidence-owned review row is append-only with a PostgreSQL UPDATE/DELETE trigger; a DomainEvent and Outbox metadata-only record are atomic with the review. Private factual text and rationale are not included in the event payload.

APIs are only:
- `GET /api/v1/classroom-observations/{id}/review-source` — returns factual source and its digest to the independent live-appointed Assessor
- `POST /api/v1/classroom-observations/{id}/review-source` — explicit human decision against the exact source digest

The decision is deliberately separate from `EvidenceCase`. Existing Evidence API has broader role-based read semantics than the Academy's per-class confidentiality requirement. Automatically emitting a Draft EvidenceCase would expose the class-sourced content through existing evidence listings without a new evidence-owned authorization contract. Therefore, **no automatic or manual EvidenceCase creation is added yet**; the next package must harden read/write access for classroom-sourced evidence cases, bind human source decision and immutable source digest into Evidence provenance, and only then create a Draft using explicit human submission. Formal Evidence decisions remain the existing Evidence context's `DRAFT → SUBMITTED → UNDER_REVIEW → ACCEPTED/REJECTED` lifecycle, not an alternative review model.

No Council publication, Dataset approval, Gemini/Gemma execution, Profile/Gate mutation, PR merge or Stage admission is authorized.
