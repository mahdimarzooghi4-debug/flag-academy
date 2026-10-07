# P22-02 — Governed Dataset Builder

**Status:** COMPLETE  
**Date:** 2026-10-07  
**Sprint:** 22 — Parcham AI Foundation  
**PR:** #20 — Draft/Open/Unmerged  
**Implementation HEAD before this record:** `a401a6558c0dfc5b13c47700a00cdcdbc6fc2a63`  
**Verified CI:** Run `37612777745` — SUCCESS

## Decision boundary

Operational Human review is **not** AI-learning approval.

The following facts do not, by themselves, authorize AI training use:

- an EvidenceCase being accepted;
- a BehaviourPattern being reviewed;
- a Flag Profile update being applied;
- a CapabilityClaim changing;
- a Gate review completing.

P22-02 therefore does not subscribe to those domain events.

The Dataset Builder consumes only the explicit governance output:

`ai.learning_input_approved.v1`

No source-specific approval producer is invented in this slice. Until a governed upstream
producer emits that contract, operational data remains outside the AI Dataset path.

## Intake contract

Each approved learning input pins:

- organization context;
- Dataset name and purpose;
- source policy key and version;
- source type, reference and optional source version;
- SHA-256 digest of the approved source payload;
- explicit approval reference;
- exact approval event ID;
- data classification;
- approving actor type/reference;
- approval time;
- trace lineage.

The Builder accepts references and content digests, not an arbitrary raw-record upload API.

## Dataset identity and versioning

Dataset identity is tenant scoped by:

`organization_context_id + name + purpose`

Every novel approved governed input creates one immutable Dataset Version.

Dataset Versions form an append-only parent chain through
`parent_dataset_version_id`. Each version records its immutable delta item and its digest
pins the parent digest plus the new provenance digest.

No prior Dataset Version is rewritten.

## Idempotency and concurrency

The Builder uses a PostgreSQL transaction advisory lock derived from the tenant-scoped
Dataset identity.

Idempotency has two independent protections:

1. the same approval reference replayed with the same semantic provenance returns the
   existing Dataset Version;
2. a new approval reference/event for the same source + policy + source version + payload
   digest is semantic re-approval and also returns the existing Dataset Version.

Reusing one approval reference for different semantic provenance fails closed with
`AI_LEARNING_APPROVAL_REFERENCE_REUSED`.

The NATS consumer also uses the platform Inbox for exact event-delivery idempotency.

## Transaction boundary

The Dataset Builder does not commit independently.

The NATS consumer owns the transaction so these records commit atomically:

- Inbox receipt;
- AI Learning Source Approval;
- Dataset / Dataset Version / Dataset Item;
- `ai.dataset_version_created.v1` Domain Event;
- transactional Outbox record.

The Dataset-created event uses the exact AI-learning approval event as its
`causation_id`.

## Bounded-context isolation

AI Dataset persistence has no foreign keys to:

- Evidence;
- Patterns;
- Flag Profile;
- Gate Assessment;
- Learning;
- Mission Runtime.

Source identifiers are opaque provenance references. All relational foreign keys remain
inside `ai_control_plane`.

## Verification

CI Run `37612777745` passed on
`a401a6558c0dfc5b13c47700a00cdcdbc6fc2a63`:

- backend lint — PASS;
- backend type check — PASS;
- 198 backend tests — PASS;
- migration validation through `0025` — PASS;
- development seed — PASS;
- OpenAPI export — PASS;
- frontend API type generation — PASS;
- frontend type check/tests/build — PASS;
- Live OIDC browser E2E — PASS;
- governed Dataset Builder NATS acceptance — PASS.

The real NATS acceptance produced:

- `datasets=1`
- `approvals=1`
- `versions=1`
- `items=1`
- `inbox=2`
- `dataset_events=1`
- `semantic_reapproval_dedup=PASS`
- `duplicate_delivery_idempotency=PASS`
- `reviewed_domain_events_implicit_approval=FORBIDDEN`

## Explicit exclusions

P22-02 does not add:

- a generic Dataset write API;
- automatic conversion of accepted/reviewed operational data into training data;
- source-specific approval policy or approval producer;
- Training Run execution;
- Model Artifact production;
- Gemma, Transformers, PyTorch, PEFT or safetensors;
- offline Evaluation execution;
- runtime inference;
- automatic promotion or Production activation;
- Gate/Profile/Responsibility/Appointment mutation.

## Result

**P22-02 — Governed Dataset Builder: COMPLETE**

The next planned slice is **P22-03 — Training Run Control Plane**.

P22-03 may consume only an exact immutable Dataset Version produced by this governed
Dataset path. It must not introduce an external trainer endpoint or allow failed/incomplete
training to create a Model Version.
