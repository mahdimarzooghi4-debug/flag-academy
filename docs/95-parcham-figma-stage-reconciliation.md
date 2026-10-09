# 95 — Parcham Figma ↔ Frontend Reconciliation and Stage Candidate Boundary

**Date:** 2026-10-09  
**Status:** REVIEW CANDIDATE — no Figma final sign-off, no Stage admission or Release approval.  
**GitHub source branch:** `sprint-23-class-simulator-foundation` · PR #21 Draft/Open, stacked on Sprint 22.  
**Audited code baseline:** `0536f4d8a8a0145af22870912cfda20603e5aa25`; CI run #37945737298 SUCCESS (Backend, Frontend, E2E).  
**Canonical Figma:** https://www.figma.com/design/K62FGKHidy3jiBsmHHs91k/flag-academy?node-id=131-426  
**Product UX review board:** Figma node `170:2236`.

## Design scope and source of truth

The `03 — Product Screens` page has **14 numbered product UX frames**, reusable component sections, one UX Review Board, and separate `Archive /` and `Exploration /` frames. Only the numbered product screens are reconciliation candidates. Archived or explorative prototypes are **not** approved live features. The Figma screen data is representative UX/sample content, **never** a backend runtime truth or proof of completed integrations.

All operational behavior, human approval boundaries, authorization, lifecycle and source-of-truth contracts remain anchored in repository Business/Technical decisions and tested backend APIs. Visual Figma parity is a separate, not-yet-passed review gate.

### Canonical numbered screens and code ownership

| Figma node | Product screen | Existing frontend surface | Reconciliation status |
|---|---|---|---|
| `135:617` | 01 ورود | `frontend/src/auth.tsx`, `App.tsx` OIDC gate | Code path exists; visual verification pending |
| `135:662` | 02 فراگیر / امروز | `CandidateHome.tsx` | Code path exists; parity pending |
| `135:860` | 03 فراگیر / مأموریت | `MissionWorkspace.tsx` | Code path exists; parity pending |
| `150:2592` | 04 استاد / فضا | `InstructorHome.tsx`, `InstructorClassWorkspace.tsx` | Class workspace implemented; parity pending |
| `150:2782` | 05 ارزیاب / شواهد | `EvidenceWorkspace.tsx` | Code path exists; scoped Observation gap below |
| `150:2964` | 06 ارزیاب / الگو | `PatternWorkspace.tsx` | Code path exists; parity pending |
| `156:4969` | 07 ارزیاب / پروفایل | `ProfileWorkspace.tsx` | Code path exists; parity pending |
| `156:5286` | 08 ارزیاب / Gate | `GateWorkspace.tsx` | Code path exists; parity pending |
| `156:5592` | 09 مدیر / آکادمی | `AcademyStudio.tsx`, `AdminAcademyOperationsWorkspace.tsx`, `AssessorGrantAdminWorkspace.tsx` | Operational subset exists; governance gaps below |
| `164:4191` | 10 مدیر / حاکمیت AI | `AIGovernanceWorkspace.tsx`, `SeedLearningApprovalWorkspace.tsx` | Governance UI exists; model and dataset remain non-operational |
| `189:2504` | 11 فراگیر / یادگیری | Candidate learning section in `App.tsx` / `CandidateHome.tsx` | Dedicated Figma parity unverified |
| `195:2341` | 12 فراگیر / تمرین | Candidate practice section in `App.tsx` | Dedicated Figma parity unverified |
| `195:2542` | 13 فراگیر / بازخورد | Candidate feedback section in `App.tsx` | Dedicated Figma parity unverified |
| `195:2734` | 14 فراگیر / رشد من | `CandidateReportWorkspace.tsx` and existing safe growth projections | Formal state remains authoritative; parity pending |

**Important:** Component existence is not equivalent to pixel-perfect design implementation or role-based browser acceptance on that exact Figma frame. Reconcile UI navigation, empty/loading/error/stale states, OIDC actor/tenant visibility, and mocked values before calling a screen FINAL.

## Targeted canonical Figma contract corrections — applied

The UX Review Board is the owner of these alignment edits made on 2026-10-09 (the rest of the canvas remains unchanged):

