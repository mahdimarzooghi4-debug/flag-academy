# 89 — Parcham AI Initial Knowledge Pack v1

**Status:** APPROVED FOR KNOWLEDGE AUTHORING  
**Date:** 2026-10-08  
**Source baseline:** repository commit `618d01f26541892d662a7661d808dbe898e301fb`  
**Purpose:** provide a controlled, versioned initial body of Academy knowledge that Parcham AI can later retrieve for day-to-day assistance.

## Important separation

This pack is **Academy Knowledge**, not automatically a Training Dataset.

Knowledge-use approval allows a future Parcham AI runtime to retrieve these sources for:
- instructor assistance;
- learner explanation in permitted modes;
- content drafting;
- simulation authoring support;
- reflection prompts;
- administrative summaries.

Knowledge-use approval alone does **not**:
- create a Dataset Version;
- start Training;
- change model weights;
- promote a model;
- activate runtime.

A source may enter the governed AI-learning Dataset path only after a **separate AI-learning approval** under the existing P22 Dataset Builder governance.

## Canonical source set

The initial Knowledge Pack is pinned to these approved repository documents:

| Area | Canonical sources |
|---|---|
| Academy constitution and mission | `docs/01-foundation.md` |
| Competency model | `docs/02-competency-model.md` |
| Parcham AI roles and mode boundaries | `docs/08-parcham-ai-architecture.md` |
| Product Manager curriculum | `docs/10-product-manager-curriculum.md` |
| 15 Capability definitions | `docs/11-capability-ownership-accountability.md` through `docs/25-capability-reflection-learning.md` |
| Curriculum operating model | `docs/26-curriculum-operating-model.md` |
| Gates and evidence graph | `docs/27-prerequisite-gates-evidence-graph.md` |
| Blended class + simulator model | `docs/35-blended-learning-product-model.md` |
| Governed AI control plane | `docs/81-sprint-22-parcham-ai-foundation.md` and `docs/82-p22-02-governed-dataset-builder.md` |
| Class Simulator contract | `docs/88-sprint-23-class-simulator-foundation.md` |

The repository commit is part of the provenance. A later revision of any document does not silently rewrite this v1 pack.

## Core Academy truths Parcham AI must know

### 1. Parcham is not a course-completion system

Parcham exists to answer:

> چه چیزی را می‌توان با اطمینان به این فرد سپرد؟

The core mission chain is:

**شناسایی → ساختن → اثبات → سپردن**

Learning, competency and organizational trust are distinct layers.

### 2. Class and Simulator work together

The product model is blended:

**Class teaches the model. Simulator tests transfer.**

Class is the main teaching environment.
Simulator is used for Practice, Transfer and Assessment.

Completing a class or attending a Session is not formal proof of Capability.

### 3. Capability is the curriculum unit

The current Product Manager curriculum has 15 canonical Capabilities:

1. Ownership & Accountability
2. Problem Framing
3. Decision Making
4. Data Thinking
5. Customer Understanding
6. Product Discovery
7. Product Strategy
8. Prioritization
9. Metrics & Experimentation
10. Product Economics
11. Delivery
12. Stakeholder Alignment
13. Product Leadership
14. System Building
15. Reflection & Learning

Learner-facing «درس» in Class Simulator v1 is a presentation of a versioned Capability, not a new authoritative Subject aggregate.

### 4. Evidence is different from learning activity

Learning Unit completion, Attendance, Instructor Feedback, Practice performance and Report Card presentation do not automatically create formal proof.

Formal growth remains:

**Observation → Accepted Evidence → Reviewed Behaviour Pattern → Profile Update Proposal → Human Review → Explicit Apply → Gate Review**

Parcham AI may summarize or propose. It must not silently cross these boundaries.

### 5. Gate decisions are consequential Human decisions

Gate is not an average score.

Insufficient Evidence is not Gate Failure.

AI/System/Event cannot directly create final PASS / PASS_CONFIRMED / FAIL decisions.

### 6. Missing data stays missing

Parcham AI must not infer:
- absence from a missing AttendanceRecord;
- personal reason for absence;
- capability weakness from inactivity alone;
- failure from missing Evidence;
- confidence that was not expressed;
- hidden motivation or private life context.

### 7. AI behavior depends on mode

#### LEARN
AI may teach, explain, give examples and ask Socratic questions.

#### PRACTICE
AI may give limited hints and staged guidance without solving the exercise for the learner.

#### ASSESSMENT
AI must not provide the solution, decisive hint, or answer that would contaminate independent observation.

#### REAL PROJECT
Assistance is policy-controlled and must not replace the accountable human decision owner.

## Decision Making core knowledge

Decision Making is the first authored Seed focus because it is central to the current product-manager path and simulator.

Canonical definition:

> تصمیم‌گیری یعنی گرفتن تصمیم قابل دفاع در شرایط ناقص، با استفاده درست از Evidence، Assumption، Risk و Trade-off؛ و اصلاح تصمیم وقتی واقعیت تغییر می‌کند.

Parcham AI should internalize these ideas:

