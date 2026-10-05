# Sprint 17 — Deterministic Experiment Runtime Code Review

**Status:** PASS  
**Date:** 2026-10-05  
**PR:** #15 — Sprint 17: deterministic experiment runtime  
**Reviewed implementation head:** `2544dbcedc060014d133de8183f1fa03483c3819`  
**CI:** Run `37324386889` — SUCCESS

## Review scope

- bounded Mission-Version-pinned `experiment_options`
- DEC-200 preregistered experiment contract
- ethical review requirement
- Candidate command boundary
- Engine-owned deterministic measurements
- no automatic interpretation/verdict/recommendation
- nested candidate payload fail-closed projection
- World optimistic concurrency
- Candidate accountability invariant
- reserved Evidence/Profile/Competency/Gate namespaces
- factual Observation boundary
- scheduled-effect cancellation ordering
- state-trigger fixed-point evaluation
- real Candidate UI
- live OIDC E2E
- Stage SQL evidence

## Findings

### CR-17-001 — Nested experiment payloads required fail-closed candidate projection

**Severity:** Blocking before merge  
**Status:** RESOLVED

Top-level event/observation allowlists were not sufficient by themselves because `contract` and `result` are nested objects. Historical or malformed runtime rows could otherwise carry nested interpretation keys through an allowed top-level `result` field.

Resolution:

- `candidate_event_payload` revalidates candidate-visible experiment contract and result;
- `candidate_observation_payload` revalidates experiment result;
- malformed nested contract/result fields are dropped fail-closed;
- tests prove `verdict` / `interpretation` nested payloads do not reach Candidate projection.

### CR-17-002 — Experiment contract is frozen before Result

**Status:** PASS

`experiment_contract_valid` requires the preregistered contract to contain:

- hypothesis
- population
- intervention
- control/comparison
- primary and secondary metrics
- guardrails
- baseline
- expected effect
- decision rule
- duration/stopping rule
- known risks
- approved ethical review

Candidate submits only `experiment_code` and rationale. Candidate cannot rewrite the contract or Result.

### CR-17-003 — Result is descriptive measurement only

**Status:** PASS

The Engine-owned Result has an exact schema:

- `control_measurements`
- `treatment_measurements`
- `noise_context`
- `observed_events`

Recursive validation rejects interpretation-bearing keys including:

- `interpretation`
- `verdict`
- `evidence_strength`
- `capability_score`
- `gate_decision`
- `recommendation`
- `decision_recommendation`

No success/failure label or decision recommendation is generated for the Candidate.

### CR-17-004 — Evidence/Profile/Gate isolation

**Status:** PASS

RUN_EXPERIMENT changes Canonical Simulation State and creates factual `EXPERIMENT_RESULT_OBSERVED`. It does not create Accepted Evidence, change Proof, update Capability/Competency scores, decide a Gate or mutate Flag Profile.

### CR-17-005 — Deterministic source of truth and concurrency

**Status:** PASS

Execution requires:

- RUNNING Mission Instance
- expected World State version
- exact option resolution from the pinned Mission Version
- Engine-owned result and world effect
- reserved namespace validation
- Candidate accountability preservation

Candidate cannot submit Result, Dataset, state patch or consequence rule.

### CR-17-006 — Post-mutation ordering

**Status:** PASS

After experiment completion the runtime preserves established ordering:

1. scheduled-effect cancellation
2. state-triggered fixed-point evaluation

### CR-17-007 — Real workflow verification

**Status:** PASS

CI Run `37324386889` passed on reviewed head:

- backend lint — PASS
- backend type check — PASS
- backend unit tests — PASS
- migrations — PASS
- OpenAPI export — PASS
- frontend type check — PASS
- frontend unit tests — PASS
- frontend build — PASS
- live OIDC browser E2E — PASS

The browser path verifies:

- preregistered contract is visible before execution;
- ethical review status is APPROVED;
- Candidate submits bounded RUN_EXPERIMENT;
- `mission.experiment_status=COMPLETED`;
- Control error rate is 13 and Treatment error rate is 5;
- guardrail measurement remains visible as raw measurement;
- `EXPERIMENT_RESULT_OBSERVED` is visible;
- no `verdict`, `interpretation` or `evidence_strength` is exposed;
- raw `world_effect_applied` remains hidden;
- later ALLOCATE_RESOURCE / DELEGATE / ESCALATE / DECIDE remains operational;
- Candidate remains UNPROVEN.

## Review conclusion

No blocking findings remain.

Sprint 17 implementation is approved for merge **only after** CI for the commit containing this review document is fully Green.
