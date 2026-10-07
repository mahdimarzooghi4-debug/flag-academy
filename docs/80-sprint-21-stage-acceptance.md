# 80 — Sprint 21 Stage Acceptance

**Status:** PASS  
**Date:** 2026-10-07  
**Accepted Implementation Commit:** `4d8ca8b35faf40bba8fa39571f946228df5943e4`

## Accepted runs

- CI: `37601470955` — PASS
- Stage Acceptance: `37601470947` — PASS
- Evidence artifact: `stage-acceptance-evidence`
- Artifact ID: `11473072199`
- Artifact digest: `sha256:5940ae31348ab2f810e2c9bce6a719f7bb0f732ad522b430e41707e576ad4c17`

## Gate Assessment acceptance evidence

```text
commit=4d8ca8b35faf40bba8fa39571f946228df5943e4
gate_definitions=5
gate_definition_versions=5
gate_assessments=1
gate_profile_snapshots=1
gate_snapshot_claims=1
gate_snapshot_pattern_refs=1
gate_snapshot_evidence_refs=1
gate_reviews=1
gate_review_decisions=1
gate_review_completed_events=1
published_gate_review_completed_events=1
gate_snapshot_immutable_triggers=4
gate_cross_context_foreign_keys=0
gate_incomplete_snapshot_claims=0
gate_incomplete_snapshot_patterns=0
gate_event_outbox_mismatches=0
gate_nonhuman_review_events=0
gate_event_lineage_mismatches=0
gate_claim_mutations_after_review=0
gate_downstream_decision_events=0
gate_pass_with_evidence_gap=1
gate_state_vocabulary=UNPROVEN+PASS+AT_RISK+REVIEW_REQUIRED+PASS_CONFIRMED+FAIL+REMEDIATION+REASSESSMENT
gate_code_vocabulary=A+B+C+D+E
gate_snapshot_immutability=DB_TRIGGER_ENFORCED
gate_snapshot_lineage=CLAIM+PATTERN+EVIDENCE+INTERPRETATION+OBSERVATION+SOURCE
gate_open_review_idempotent_replay=PASS
gate_decision_idempotent_replay=PASS
gate_human_decision_only=PASS_CONFIRMED_OR_FAIL+PERSON+RATIONALE
gate_missing_evidence_auto_fail=FORBIDDEN
gate_event_delivery=DOMAIN_EVENT+OUTBOX+PUBLISHED
gate_ai_system_direct_decision=FORBIDDEN
gate_capability_claim_mutation=FORBIDDEN
gate_responsibility_flagboard_appointment_mutation=FORBIDDEN
browser_oidc_acceptance=PASS
```

## Verified runtime path

**Current Flag Profile → immutable Gate ProfileSnapshot → Open Human Review → pinned Gate Definition + full Profile lineage inspection → accountable Human Decision → `gate.review_completed.v1`**

Verified in the ephemeral Stage environment:

- exactly five canonical Gate definitions A–E exist;
- GateAssessment uses the canonical Sprint 21 state vocabulary;
- consequential Gate Review pins a Gate-owned immutable ProfileSnapshot;
- ProfileSnapshot rows, Claim rows, Pattern references and Evidence references are protected from UPDATE/DELETE by database triggers;
- every accepted snapshot Claim has Pattern lineage and every accepted snapshot Pattern has Evidence lineage;
- the pinned lineage remains reconstructable as Claim → Pattern → Evidence → Interpretation → Observation → Source;
- Gate consumes Current Flag Profile through the Flag-Profile-owned public snapshot contract rather than through Flag Profile persistence models;
- Open Review is versioned and idempotent; replay with the same request returns the same Review and same ProfileSnapshot without creating another snapshot;
- final Review decision is versioned and idempotent; replay with the same request returns the same Human decision without creating another decision or event;
- a final consequential decision is limited to `PASS_CONFIRMED` or `FAIL`, requires a PERSON reviewer and non-empty rationale, and is tied to the exact GateDefinitionVersion and ProfileSnapshot version inspected by that reviewer;
- `gate.review_completed.v1` is recorded as Domain Event + Outbox and is published;
- event actor, decision state and ProfileSnapshot lineage match the persisted Human decision;
- no non-human Gate review-completion event was accepted;
- missing or remaining Evidence does not automatically fail a Gate: the accepted Stage run contains a `PASS_CONFIRMED` decision while `next_evidence_needed` remains non-empty;
- the Gate schema has zero cross-bounded-context foreign keys;
- Gate review produced zero direct CapabilityClaim mutation and zero Responsibility, Flag Board or Appointment decision event;
- Candidate projection remains allowlist-only and Live OIDC acceptance confirms Assessor-only lineage is not exposed to the Candidate.

## Recovery and reassessment contract

The Sprint 21 recovery state machine remains:

**FAIL → REMEDIATION → REASSESSMENT → PASS / FAIL**

CI/domain acceptance verifies:

- Remediation can begin only from a Human-backed `FAIL`;
- Reassessment pins a new immutable Current Flag Profile snapshot instead of rewriting the historical Review snapshot;
- reassessment final decision is Human-only and limited to `PASS` or `FAIL`;
- prior Review, snapshot and decision history remains append-only;
- reassessment cannot mutate CapabilityClaim, ResponsibilityRecommendation, Flag Board or Appointment;
- no score, threshold or automatic recovery rule is introduced.

## Bounded-context and governance verification

- Gate Assessment owns GateDefinition, GateDefinitionVersion, GateAssessment, Gate Review history, Gate-owned ProfileSnapshots and recovery/reassessment history.
- Gate Assessment does not directly import Flag Profile persistence models.
- Cross-context identifiers copied into Gate snapshots are opaque lineage references, not database foreign keys.
- No numeric threshold, weighted average, readiness score, black-box progression rule or auto-evaluator is part of Sprint 21.
- AI/System/Event cannot directly produce `PASS`, `PASS_CONFIRMED` or `FAIL`.
- `INSUFFICIENT EVIDENCE` is not equivalent to Gate failure.
- Sprint 21 does not create ResponsibilityRecommendation, decide Flag Board/Appointment, or activate any Parcham AI runtime.
- External AI APIs remain outside the Sprint 21 runtime.
- Production deployment is not part of this acceptance.

## Result

> **Sprint 21 — Gate Assessment Foundation: ACCEPTED**

Parcham now has an auditable, tenant-scoped, versioned and human-governed Gate Assessment foundation with canonical Gate A–E definitions, immutable point-in-time Profile lineage, accountable consequential decisions, governed recovery/reassessment, candidate-safe transparency, transactional event publication and explicit bounded-context isolation.
