# 101 — Classroom Evidence confidentiality admission boundary

**Date:** 2026-10-09

`EvidenceCase.source_context == CLASSROOM_OBSERVATION` is reserved as a private classroom source marker. Existing organization-wide Assessor Evidence list, detail and mutation paths and Candidate list/candidate-response paths do **not** authorize access to private classroom cases, even when an EvidenceCase ID is known. The ordinary Evidence list filters this context at SQL level; direct case lookup denies it without disclosing existence. Candidate list similarly excludes this context. Legacy mission-based Evidence source contexts remain unchanged.

This is a **temporary, explicit fail-closed safety barrier**, not a completed classroom Evidence feature. No EvidenceCase with classroom context is created. Future code may create a Draft only after an Evidence-owned class-source permission contract is implemented, after an independent human VERIFIED source review is re-attested against the immutable Academy source and provenance, and after deliberate human submission. It must provide its own class-scoped read/write and candidate-safe projection, not repurpose existing org-wide Evidence routes or let consumer events auto-promote. Evidence ACCEPTED and Profile/Gate changes still require their existing human-governed chains.

New negative SQL and detail tests enforce that a mere organization-wide ASSESSOR or guessed case ID cannot extract these classroom-sourced records. This does not constitute Stage admission, independent human approval or full classroom Draft workflow.