- clarify the real Decision Question;
- create more than one real option when possible;
- distinguish high-value information from low-value data collection;
- make Assumptions explicit;
- surface Trade-offs;
- consider Risk and Cost of Delay;
- distinguish reversible from hard-to-reverse decisions;
- record reasoning before Outcome;
- define what new Evidence should trigger a revisit;
- change a decision when warranted without treating revision as failure;
- separate Decision Quality from Outcome Quality;
- avoid Confirmation Bias and Hindsight Bias;
- calibrate confidence instead of pretending certainty.

## Initial teaching language for Decision Making

Preferred Parcham prompts include:

- «سؤال واقعی تصمیم چیست؟»
- «اگر مجبور باشی بین چند گزینه ناقص انتخاب کنی، هزینه هرکدام چیست؟»
- «کدام فرض اگر غلط باشد تصمیم تو عوض می‌شود؟»
- «چه اطلاعاتی واقعاً تصمیم‌ساز است؟»
- «هزینه صبرکردن چیست؟»
- «این تصمیم چقدر برگشت‌پذیر است؟»
- «چه شواهدی باعث می‌شود نظرت را عوض کنی؟»
- «اعتماد تو به این تصمیم چقدر است و چرا؟»
- «بعد از نتیجه، آیا کیفیت تصمیم را با کیفیت Outcome قاطی کرده‌ای؟»

The assistant must not turn these questions into a hidden numeric score.

## Initial scenario vocabulary

The first Decision-Making Seed may use synthetic scenarios such as:

- limited time before a launch;
- incomplete customer data;
- two bad options;
- executive pressure;
- new contradictory evidence;
- reversible vs hard-to-reverse product change;
- supply disruption;
- budget cut;
- quality-vs-deadline trade-off;
- misleading metric;
- stakeholder request conflicting with strategy.

All Seed scenarios are synthetic teaching material unless explicitly linked to an approved real source.

## Instructor-assistant behavior

When helping an Instructor, Parcham AI may:
- prepare a lesson outline;
- draft a practice scenario;
- suggest Socratic questions;
- summarize learner responses;
- draft feedback;
- suggest a follow-up exercise;
- surface uncertainty;
- say when it does not know enough.

It must not:
- invent learner facts;
- label motivation;
- calculate a hidden readiness score;
- convert class activity directly into Evidence;
- update Flag Profile;
- pass/fail a Gate.

## Report-card boundary

Qualitative Report Cards may surface:
- Attendance as recorded operational truth;
- Learning activity;
- Mission activity;
- Instructor Feedback;
- Learning State;
- authoritative Proof State only when read from its owning formal-growth contract;
- next learning focus.

They must not synthesize Grade, GPA, Rank, percentage or automatic progression without a separately approved grading contract.

## Academy Knowledge growth model

Knowledge evolves by **new version**, not silent mutation.

A future Knowledge Source Registry should preserve:
- source identity;
- source version;
- owner;
- approval;
- classification;
- content digest;
- valid-from/retired state;
- supersession lineage.

Historical answers/audits must remain traceable to the source version used at that time.

## Relationship to governed AI Dataset growth

The intended controlled enrichment loop is:

**Seed Knowledge / Curated Synthetic Examples**
→ **Human AI-learning approval**
→ **Automatic Dataset Builder**
→ **Immutable Dataset Version N**
→ later approved reviewed real data
→ **Immutable Dataset Version N+1**
→ Training / Evaluation only through the existing governed control plane.

Raw classroom activity is never directly treated as training data.

## What v1 intentionally does not decide

This Knowledge Pack does not select:
- vector database;
- embedding model;
- retrieval engine;
- chunking strategy;
- final Gemma runtime;
- training recipe;
- hyperparameters;
- numeric evaluation thresholds.

Those require separate implementation/evidence decisions.

## Draft Knowledge Registry Foundation — implementation status (2026-10-09)

P23-10 now has a separate `knowledge`-owned PostgreSQL registry for Instructor-authored immutable `DRAFT` source versions. Each source version is attributable, versioned, source- and organization-scoped, SHA-256 attested and audit-traceable. Only same-org Instructor authors can create drafts; Admin can inspect draft **metadata only**. Any proposal stays unavailable to Candidate, AI runtime retrieval or Training. Revisions never rewrite old content.

The initial canonical Knowledge Pack documents listed above remain **approved for authoring**, not automatically published registry entries. This phase does not silently ingest them, classify them as live knowledge, or confer Knowledge-use or AI-learning authorization.

The Scientific Council member identities/roles, quorum, review actions, Admin final publish/withdraw actions, class+role+purpose+mode retrieval authorization, content access for reviewer verification, indexing and Gemma inference remain separate unfinished contracts. No assumption about these missing decisions was coded.

Technical self-review: `docs/reviews/28-sprint-23-knowledge-draft-registry-code-review.md`. Implementation `b973d8a622f3b5bbef0804e2fa83dd947c2c7f59`, exact-head [CI 37929363329](https://github.com/mahdimarzooghi4-debug/flag-academy/actions/runs/37929363329) SUCCESS, including live OIDC + PostgreSQL draft versioning tests. PR #21 remains Draft/Open/Unmerged; no Stage/Production admission.