- `255:3149`: a learner-facing `درس` is a versioned presentation of an existing `CapabilityVersion`, not a new `Subject` aggregate.
- `255:3177`: class flow now explicitly presents `ClassOffering` / `CapabilityVersion` / `Session`.
- `255:3185`: subject identity derives from an actual versioned `CapabilityVersion`.
- `255:3246`: AI training eligibility includes separately approved synthetic Seed and authorized real sources, never raw classroom activity.

No model execution, Knowledge publication, human governance approval, Stage acceptance, or Release claim was made by these design text edits.

## What can enter the first ephemeral Stage acceptance candidate

The **proposed scope**, pending accountable product/technical acceptance, is limited to repository-implemented and tested experiences: OIDC login; bounded Candidate/Instructor/Assessor/Admin views; Mission/Learning, Attendance, roster, class activity, qualitative report, assessment/profile/gate human-controlled paths; Assessor class-grant lifecycle and read access; read-only AI governance; non-operational Seed approval preview and Knowledge Draft registry.

Every screen must clearly distinguish `NOT_IMPLEMENTED` / `DRAFT` / `PREVIEW` / `DATA_UNAVAILABLE` where applicable; fake payment, AI inference, model training, accepted Dataset Version, or published knowledge must never be implied. Figma Explorations (especially proposed AI instructor-memory and autonomous-content workflows) are **excluded** from this candidate.

## Open gates — must not be converted into silent acceptance

1. **P23-09C:** Class/Session/Candidate-linked factual Assessor Observation, separate observed-at/recorded-at, valid grant time and independently human-reviewed Evidence promotion. The current read-only Assessor Workspace is not this writer contract.
2. **Class completion policy:** authoritative terminal status/actual completion cutoff for grant expiration still lacks a complete approved lifecycle.
3. **Knowledge governance:** Scientific Council member/role/quorum contract, separate council review, Admin publication/revocation, and role/purpose/mode scoped *published* retrieval are not implemented.
4. **Proof/focus/attendance closure:** independent ProofState reader, Instructor decision/write contract for next learning focus, and explicit Attendance finalization/correction lifecycle remain unresolved.
5. **Dataset and Gemma:** no actual accountable Seed approval in operating Academy, no operational Dataset Version 1, no real pretrained checkpoint/LoRA Trainer/GPU benchmark or authorized Tutor runtime. Their *governance and fail-closed UI only* can be tested in Stage; real AI cannot.
6. **Design sign-off:** numbered screen UX parity, role navigation, loading/empty/error/stale states and responsive/accessibility acceptance need explicit inspection and recorded results; current frames remain UX-review candidates.
7. **Independent Code Review and PR chain:** PR #19 → #20 → #21 are Draft/Open stacked changes; existing technical self-reviews do not confer independent Human Code Review or permission to merge.
8. **Stage workflow admission:** `.github/workflows/stage.yml` is **ephemeral** and creates short-lived test infrastructure. Its automatic PR trigger targets `main`; stacked PR #21 does not itself qualify. Running or editing the Stage workflow requires explicit admission decision and an exact pinned SHA. It is not Production deployment.

## Fast closure sequence (no invented decisions)

**A — Freeze bounded Stage candidate scope:** Owner explicitly accepts which incomplete capabilities are deferred/excluded vs required for Sprint 23. Deferral must be visible in UX; it cannot be disguised as working functionality.

**B — Finish Figma:** inspect 14 numbered frames against tested role-specific live UI, fix only witnessed mismatches, capture sign-off and version/node inventory; keep Archive/Exploration out of Stage.

**C — Close code gaps on approved scope:** implement remaining authorized contract slices with Backend → tests → Code Review → CI, prioritizing P23-09C if included. Do not invent Class completion, Council quorum or AI recipe.

**D — Independent review / Stage:** reconcile stacked PR dependencies and obtain explicit approval for review and Stage admission at exact SHA. Only then execute ephemeral Stage Acceptance and record evidence. Stage SUCCESS is not release approval, model approval or Production readiness.

## Acceptance semantics

This document is a **reconciliation record**, not proof that all 14 Figma screens are final or a substitute for the Stage workflow. The intentionally unmet gates above remain open until independently evidenced. The approved development sequence is Business → Technical → Scrum/Product Backlog → Sprint → Code → Code Review → Stage → QA/Testing → Release Approval → Production → Monitoring → Improvement.
