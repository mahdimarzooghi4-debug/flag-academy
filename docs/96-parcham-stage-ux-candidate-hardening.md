# 96 — Figma candidate UX Stage-scope hardening

**Date:** 2026-10-09
**Review basis:** Figma file `K62FGKHidy3jiBsmHHs91k`, page `131:426`, UX review board `170:2236`.
**Status:** implementation candidate and scoped technical review, not Figma final approval or Stage execution.

## Observed mismatch and fix

The live Candidate Home had raw `TO_LEARN`, `UNPROVEN`, task/attempt states and an English ATTEMPT count in the main learner view. The official Figma board requires understandable learner language and missing-data safety. More importantly, an unrecognized pre-work status previously fell into the branch showing *completed*, which implied progression without an authoritative state. The implementation now:
- translates only known canonical status codes and preserves unknown values without inventing meaning;
- uses a no-next-session factual empty message instead of asserting a Capability is active;
- explains absent learning/proof lists without interpreting missing proof as failure or weakness;
- treats ONLY explicit `COMPLETED` as completed pre-work, and disables progress actions on unsupported values;
- keeps Proof entirely separate from Learning status and prevents automatic Evidence/Claim/Gate changes.

Unit coverage tests known states, absent data and unsupported pre-work states. CI green is required for acceptance.

## Design reconciliation already performed

The Figma UX board's eight review-label nodes now explicitly identify Stage subset and unfinished implementation for screens 04, 05, 09, 10, 11, 12, 13 and 14. The full Instructor AI design remains future UX only. Model/Dataset success samples remain mock, not operational evidence. The canonical design node corrections of `255:3149`, `255:3177`, `255:3185`, `255:3246` remain intact.

## Deliberate open items

Live visual parity for all 14 product frames, accessibility screenshots, P23-09C, Scientific Council decisions, full published Knowledge flow and real AI runtime are NOT accepted by this work. Independent reviewer approval and human Figma sign-off are not asserted. Stage may only be run after explicit admission at a pinned SHA; `#19 → #20 → #21` remain Draft/Open/Unmerged.
