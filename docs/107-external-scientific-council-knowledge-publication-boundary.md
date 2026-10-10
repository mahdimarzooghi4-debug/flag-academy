# 107 — External Scientific Council Decision and Knowledge Publication Boundary

**Decision date:** 2026-10-10  
**Decision:** DEC-653 FINAL; replaces DEC-649 without deleting its history  
**Product status:** APPROVED BOUNDARY / INTAKE AND PUBLICATION NOT IMPLEMENTED

## Business decision

The Scientific Council deliberates and decides **outside Parcham**. It sends the outcome to Parcham. The Council's membership, deliberation procedure, votes, quorum and own decision approval are **external processes**, not Parcham product features. Do not define `SCIENTIFIC_COUNCIL` as an internal application role, create a member registry, construct quorum math or simulate Council decisions.

Academy Instructor/content owner continues to author versioned immutable `DRAFT` Knowledge. The Academy Admin (`ACADEMY_ADMIN`) remains the **final human authority** to publish Academy Knowledge after the applicable external Council decision has been received and adequately verified under a separately defined intake contract.

## Strictly separated responsibilities

1. **Outside Parcham:** Scientific Council reviews relevant content and produces its own decision.
2. **Parcham intake — contract pending:** record the exact communicated decision and its evidentiary/provenance link to a particular `KnowledgeSourceVersion` and SHA-256 content digest, preserving tenant scope and accountable audit without editing the original Instructor draft.
3. **Parcham publication — separate human decision, not yet implemented:** ACADEMY_ADMIN explicitly approves or refuses publication, with a separately authorized and audited write; **receipt of external Council communication does not automatically publish**.
4. **Knowledge use — separate:** even published knowledge is available only under future role, class/scope, purpose and AI-mode authorization; assessment-protected content is never implicitly exposed.
5. **AI learning — separate:** Knowledge-use or publication permission never equals Dataset approval, Training, automatic model change, Evaluation or Production activation.

## Decisions deliberately unresolved

- Which communication/receipt mechanism is authoritative (manual document delivery, authenticated integration, otherwise)?
- How to verify the notification's provenance/authenticity and exact authorized external decision identity?
- Which Parcham human may receive/register a notification and who verifies it? An ACADEMY_ADMIN publication power **does not automatically answer** the intake-authority question.
- External decision values/schema, signatures, reference identifiers, attachments, corrigenda, withdrawal and replacement semantics.
- Whether multiple Council decisions can address the same content version, and how the publisher must handle discrepancies.
- The final Admin publication/withdraw lifecycle, retrieval classifications, class/purpose/mode visibility and content verification access.

These are **contract questions**, not implementation defaults. Do not auto-promote, infer approval from silence, accept an unverified council message as authoritative or invent an external endpoint. Under the current implementation, KnowledgeSourceVersion remains SQL-enforced immutable `DRAFT`; no Council decision intake, approval, publication or retrieval routes exist.

## Compatibility and audit

- Historical `DEC-649` remains as `SUPERSEDED → DEC-653`. Prior code-review documents are historical snapshots and need not be rewritten.
- Existing P23-10 author-only/tenant-scoped Draft APIs and recorded human-authored content are unchanged.
- PR #21 remains Draft/Open/Unmerged on the existing stacked branch. No Stage, Human QA, Release, Production or model promotion is authorized by this decision.
