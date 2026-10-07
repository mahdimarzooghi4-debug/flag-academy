from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest

from app.curriculum.domain import CAPABILITY_CODES, LearningState, ProofState
from app.errors import AppError
from app.evidence.domain import (
    EvidenceCaseStatus,
    case_transition_allowed,
    interpretation_contract_valid,
)
from app.flag_profile.application import (
    ApplyProfileUpdateCaseCommand,
    ApproveProfileUpdateCaseCommand,
    CreateProfileUpdateCaseCommand,
    ProfileUpdatePatternInput,
    RequestProfileUpdateReviewCommand,
    _applied_retry_matches,
    _approval_retry_matches,
    _claim_snapshot_matches_current,
    _new_profile_claim_changed_event,
    _require_create_contract,
    _require_profile_update_approval_contract,
    _require_profile_update_create_expected_version,
    _require_profile_update_expected_version,
    _review_request_retry_matches,
)
from app.flag_profile.domain import (
    CapabilityClaimState,
    CapabilityLevel,
    ClaimPatternRelationship,
    ProfileUpdateCaseState,
    profile_update_transition_allowed,
)
from app.flag_profile.models import CapabilityClaim, ProfileUpdateCase
from app.gate_assessment.domain import (
    GATE_DEFINITION_REGISTRY,
    GateAssessmentState,
    GateCode,
    gate_transition_allowed,
)
from app.journey.domain import CandidateJourneyState
from app.learning.domain import (
    LearningPhase,
    LearningUnitProgressState,
    LearningUnitType,
    PracticeAttemptStatus,
    PracticeKind,
    PracticeReplayState,
    SubmissionStatus,
)
from app.mission_design.domain import (
    MissionDifficulty,
    MissionMode,
    MissionVersionStatus,
    transition_allowed,
)
from app.mission_runtime.domain import (
    MissionActionType,
    MissionAssignmentStatus,
    MissionInstanceStatus,
    apply_actor_effect,
    apply_world_effect,
    assignment_transition_allowed,
    candidate_event_payload,
    candidate_event_visible,
    candidate_observation_payload,
    candidate_observation_visible,
    canonical_resource_balance_matches,
    delegation_preserves_candidate_accountability,
    experiment_contract_valid,
    experiment_result_valid,
    preserves_candidate_accountability,
    project_candidate_visible_state,
    resource_allocation_transition_valid,
    runtime_transition_allowed,
)
from app.patterns.application import (
    AcceptedEvidenceSnapshot,
    _accepted_snapshot_matches_context,
    _new_pattern_updated_event,
    _require_create_expected_version,
    _require_pattern_candidate_create_expected_version,
    _require_pattern_review_expected_version,
    _reviewed_pattern_status_valid,
)
from app.patterns.contracts import _source_contract
from app.patterns.domain import (
    PatternEvidenceRelationship,
    PatternStatus,
    evidence_set_contract_valid,
    pattern_candidate_contract_valid,
)
from app.patterns.models import BehaviourPattern
from app.platform.events import new_event


def test_pm_curriculum_has_15_capabilities() -> None:
    assert len(CAPABILITY_CODES) == 15
    assert len(set(CAPABILITY_CODES)) == 15


def test_learning_completion_is_not_proof() -> None:
    assert LearningState.LEARNING_COMPLETED.value != ProofState.PROVEN.value


def test_learning_experience_types_are_explicit() -> None:
    assert LearningUnitType.RESOURCE.value == "RESOURCE"
    assert LearningPhase.PRE_WORK.value == "PRE_WORK"
    assert LearningPhase.PRACTICE.value == "PRACTICE"
    assert PracticeKind.GUIDED_EXERCISE.value == "GUIDED_EXERCISE"
    assert PracticeKind.CASE_STUDY.value == "CASE_STUDY"
    assert LearningUnitProgressState.IN_PROGRESS.value == "IN_PROGRESS"
    assert LearningUnitProgressState.COMPLETED.value == "COMPLETED"
    assert PracticeAttemptStatus.SUBMITTED.value == "SUBMITTED"
    assert PracticeAttemptStatus.FEEDBACK_PROVIDED.value == "FEEDBACK_PROVIDED"
    assert PracticeReplayState.WAITING_FOR_FEEDBACK.value == "WAITING_FOR_FEEDBACK"
    assert PracticeReplayState.REPLAY_AVAILABLE.value == "REPLAY_AVAILABLE"
    assert SubmissionStatus.FEEDBACK_PROVIDED.value == "FEEDBACK_PROVIDED"


def test_candidate_journey_states_are_explicit() -> None:
    assert CandidateJourneyState.ACTIVE.value == "ACTIVE"
    assert CandidateJourneyState.WITHDRAWN.value == "WITHDRAWN"


def test_domain_event_envelope_is_versioned_and_traceable() -> None:
    event = new_event(
        event_type="candidate.journey_created.v1",
        aggregate_type="CandidateJourney",
        aggregate_id=UUID("00000000-0000-0000-0000-000000000401"),
        aggregate_version=1,
        actor={"type": "SYSTEM", "id": "test"},
        organization_context_id=UUID("00000000-0000-0000-0000-000000000001"),
        data_classification="INTERNAL",
        payload={"candidate_id": "candidate-1"},
        trace_id="trace-test",
    )
    payload = event.model_dump(mode="json")
    assert payload["event_version"] == 1
    assert payload["trace_id"] == "trace-test"
    assert payload["event_type"] == "candidate.journey_created.v1"


def test_mission_design_lifecycle_is_explicit() -> None:
    assert MissionMode.PRACTICE.value == "PRACTICE"
    assert MissionDifficulty.D3.value == "D3"
    assert transition_allowed(MissionVersionStatus.DRAFT.value, MissionVersionStatus.PILOT.value)
    assert transition_allowed(MissionVersionStatus.PILOT.value, MissionVersionStatus.VALIDATED.value)
    assert transition_allowed(MissionVersionStatus.VALIDATED.value, MissionVersionStatus.ACTIVE.value)
    assert not transition_allowed(MissionVersionStatus.DRAFT.value, MissionVersionStatus.ACTIVE.value)


def test_mission_runtime_lifecycle_and_action_contract_are_explicit() -> None:
    assert runtime_transition_allowed(
        MissionInstanceStatus.CREATED.value,
        MissionInstanceStatus.ELIGIBILITY_CHECK.value,
    )
    assert runtime_transition_allowed(
        MissionInstanceStatus.READY.value,
        MissionInstanceStatus.RUNNING.value,
    )
    assert runtime_transition_allowed(
        MissionInstanceStatus.RUNNING.value,
        MissionInstanceStatus.COMPLETED.value,
    )
    assert MissionActionType.REQUEST_INFORMATION.value == "REQUEST_INFORMATION"
    assert MissionActionType.COMMUNICATE.value == "COMMUNICATE"
    assert MissionActionType.NO_ACTION.value == "NO_ACTION"
    assert MissionActionType.DECIDE.value == "DECIDE"
    assert runtime_transition_allowed(
        MissionInstanceStatus.RUNNING.value,
        MissionInstanceStatus.TIME_EXPIRED.value,
    )


def test_mission_runtime_world_effect_is_deterministic_and_cannot_touch_profile() -> None:
    initial = {
        "technical": {"rollback_started": False},
        "risk": {"level": "HIGH"},
    }
    effect = {
        "technical": {"rollback_started": True},
        "risk": {"level": "MEDIUM"},
    }
    assert apply_world_effect(initial, effect) == {
        "technical": {"rollback_started": True},
        "risk": {"level": "MEDIUM"},
    }
    assert initial["technical"]["rollback_started"] is False

    try:
        apply_world_effect(initial, {"profile": {"proof_state": "PROVEN"}})
    except ValueError as exc:
        assert "reserved namespaces" in str(exc)
    else:
        raise AssertionError("Mission Runtime must reject direct Profile mutation.")


def test_mission_assignment_lifecycle_is_explicit() -> None:
    assert assignment_transition_allowed(
        MissionAssignmentStatus.ASSIGNED.value,
        MissionAssignmentStatus.STARTED.value,
    )
    assert assignment_transition_allowed(
        MissionAssignmentStatus.STARTED.value,
        MissionAssignmentStatus.COMPLETED.value,
    )
    assert not assignment_transition_allowed(
        MissionAssignmentStatus.COMPLETED.value,
        MissionAssignmentStatus.STARTED.value,
    )


def test_candidate_world_projection_is_allowlist_only() -> None:
    canonical = {
        "business": {"rollout_status": "DEGRADED"},
        "technical": {
            "error_rate_percent": 13,
            "rollback_available": True,
            "root_cause_code": "DOWNSTREAM_DEPENDENCY",
        },
        "risk": {"level": "HIGH"},
    }
    projected = project_candidate_visible_state(
        canonical,
        [
            "business.rollout_status",
            "technical.error_rate_percent",
            "technical.rollback_available",
            "risk.level",
        ],
    )
    assert projected == {
        "business": {"rollout_status": "DEGRADED"},
        "technical": {
            "error_rate_percent": 13,
            "rollback_available": True,
        },
        "risk": {"level": "HIGH"},
    }
    assert "root_cause_code" not in projected["technical"]


def test_candidate_event_payload_is_fail_closed() -> None:
    assert candidate_event_visible("decision.committed")
    assert not candidate_event_visible("internal.secret_event")

    decision_payload = {
        "decision_code": "ROLLBACK_AND_RECOVER",
        "effect_applied": {
            "technical": {"root_cause_code": "DOWNSTREAM_DEPENDENCY"}
        },
    }
    assert candidate_event_payload("decision.committed", decision_payload) == {
        "decision_code": "ROLLBACK_AND_RECOVER"
    }
    assert candidate_event_payload("internal.secret_event", {"secret": "x"}) == {}


def test_candidate_observation_visibility_is_explicit() -> None:
    assert candidate_observation_visible("DECISION_COMMITTED")
    assert not candidate_observation_visible("INTERNAL_WORLD_FACT")
    assert candidate_observation_payload(
        "DECISION_COMMITTED",
        {
            "decision_code": "ROLLBACK_AND_RECOVER",
            "world_version_before": 1,
            "world_version_after": 2,
            "hidden_root_cause": "DOWNSTREAM_DEPENDENCY",
        },
    ) == {
        "decision_code": "ROLLBACK_AND_RECOVER",
        "world_version_before": 1,
        "world_version_after": 2,
    }


def test_actor_effect_is_deterministic_and_cannot_touch_governance_state() -> None:
    initial = {
        "trust_toward_candidate": 35,
        "current_frustration": 70,
        "commitment": "CONDITIONAL",
        "private_escalation_threshold": "LOW",
    }
    effect = {
        "trust_toward_candidate": 60,
        "current_frustration": 40,
        "commitment": "SUPPORTIVE",
    }
    assert apply_actor_effect(initial, effect) == {
        "trust_toward_candidate": 60,
        "current_frustration": 40,
        "commitment": "SUPPORTIVE",
        "private_escalation_threshold": "LOW",
    }
    assert initial["trust_toward_candidate"] == 35

    try:
        apply_actor_effect(initial, {"profile": {"proof_state": "PROVEN"}})
    except ValueError as exc:
        assert "reserved keys" in str(exc)
    else:
        raise AssertionError("Actor Runtime must reject direct Profile mutation.")


def test_escalation_candidate_payload_hides_internal_effects() -> None:
    payload = {
        "actor_key": "business_sponsor",
        "escalation_code": "EXECUTIVE_RECOVERY_ESCALATION",
        "response": "Escalation accepted.",
        "world_version_before": 1,
        "world_version_after": 2,
        "actor_state_version_before": 2,
        "actor_state_version_after": 3,
        "world_effect_applied": {"stakeholder": {"executive_attention": "ENGAGED"}},
        "actor_effect_applied": {"commitment": "EXECUTIVE_SPONSORSHIP"},
    }
    assert candidate_event_visible("escalation.accepted")
    visible = candidate_event_payload("escalation.accepted", payload)
    assert visible["escalation_code"] == "EXECUTIVE_RECOVERY_ESCALATION"
    assert visible["world_version_after"] == 2
    assert "world_effect_applied" not in visible
    assert "actor_effect_applied" not in visible


def test_escalation_observation_is_explicit_candidate_fact() -> None:
    assert candidate_observation_visible("ESCALATION_OBSERVED")
    visible = candidate_observation_payload(
        "ESCALATION_OBSERVED",
        {
            "actor_key": "business_sponsor",
            "escalation_code": "EXECUTIVE_RECOVERY_ESCALATION",
            "world_version_before": 1,
            "world_version_after": 2,
            "actor_state_version_before": 2,
            "actor_state_version_after": 3,
            "judgment": "strong leadership",
        },
    )
    assert "judgment" not in visible
    assert visible["actor_state_version_after"] == 3


def test_delegation_preserves_candidate_accountability() -> None:
    before = {
        "mission": {"accountability_owner": "CANDIDATE"},
        "delivery": {"recovery_coordinator": "CANDIDATE"},
    }
    accepted = {
        "mission": {"accountability_owner": "CANDIDATE", "delegation_status": "ACTIVE"},
        "delivery": {"recovery_coordinator": "DELIVERY_LEAD"},
    }
    transferred = {
        "mission": {"accountability_owner": "DELIVERY_LEAD"},
        "delivery": {"recovery_coordinator": "DELIVERY_LEAD"},
    }
    missing = {"mission": {"delegation_status": "ACTIVE"}}

    assert delegation_preserves_candidate_accountability(before, accepted)
    assert not delegation_preserves_candidate_accountability(before, transferred)
    assert not delegation_preserves_candidate_accountability(missing, missing)


def test_delegation_visibility_is_factual_and_fail_closed() -> None:
    assert candidate_event_visible("delegation.requested")
    assert candidate_event_visible("delegation.accepted")
    requested = candidate_event_payload(
        "delegation.requested",
        {
            "actor_key": "delivery_lead",
            "delegation_code": "DELEGATE_RECOVERY_COORDINATION",
            "rationale": "Delegate coordination while retaining accountability.",
            "hidden_rule": "DO_NOT_EXPOSE",
        },
    )
    assert requested["delegation_code"] == "DELEGATE_RECOVERY_COORDINATION"
    assert "hidden_rule" not in requested

    accepted = candidate_event_payload(
        "delegation.accepted",
        {
            "actor_key": "delivery_lead",
            "delegation_code": "DELEGATE_RECOVERY_COORDINATION",
            "response": "Accepted.",
            "world_version_before": 1,
            "world_version_after": 2,
            "actor_state_version_before": 1,
            "actor_state_version_after": 2,
            "world_effect_applied": {
                "delivery": {"recovery_coordinator": "DELIVERY_LEAD"},
            },
            "actor_effect_applied": {
                "delegated_responsibility": "RECOVERY_COORDINATION",
            },
        },
    )
    assert accepted["world_version_after"] == 2
    assert "world_effect_applied" not in accepted
    assert "actor_effect_applied" not in accepted

    assert candidate_observation_visible("DELEGATION_OBSERVED")
    observation = candidate_observation_payload(
        "DELEGATION_OBSERVED",
        {
            "actor_key": "delivery_lead",
            "delegation_code": "DELEGATE_RECOVERY_COORDINATION",
            "world_version_before": 1,
            "world_version_after": 2,
            "actor_state_version_before": 1,
            "actor_state_version_after": 2,
            "judgment": "good delegation",
        },
    )
    assert observation["actor_key"] == "delivery_lead"
    assert "judgment" not in observation


def test_canonical_resource_balance_requires_strict_integer() -> None:
    assert canonical_resource_balance_matches(1, 1)
    assert not canonical_resource_balance_matches(True, 1)
    assert not canonical_resource_balance_matches("1", 1)


def test_resource_allocation_arithmetic_is_balanced_and_nonnegative() -> None:
    assert resource_allocation_transition_valid(
        quantity=2,
        from_available=3,
        to_available=1,
        from_allocated=0,
        to_allocated=2,
    )
    assert not resource_allocation_transition_valid(
        quantity=4,
        from_available=3,
        to_available=-1,
        from_allocated=0,
        to_allocated=4,
    )
    assert not resource_allocation_transition_valid(
        quantity=2,
        from_available=3,
        to_available=2,
        from_allocated=0,
        to_allocated=2,
    )
    assert not resource_allocation_transition_valid(
        quantity=True,
        from_available=3,
        to_available=2,
        from_allocated=0,
        to_allocated=1,
    )


def test_resource_allocation_visibility_is_factual_and_fail_closed() -> None:
    assert candidate_event_visible("resource_allocation.requested")
    assert candidate_event_visible("resource_allocation.accepted")
    requested = candidate_event_payload(
        "resource_allocation.requested",
        {
            "resource_allocation_code": "ALLOCATE_TWO_ENGINEERS_TO_RECOVERY",
            "resource_type": "ENGINEERING_CAPACITY",
            "unit": "ENGINEER_EQUIVALENT",
            "quantity": 2,
            "target": "RECOVERY_EXECUTION",
            "rationale": "Commit scarce capacity to recovery.",
            "available_path": "resources.engineering_capacity.available_units",
        },
    )
    assert requested["quantity"] == 2
    assert "available_path" not in requested

    accepted = candidate_event_payload(
        "resource_allocation.accepted",
        {
            "resource_allocation_code": "ALLOCATE_TWO_ENGINEERS_TO_RECOVERY",
            "resource_type": "ENGINEERING_CAPACITY",
            "unit": "ENGINEER_EQUIVALENT",
            "quantity": 2,
            "target": "RECOVERY_EXECUTION",
            "response": "Accepted.",
            "from_available": 3,
            "to_available": 1,
            "from_allocated": 0,
            "to_allocated": 2,
            "world_version_before": 2,
            "world_version_after": 3,
            "available_path": "resources.engineering_capacity.available_units",
            "allocated_path": "delivery.recovery_capacity_units",
            "resource_cost_applied": {"engineering_capacity_units": 2},
            "world_effect_applied": {
                "resources": {"engineering_capacity": {"available_units": 1}},
            },
        },
    )
    assert accepted["to_available"] == 1
    assert accepted["to_allocated"] == 2
    assert "available_path" not in accepted
    assert "allocated_path" not in accepted
    assert "resource_cost_applied" not in accepted
    assert "world_effect_applied" not in accepted

    assert candidate_observation_visible("RESOURCE_ALLOCATION_OBSERVED")
    observation = candidate_observation_payload(
        "RESOURCE_ALLOCATION_OBSERVED",
        {
            "resource_allocation_code": "ALLOCATE_TWO_ENGINEERS_TO_RECOVERY",
            "resource_type": "ENGINEERING_CAPACITY",
            "unit": "ENGINEER_EQUIVALENT",
            "quantity": 2,
            "target": "RECOVERY_EXECUTION",
            "from_available": 3,
            "to_available": 1,
            "from_allocated": 0,
            "to_allocated": 2,
            "world_version_before": 2,
            "world_version_after": 3,
            "judgment": "good prioritization",
        },
    )
    assert observation["quantity"] == 2
    assert "judgment" not in observation


def test_scope_change_preserves_candidate_accountability() -> None:
    before = {
        "mission": {"accountability_owner": "CANDIDATE"},
        "delivery": {"scope": "FULL_ROLLOUT"},
    }
    accepted = {
        "mission": {
            "accountability_owner": "CANDIDATE",
            "scope_change_status": "ACTIVE",
        },
        "delivery": {"scope": "CRITICAL_CUSTOMERS_ONLY"},
    }
    transferred = {
        "mission": {"accountability_owner": "OPERATIONS"},
        "delivery": {"scope": "CRITICAL_CUSTOMERS_ONLY"},
    }

    assert preserves_candidate_accountability(before, accepted)
    assert not preserves_candidate_accountability(before, transferred)


def test_scope_change_visibility_is_factual_and_fail_closed() -> None:
    assert candidate_event_visible("scope_change.requested")
    assert candidate_event_visible("scope_change.accepted")
    requested = candidate_event_payload(
        "scope_change.requested",
        {
            "scope_change_code": "CRITICAL_CUSTOMERS_ONLY",
            "from_scope": "FULL_ROLLOUT",
            "to_scope": "CRITICAL_CUSTOMERS_ONLY",
            "rationale": "Reduce blast radius while keeping accountability.",
            "hidden_rule": "DO_NOT_EXPOSE",
        },
    )
    assert requested["scope_change_code"] == "CRITICAL_CUSTOMERS_ONLY"
    assert requested["from_scope"] == "FULL_ROLLOUT"
    assert requested["to_scope"] == "CRITICAL_CUSTOMERS_ONLY"
    assert "hidden_rule" not in requested

    accepted = candidate_event_payload(
        "scope_change.accepted",
        {
            "scope_change_code": "CRITICAL_CUSTOMERS_ONLY",
            "response": "Scope changed.",
            "scope_path": "delivery.scope",
            "from_scope": "FULL_ROLLOUT",
            "to_scope": "CRITICAL_CUSTOMERS_ONLY",
            "world_version_before": 2,
            "world_version_after": 3,
            "world_effect_applied": {
                "delivery": {"scope": "CRITICAL_CUSTOMERS_ONLY"},
            },
        },
    )
    assert accepted["world_version_after"] == 3
    assert accepted["from_scope"] == "FULL_ROLLOUT"
    assert accepted["to_scope"] == "CRITICAL_CUSTOMERS_ONLY"
    assert "scope_path" not in accepted
    assert "world_effect_applied" not in accepted

    assert candidate_observation_visible("SCOPE_CHANGE_OBSERVED")
    observation = candidate_observation_payload(
        "SCOPE_CHANGE_OBSERVED",
        {
            "scope_change_code": "CRITICAL_CUSTOMERS_ONLY",
            "from_scope": "FULL_ROLLOUT",
            "to_scope": "CRITICAL_CUSTOMERS_ONLY",
            "world_version_before": 2,
            "world_version_after": 3,
            "judgment": "good scope decision",
        },
    )
    assert observation["scope_change_code"] == "CRITICAL_CUSTOMERS_ONLY"
    assert observation["from_scope"] == "FULL_ROLLOUT"
    assert observation["to_scope"] == "CRITICAL_CUSTOMERS_ONLY"
    assert "judgment" not in observation


def test_experiment_contract_requires_preregistration_and_ethics() -> None:
    contract = {
        "hypothesis": "Canary reduces error rate.",
        "population": "10% traffic",
        "intervention": "rollback canary",
        "control_comparison": "degraded path",
        "primary_metrics": ["error_rate_percent"],
        "secondary_metrics": ["customer_impact_percent"],
        "guardrails": ["customer_impact_percent<=2"],
        "baseline": {"error_rate_percent": 13},
        "expected_effect": "lower error rate",
        "decision_rule": "Candidate interprets measurements before later action.",
        "duration_stopping_rule": "15 minutes or guardrail breach",
        "known_risks": ["short_window_noise"],
        "ethical_review": {
            "status": "APPROVED",
            "summary": "No sensitive personal data.",
            "risk_categories": [],
        },
    }
    assert experiment_contract_valid(contract)

    missing_rule = dict(contract)
    missing_rule.pop("decision_rule")
    assert not experiment_contract_valid(missing_rule)

    rejected_ethics = dict(contract)
    rejected_ethics["ethical_review"] = {
        "status": "REJECTED",
        "summary": "Risk not approved.",
        "risk_categories": ["TRUST"],
    }
    assert not experiment_contract_valid(rejected_ethics)


def test_experiment_result_is_measurement_only() -> None:
    result = {
        "control_measurements": {"error_rate_percent": 13},
        "treatment_measurements": {"error_rate_percent": 5},
        "noise_context": ["short window"],
        "observed_events": ["No guardrail breach observed."],
    }
    assert experiment_result_valid(result)

    interpreted = dict(result)
    interpreted["interpretation"] = "SUCCESS"
    assert not experiment_result_valid(interpreted)

    nested_verdict = dict(result)
    nested_verdict["noise_context"] = [{"verdict": "GOOD"}]
    assert not experiment_result_valid(nested_verdict)


def test_experiment_visibility_is_factual_and_hides_world_effect() -> None:
    assert candidate_event_visible("experiment.requested")
    assert candidate_event_visible("experiment.completed")
    completed = candidate_event_payload(
        "experiment.completed",
        {
            "experiment_code": "RECOVERY_CANARY",
            "method": "CONTROLLED_CANARY",
            "response": "Measurements recorded.",
            "contract": {"hypothesis": "bounded"},
            "result": {
                "control_measurements": {"error_rate_percent": 13},
                "treatment_measurements": {"error_rate_percent": 5},
                "noise_context": [],
                "observed_events": [],
            },
            "world_effect_applied": {"mission": {"experiment_status": "COMPLETED"}},
            "world_version_before": 2,
            "world_version_after": 3,
        },
    )
    assert completed["experiment_code"] == "RECOVERY_CANARY"
    assert "result" in completed
    assert "contract" not in completed
    assert "world_effect_applied" not in completed

    malformed_completed = candidate_event_payload(
        "experiment.completed",
        {
            "experiment_code": "RECOVERY_CANARY",
            "method": "CONTROLLED_CANARY",
            "result": {
                "control_measurements": {"error_rate_percent": 13},
                "treatment_measurements": {"error_rate_percent": 5},
                "noise_context": [],
                "observed_events": [],
                "verdict": "SUCCESS",
            },
        },
    )
    assert "result" not in malformed_completed

    assert candidate_observation_visible("EXPERIMENT_RESULT_OBSERVED")
    observed = candidate_observation_payload(
        "EXPERIMENT_RESULT_OBSERVED",
        {
            "experiment_code": "RECOVERY_CANARY",
            "method": "CONTROLLED_CANARY",
            "result": {
                "control_measurements": {"error_rate_percent": 13},
                "treatment_measurements": {"error_rate_percent": 5},
                "noise_context": [],
                "observed_events": [],
            },
            "world_version_before": 2,
            "world_version_after": 3,
            "evidence_strength": "HIGH",
        },
    )
    assert observed["world_version_after"] == 3
    assert "evidence_strength" not in observed

    malformed_observed = candidate_observation_payload(
        "EXPERIMENT_RESULT_OBSERVED",
        {
            "experiment_code": "RECOVERY_CANARY",
            "method": "CONTROLLED_CANARY",
            "result": {
                "control_measurements": {"error_rate_percent": 13},
                "treatment_measurements": {"error_rate_percent": 5},
                "noise_context": [],
                "observed_events": [],
                "interpretation": "POSITIVE",
            },
        },
    )
    assert "result" not in malformed_observed


def test_scheduled_effect_payload_hides_internal_effect() -> None:
    assert candidate_event_visible("scheduled_effect.created")
    assert candidate_event_visible("scheduled_effect.applied")
    visible = candidate_event_payload(
        "scheduled_effect.applied",
        {
            "effect_code": "EXECUTIVE_CHECKPOINT_DUE",
            "label": "Executive recovery checkpoint",
            "due_at": "2026-10-05T10:00:00+00:00",
            "trigger_mode": "DUE_AT",
            "effect_applied": {
                "stakeholder": {"executive_checkpoint": "DUE"},
            },
            "world_version_before": 2,
            "world_version_after": 3,
        },
    )
    assert visible["effect_code"] == "EXECUTIVE_CHECKPOINT_DUE"
    assert visible["world_version_after"] == 3
    assert visible["trigger_mode"] == "DUE_AT"
    assert "effect_applied" not in visible


def test_scheduled_effect_observation_is_factual_and_explicit() -> None:
    assert candidate_observation_visible("SCHEDULED_EFFECT_OBSERVED")
    visible = candidate_observation_payload(
        "SCHEDULED_EFFECT_OBSERVED",
        {
            "effect_code": "EXECUTIVE_CHECKPOINT_DUE",
            "due_at": "2026-10-05T10:00:00+00:00",
            "trigger_mode": "DUE_AT",
            "world_version_before": 2,
            "world_version_after": 3,
            "judgment": "candidate waited too long",
        },
    )
    assert "judgment" not in visible
    assert visible["world_version_before"] == 2
    assert visible["world_version_after"] == 3


def test_no_action_and_timeout_visibility_are_explicit() -> None:
    assert candidate_event_visible("no_action.committed")
    assert candidate_event_visible("mission.time_expired")
    assert candidate_observation_visible("NO_ACTION_OBSERVED")
    assert candidate_observation_visible("MISSION_TIME_EXPIRED")

    no_action = candidate_event_payload(
        "no_action.committed",
        {
            "no_action_code": "WAIT_30_MINUTES",
            "reasoning": "Wait for more signal.",
            "simulation_time_before": "2026-10-05T10:00:00+00:00",
            "simulation_time_after": "2026-10-05T10:30:00+00:00",
            "hidden_policy": "DO_NOT_EXPOSE",
        },
    )
    assert "hidden_policy" not in no_action
    assert no_action["no_action_code"] == "WAIT_30_MINUTES"

    timeout = candidate_observation_payload(
        "MISSION_TIME_EXPIRED",
        {
            "effect_code": "RECOVERY_DECISION_DEADLINE",
            "expired_at": "2026-10-05T10:30:00+00:00",
            "world_version_before": 3,
            "world_version_after": 4,
            "judgment": "poor decision making",
        },
    )
    assert timeout["effect_code"] == "RECOVERY_DECISION_DEADLINE"
    assert "judgment" not in timeout


def test_scheduled_effect_cancellation_visibility_is_fail_closed() -> None:
    assert candidate_event_visible("scheduled_effect.cancelled")
    visible = candidate_event_payload(
        "scheduled_effect.cancelled",
        {
            "effect_code": "RECOVERY_DECISION_DEADLINE",
            "label": "Recovery decision deadline",
            "due_at": "2026-10-05T10:30:00+00:00",
            "cancelled_at": "2026-10-05T10:18:00+00:00",
            "reason_code": "DECISION_COMMITTED",
            "cancel_condition_matched": {
                "type": "WORLD_STATE_EQUALS",
                "path": "mission.decision_status",
                "equals": "COMMITTED",
            },
        },
    )
    assert visible["reason_code"] == "DECISION_COMMITTED"
    assert "cancel_condition_matched" not in visible

    assert candidate_observation_visible("SCHEDULED_EFFECT_CANCELLED_OBSERVED")
    observation = candidate_observation_payload(
        "SCHEDULED_EFFECT_CANCELLED_OBSERVED",
        {
            "effect_code": "RECOVERY_DECISION_DEADLINE",
            "due_at": "2026-10-05T10:30:00+00:00",
            "cancelled_at": "2026-10-05T10:18:00+00:00",
            "reason_code": "DECISION_COMMITTED",
            "world_version": 4,
            "judgment": "good timing",
        },
    )
    assert observation["world_version"] == 4
    assert "judgment" not in observation


def test_state_triggered_effect_visibility_hides_internal_condition() -> None:
    visible = candidate_event_payload(
        "scheduled_effect.applied",
        {
            "effect_code": "RECOVERY_COMMITMENT_BROADCAST",
            "label": "Recovery commitment broadcast",
            "due_at": None,
            "trigger_mode": "STATE_TRIGGERED",
            "effect_applied": {
                "stakeholder": {"recovery_signal": "BROADCAST"},
            },
            "trigger_condition_matched": {
                "type": "WORLD_STATE_EQUALS",
                "path": "mission.decision_status",
                "equals": "COMMITTED",
            },
            "world_version_before": 4,
            "world_version_after": 5,
        },
    )
    assert visible["trigger_mode"] == "STATE_TRIGGERED"
    assert visible["due_at"] is None
    assert "effect_applied" not in visible
    assert "trigger_condition_matched" not in visible

    observation = candidate_observation_payload(
        "SCHEDULED_EFFECT_OBSERVED",
        {
            "effect_code": "RECOVERY_COMMITMENT_BROADCAST",
            "due_at": None,
            "trigger_mode": "STATE_TRIGGERED",
            "world_version_before": 4,
            "world_version_after": 5,
            "judgment": "strong recovery leadership",
        },
    )
    assert observation["trigger_mode"] == "STATE_TRIGGERED"
    assert "judgment" not in observation


def test_evidence_case_review_lifecycle_is_explicit() -> None:
    assert case_transition_allowed(
        EvidenceCaseStatus.DRAFT.value,
        EvidenceCaseStatus.SUBMITTED.value,
    )
    assert case_transition_allowed(
        EvidenceCaseStatus.SUBMITTED.value,
        EvidenceCaseStatus.UNDER_REVIEW.value,
    )
    assert case_transition_allowed(
        EvidenceCaseStatus.UNDER_REVIEW.value,
        EvidenceCaseStatus.NEEDS_CONTEXT.value,
    )
    assert case_transition_allowed(
        EvidenceCaseStatus.NEEDS_CONTEXT.value,
        EvidenceCaseStatus.UNDER_REVIEW.value,
    )
    assert case_transition_allowed(
        EvidenceCaseStatus.UNDER_REVIEW.value,
        EvidenceCaseStatus.ACCEPTED.value,
    )
    assert not case_transition_allowed(
        EvidenceCaseStatus.ACCEPTED.value,
        EvidenceCaseStatus.UNDER_REVIEW.value,
    )


def test_evidence_interpretation_contract_requires_links_and_qualitative_confidence() -> None:
    interpretation = {
        "behaviour_code": "METRIC_REASONING",
        "behaviour_description": "Candidate distinguishes measurement from interpretation.",
        "signal": "POSITIVE",
        "scope": "MISSION",
        "confidence": "HIGH",
        "context_difficulty": "D3",
        "prompt_contamination": "NONE",
        "ai_contribution": "NONE",
        "mode": "ASSESSMENT",
        "rationale": "Observed result was handled as data rather than automatic proof.",
        "links": [
            {
                "target_type": "CAPABILITY",
                "target_ref": "METRICS_EXPERIMENTATION",
                "signal": "POSITIVE",
                "scope": "MISSION",
                "relevance": "HIGH",
                "confidence": "HIGH",
            }
        ],
    }
    assert interpretation_contract_valid(interpretation)

    missing_links = {**interpretation, "links": []}
    assert not interpretation_contract_valid(missing_links)

    numeric_confidence = {**interpretation, "confidence": 0.9}
    assert not interpretation_contract_valid(numeric_confidence)

    undeclared_ai = {**interpretation, "ai_contribution": "EXTERNAL_PROVIDER"}
    assert not interpretation_contract_valid(undeclared_ai)


def test_evidence_interpretation_rejects_unknown_target_type() -> None:
    interpretation = {
        "behaviour_code": "METRIC_REASONING",
        "behaviour_description": "Candidate distinguishes measurement from interpretation.",
        "signal": "NEUTRAL",
        "scope": "MISSION",
        "confidence": "MEDIUM",
        "context_difficulty": "D3",
        "prompt_contamination": "NONE",
        "ai_contribution": "NONE",
        "mode": "ASSESSMENT",
        "rationale": "Target links must remain explicit and bounded.",
        "links": [
            {
                "target_type": "PROFILE",
                "target_ref": "proof_state",
                "signal": "POSITIVE",
                "scope": "MISSION",
                "relevance": "HIGH",
                "confidence": "MEDIUM",
            }
        ],
    }
    assert not interpretation_contract_valid(interpretation)

PATTERN_ORG_ID = "00000000-0000-0000-0000-000000000001"
PATTERN_SUBJECT_ID = "00000000-0000-0000-0000-000000000101"
PATTERN_EVIDENCE_ID = "90000000-0000-0000-0000-000000000001"
PATTERN_INTERPRETATION_ID = "90000000-0000-0000-0000-000000000002"
PATTERN_MEMBER_ID = "90000000-0000-0000-0000-000000000003"


def _accepted_pattern_snapshot() -> AcceptedEvidenceSnapshot:
    return AcceptedEvidenceSnapshot(
        evidence_case_id=UUID(PATTERN_EVIDENCE_ID),
        interpretation_id=UUID(PATTERN_INTERPRETATION_ID),
        interpretation_version=1,
        organization_context_id=UUID(PATTERN_ORG_ID),
        subject_person_id=UUID(PATTERN_SUBJECT_ID),
        status="ACCEPTED",
        interpretation_status="ACTIVE",
        behaviour_code="METRIC_REASONING",
        signal="POSITIVE",
        scope="RECOVERY_EXPERIMENT",
        confidence="HIGH",
        context_difficulty="HIGH",
        prompt_contamination="NONE",
        source_independence_group="MISSION_INSTANCE:mission-1",
        accepted_at=datetime(2026, 10, 6, 7, 0, tzinfo=UTC),
        target_links=[
            {
                "target_type": "CAPABILITY",
                "target_ref": "METRICS_EXPERIMENTATION",
                "signal": "POSITIVE",
                "scope": "RECOVERY_EXPERIMENT",
                "relevance": "HIGH",
                "confidence": "HIGH",
            }
        ],
        source_lineage={
            "source_observation_id": "observation-1",
            "source_context": "MISSION_RUNTIME",
            "source_reference": "MISSION_INSTANCE:mission-1",
            "observation_type": "EXPERIMENT_RESULT_OBSERVED",
        },
    )


def _pattern_evidence_set() -> dict:
    return {
        "organization_context_id": PATTERN_ORG_ID,
        "subject_person_id": PATTERN_SUBJECT_ID,
        "members": [
            {
                "evidence_case_id": PATTERN_EVIDENCE_ID,
                "interpretation_id": PATTERN_INTERPRETATION_ID,
                "interpretation_version": 1,
                "behaviour_code": "METRIC_REASONING",
                "signal": "POSITIVE",
                "scope": "RECOVERY_EXPERIMENT",
                "confidence": "HIGH",
                "context_difficulty": "HIGH",
                "prompt_contamination": "NONE",
                "source_independence_group": "MISSION_INSTANCE:mission-1",
                "accepted_at": "2026-10-06T07:00:00Z",
                "target_links": [
                    {
                        "target_type": "CAPABILITY",
                        "target_ref": "METRICS_EXPERIMENTATION",
                        "signal": "POSITIVE",
                        "scope": "RECOVERY_EXPERIMENT",
                        "relevance": "HIGH",
                        "confidence": "HIGH",
                    }
                ],
                "source_lineage": {
                    "source_observation_id": "observation-1",
                    "source_context": "MISSION_RUNTIME",
                    "source_reference": "MISSION_INSTANCE:mission-1",
                    "observation_type": "EXPERIMENT_RESULT_OBSERVED",
                },
            }
        ],
    }


def _pattern_candidate() -> dict:
    return {
        "behaviour_code": "METRIC_REASONING",
        "behaviour_description": "Uses experiment measurements to reason about outcomes.",
        "proposed_pattern_status": "EMERGING",
        "scope": "RECOVERY_EXPERIMENT",
        "rationale": "Accepted evidence supports a reviewable emerging pattern.",
        "evidence": [
            {
                "evidence_set_member_id": PATTERN_MEMBER_ID,
                "relationship": "SUPPORTING",
            }
        ],
    }


def test_pattern_status_vocabulary_matches_final_decision() -> None:
    assert {item.value for item in PatternStatus} == {
        "EMERGING",
        "REPEATED",
        "STABLE",
        "CONTRADICTED",
        "REGRESSED",
        "RECOVERING",
    }
    assert {item.value for item in PatternEvidenceRelationship} == {
        "SUPPORTING",
        "CONTRADICTORY",
    }


def test_pattern_evidence_set_contract_preserves_reviewed_lineage() -> None:
    assert evidence_set_contract_valid(_pattern_evidence_set())

    duplicate = _pattern_evidence_set()
    duplicate["members"].append(dict(duplicate["members"][0]))
    assert not evidence_set_contract_valid(duplicate)

    missing_lineage = _pattern_evidence_set()
    del missing_lineage["members"][0]["source_lineage"]["source_reference"]
    assert not evidence_set_contract_valid(missing_lineage)


def test_pattern_candidate_requires_allowed_status_and_supporting_evidence() -> None:
    assert pattern_candidate_contract_valid(_pattern_candidate())

    unknown_status = _pattern_candidate()
    unknown_status["proposed_pattern_status"] = "PROVEN"
    assert not pattern_candidate_contract_valid(unknown_status)

    contradictory_only = _pattern_candidate()
    contradictory_only["evidence"][0]["relationship"] = "CONTRADICTORY"
    assert not pattern_candidate_contract_valid(contradictory_only)


def test_pattern_candidate_rejects_duplicate_evidence_members() -> None:
    candidate = _pattern_candidate()
    candidate["evidence"].append(dict(candidate["evidence"][0]))
    assert not pattern_candidate_contract_valid(candidate)

def test_pattern_application_requires_creation_expected_version() -> None:
    _require_create_expected_version(0)

    with pytest.raises(AppError) as exc_info:
        _require_create_expected_version(1)

    assert exc_info.value.code == "VERSION_CONFLICT"
    assert exc_info.value.status_code == 409
    assert exc_info.value.details == {
        "expected_version": 1,
        "current_version": 0,
    }


def test_pattern_application_requires_accepted_active_interpretation_context() -> None:
    snapshot = _accepted_pattern_snapshot()
    assert _accepted_snapshot_matches_context(
        snapshot,
        organization_context_id=UUID(PATTERN_ORG_ID),
        subject_person_id=UUID(PATTERN_SUBJECT_ID),
    )

    assert not _accepted_snapshot_matches_context(
        replace(snapshot, status="REJECTED"),
        organization_context_id=UUID(PATTERN_ORG_ID),
        subject_person_id=UUID(PATTERN_SUBJECT_ID),
    )
    assert not _accepted_snapshot_matches_context(
        replace(snapshot, interpretation_status="SUPERSEDED"),
        organization_context_id=UUID(PATTERN_ORG_ID),
        subject_person_id=UUID(PATTERN_SUBJECT_ID),
    )
    assert not _accepted_snapshot_matches_context(
        replace(
            snapshot,
            subject_person_id=UUID("00000000-0000-0000-0000-000000000102"),
        ),
        organization_context_id=UUID(PATTERN_ORG_ID),
        subject_person_id=UUID(PATTERN_SUBJECT_ID),
    )


def test_pattern_candidate_creation_requires_expected_version_zero() -> None:
    _require_pattern_candidate_create_expected_version(0)

    with pytest.raises(AppError) as exc_info:
        _require_pattern_candidate_create_expected_version(1)

    assert exc_info.value.code == "VERSION_CONFLICT"
    assert exc_info.value.status_code == 409
    assert exc_info.value.details == {
        "expected_version": 1,
        "current_version": 0,
    }


def test_pattern_candidate_contract_preserves_explicit_contradiction() -> None:
    candidate = _pattern_candidate()
    candidate["evidence"].append(
        {
            "evidence_set_member_id": (
                "90000000-0000-0000-0000-000000000004"
            ),
            "relationship": "CONTRADICTORY",
        }
    )
    assert pattern_candidate_contract_valid(candidate)


def test_pattern_review_requires_current_candidate_version() -> None:
    _require_pattern_review_expected_version(
        current_version=1,
        expected_version=1,
    )

    with pytest.raises(AppError) as exc_info:
        _require_pattern_review_expected_version(
            current_version=2,
            expected_version=1,
        )

    assert exc_info.value.code == "VERSION_CONFLICT"
    assert exc_info.value.status_code == 409
    assert exc_info.value.details == {
        "expected_version": 1,
        "current_version": 2,
    }


def test_pattern_review_uses_only_dec401_status_vocabulary() -> None:
    for status in PatternStatus:
        assert _reviewed_pattern_status_valid(status.value)

    assert not _reviewed_pattern_status_valid("PROVEN")
    assert not _reviewed_pattern_status_valid("APPROVED")


def test_pattern_updated_event_contract_is_minimal_and_versioned() -> None:
    pattern = BehaviourPattern(
        id=UUID("90000000-0000-0000-0000-000000000010"),
        version=1,
        organization_context_id=UUID(PATTERN_ORG_ID),
        subject_person_id=UUID(PATTERN_SUBJECT_ID),
        source_pattern_candidate_id=UUID(
            "90000000-0000-0000-0000-000000000011"
        ),
        evidence_set_id=UUID("90000000-0000-0000-0000-000000000012"),
        behaviour_code="METRIC_REASONING",
        behaviour_description="Reviewed behaviour.",
        pattern_status="STABLE",
        scope="RECOVERY_EXPERIMENT",
        rationale="Human reviewed rationale.",
        reviewed_by=UUID("90000000-0000-0000-0000-000000000013"),
        reviewed_at=datetime(2026, 10, 6, 8, 0, tzinfo=UTC),
        created_at=datetime(2026, 10, 6, 8, 0, tzinfo=UTC),
        updated_at=datetime(2026, 10, 6, 8, 0, tzinfo=UTC),
    )
    reviewer_id = UUID("90000000-0000-0000-0000-000000000013")

    event = _new_pattern_updated_event(
        pattern=pattern,
        reviewer_id=reviewer_id,
        trace_id="trace-pattern-review",
    )

    assert event.event_type == "pattern.updated.v1"
    assert event.event_version == 1
    assert event.aggregate_type == "BehaviourPattern"
    assert event.aggregate_id == pattern.id
    assert event.aggregate_version == 1
    assert event.actor == {"type": "PERSON", "id": str(reviewer_id)}
    assert event.organization_context_id == UUID(PATTERN_ORG_ID)
    assert event.data_classification == "CONFIDENTIAL"
    assert event.trace_id == "trace-pattern-review"
    assert event.payload == {
        "pattern_id": str(pattern.id),
        "source_pattern_candidate_id": str(pattern.source_pattern_candidate_id),
        "subject_person_id": str(pattern.subject_person_id),
        "evidence_set_id": str(pattern.evidence_set_id),
        "pattern_status": "STABLE",
        "behaviour_code": "METRIC_REASONING",
        "scope": "RECOVERY_EXPERIMENT",
    }
    assert "rationale" not in event.payload
    assert "reviewed_by" not in event.payload


def test_pattern_review_records_update_event_before_commit() -> None:
    application_source = Path("app/patterns/application.py").read_text()
    review_source = application_source.split("async def review_pattern_candidate", 1)[1]

    event_index = review_source.index("_new_pattern_updated_event(")
    commit_index = review_source.index("await db.commit()")
    assert event_index < commit_index


def test_pattern_application_keeps_evidence_boundary_event_contract_only() -> None:
    application_source = Path("app/patterns/application.py").read_text()
    models_source = Path("app/patterns/models.py").read_text()

    assert "app.evidence" not in application_source
    assert "app.evidence" not in models_source
    assert "evidence.evidence_" not in models_source
    assert 'event_type="pattern.updated.v1"' in application_source



def test_pattern_candidate_evidence_set_lookup_is_tenant_scoped_before_lock() -> None:
    source = Path("app/patterns/application.py").read_text()
    candidate_source = source.split(
        "async def create_pattern_candidate",
        1,
    )[1].split(
        "@dataclass(frozen=True)\nclass ReviewPatternCandidateCommand",
        1,
    )[0]
    lookup = candidate_source.split("select(EvidenceSet)", 1)[1].split(
        ".with_for_update()",
        1,
    )[0]

    assert "EvidenceSet.id == command.evidence_set_id" in lookup
    assert "EvidenceSet.organization_context_id" in lookup
    assert "command.organization_context_id" in lookup



def test_flag_profile_claim_vocabularies_are_exact() -> None:
    assert {state.value for state in CapabilityClaimState} == {
        "UNPROVEN",
        "EMERGING",
        "DEMONSTRATED",
        "PROVEN",
    }
    assert {level.value for level in CapabilityLevel} == {
        "L0",
        "L1",
        "L2",
        "L3",
        "L4",
    }
    assert {state.value for state in ProfileUpdateCaseState} == {
        "PROPOSED",
        "REVIEW_REQUIRED",
        "AUTO_ELIGIBLE",
        "APPROVED",
        "APPLIED",
    }
    assert {item.value for item in ClaimPatternRelationship} == {
        "SUPPORTING",
        "CONTRADICTORY",
    }


def test_flag_profile_persistence_keeps_cross_context_refs_opaque() -> None:
    models_source = Path("app/flag_profile/models.py").read_text()
    migration_source = Path(
        "alembic/versions/0016_flag_profile_capability_claim_foundation.py"
    ).read_text()

    assert "app.patterns" not in models_source
    assert "app.evidence" not in models_source
    assert "app.curriculum" not in models_source
    assert '"patterns.' not in migration_source
    assert '"evidence.' not in migration_source
    assert '"curriculum.' not in migration_source

    assert 'ForeignKey("flag_profile.flag_profiles.id")' in models_source
    assert 'ForeignKey("flag_profile.profile_update_cases.id")' in models_source
    assert 'ForeignKey("flag_profile.profile_update_patterns.id")' in models_source
    assert 'ForeignKey("flag_profile.capability_claims.id")' in models_source


def test_flag_profile_lineage_is_explicit_not_aggregate_json() -> None:
    models_source = Path("app/flag_profile/models.py").read_text()

    assert "ProfileUpdatePattern" in models_source
    assert "ProfileUpdatePatternEvidence" in models_source
    assert "CapabilityClaimPattern" in models_source
    assert "evidence_case_id" in models_source
    assert "interpretation_id" in models_source
    assert "source_observation_id" in models_source
    assert "source_reference" in models_source
    assert "JSONB" not in models_source


def test_capability_claim_persistence_has_no_gate_or_responsibility_state() -> None:
    models_source = Path("app/flag_profile/models.py").read_text()

    assert "GateAssessment" not in models_source
    assert "ResponsibilityRecommendation" not in models_source
    assert "gate_state" not in models_source
    assert "responsibility_state" not in models_source



def test_reviewed_pattern_public_contract_rejects_incomplete_source_lineage() -> None:
    source = _source_contract(
        {
            "source_observation_id": "90000000-0000-0000-0000-000000000001",
            "source_context": "MISSION_RUNTIME",
            "source_reference": "MISSION_INSTANCE:mission-1",
            "observation_type": "EXPERIMENT_RESULT_OBSERVED",
        }
    )
    assert source.source_observation_id == UUID(
        "90000000-0000-0000-0000-000000000001"
    )
    assert source.source_context == "MISSION_RUNTIME"

    with pytest.raises(AppError) as exc_info:
        _source_contract(
            {
                "source_context": "MISSION_RUNTIME",
                "source_reference": "MISSION_INSTANCE:mission-1",
                "observation_type": "EXPERIMENT_RESULT_OBSERVED",
            }
        )

    assert exc_info.value.code == "PATTERN_LINEAGE_INCOMPLETE"
    assert exc_info.value.status_code == 409


def test_reviewed_pattern_contract_is_pattern_owned_and_minimal() -> None:
    contract_source = Path("app/patterns/contracts.py").read_text()

    assert "from app.patterns.models import" in contract_source
    assert "ReviewedPatternSnapshotContract" in contract_source
    assert "ReviewedPatternEvidenceContract" in contract_source
    assert "source_observation_id" in contract_source
    assert "target_links" in contract_source

    snapshot_block = contract_source.split(
        "class ReviewedPatternSnapshotContract",
        1,
    )[1].split("def _source_contract", 1)[0]
    assert "rationale" not in snapshot_block
    assert "reviewed_by" not in snapshot_block
    assert "idempotency_key" not in snapshot_block


def test_flag_profile_consumes_pattern_public_contract_only() -> None:
    reader_source = Path("app/flag_profile/pattern_reader.py").read_text()

    assert "from app.patterns.contracts import" in reader_source
    assert "app.patterns.models" not in reader_source
    assert "app.patterns.application" not in reader_source
    assert "app.patterns.api" not in reader_source


def test_reviewed_pattern_contract_scopes_subject_and_organization() -> None:
    contract_source = Path("app/patterns/contracts.py").read_text()
    loader_source = contract_source.split(
        "async def load_reviewed_pattern_snapshots",
        1,
    )[1]

    assert "BehaviourPattern.organization_context_id == organization_context_id" in loader_source
    assert "BehaviourPattern.subject_person_id == subject_person_id" in loader_source
    assert "PatternCandidate.organization_context_id" in loader_source
    assert "EvidenceSet.organization_context_id" in loader_source
    assert "PatternReview.resulting_pattern_id == pattern.id" in loader_source



def _profile_update_command() -> CreateProfileUpdateCaseCommand:
    return CreateProfileUpdateCaseCommand(
        organization_context_id=UUID("00000000-0000-0000-0000-000000000001"),
        subject_person_id=UUID("00000000-0000-0000-0000-000000000101"),
        track_code="PRODUCT_MANAGER",
        capability_id=UUID("10000000-0000-0000-0000-000000000003"),
        patterns=(
            ProfileUpdatePatternInput(
                pattern_id=UUID("90000000-0000-0000-0000-000000000001"),
                relationship="SUPPORTING",
            ),
            ProfileUpdatePatternInput(
                pattern_id=UUID("90000000-0000-0000-0000-000000000002"),
                relationship="CONTRADICTORY",
            ),
        ),
        proposed_claim_state="DEMONSTRATED",
        proposed_level="L2",
        proposed_proven_scope="PROJECT",
        proposed_evidence_recency="CURRENT",
        proposed_confidence_in_claim="MODERATE",
        proposed_next_evidence_needed="Authority-pressure evidence.",
        rationale="Human proposal based on reviewed Patterns.",
        created_by=UUID("00000000-0000-0000-0000-000000000104"),
        expected_version=0,
        idempotency_key="profile-update-create-1",
        trace_id="trace-profile-update-create-1",
    )


def test_profile_update_creation_requires_expected_version_zero() -> None:
    _require_profile_update_create_expected_version(0)

    with pytest.raises(AppError) as exc_info:
        _require_profile_update_create_expected_version(1)

    assert exc_info.value.code == "VERSION_CONFLICT"
    assert exc_info.value.status_code == 409
    assert exc_info.value.details == {
        "expected_version": 1,
        "current_version": 0,
    }


def test_profile_update_creation_validates_claim_vocabulary_without_inference() -> None:
    command = _profile_update_command()
    _require_create_contract(command)

    with pytest.raises(AppError) as state_error:
        _require_create_contract(replace(command, proposed_claim_state="PASS"))
    assert state_error.value.code == "PROFILE_CLAIM_STATE_INVALID"

    with pytest.raises(AppError) as level_error:
        _require_create_contract(replace(command, proposed_level="L5"))
    assert level_error.value.code == "PROFILE_CAPABILITY_LEVEL_INVALID"


def test_profile_update_creation_preserves_explicit_pattern_relationships() -> None:
    command = _profile_update_command()
    _require_create_contract(command)
    assert {item.relationship for item in command.patterns} == {
        "SUPPORTING",
        "CONTRADICTORY",
    }

    with pytest.raises(AppError) as duplicate_error:
        _require_create_contract(
            replace(
                command,
                patterns=(
                    command.patterns[0],
                    command.patterns[0],
                ),
            )
        )
    assert duplicate_error.value.code == "PROFILE_PATTERN_DUPLICATE"


def test_profile_update_creation_does_not_infer_claim_or_import_pattern_models() -> None:
    source = Path("app/flag_profile/application.py").read_text()

    assert "app.patterns.models" not in source
    assert "app.patterns.application" not in source
    assert "from app.patterns.contracts import" in source

    assert "proposed_claim_state=command.proposed_claim_state" in source
    assert "proposed_level=command.proposed_level" in source
    assert "proposed_proven_scope=command.proposed_proven_scope.strip()" in source
    assert "threshold" not in source.lower()
    assert "score" not in source.lower()


def test_profile_update_creation_starts_proposed_and_does_not_apply_claim() -> None:
    source = Path("app/flag_profile/application.py").read_text()
    create_source = source.split("async def create_profile_update_case", 1)[1].split(
        "@dataclass(frozen=True)\nclass RequestProfileUpdateReviewCommand",
        1,
    )[0]

    assert "state=ProfileUpdateCaseState.PROPOSED.value" in create_source
    assert "CapabilityClaim(" not in create_source
    assert 'event_type="profile.claim_changed.v1"' not in create_source
    assert "GateAssessment" not in create_source
    assert "ResponsibilityRecommendation" not in create_source


def test_profile_update_creation_scopes_pattern_reader_to_tenant_and_subject() -> None:
    source = Path("app/flag_profile/application.py").read_text()
    create_source = source.split("async def create_profile_update_case", 1)[1]

    assert "organization_context_id=command.organization_context_id" in create_source
    assert "subject_person_id=command.subject_person_id" in create_source
    assert 'code="PROFILE_PATTERN_NOT_FOUND"' not in create_source
    assert '"PROFILE_PATTERN_NOT_FOUND"' in create_source



def test_profile_update_transition_graph_is_explicit() -> None:
    assert profile_update_transition_allowed("PROPOSED", "REVIEW_REQUIRED")
    assert profile_update_transition_allowed("PROPOSED", "AUTO_ELIGIBLE")
    assert profile_update_transition_allowed("REVIEW_REQUIRED", "APPROVED")
    assert profile_update_transition_allowed("AUTO_ELIGIBLE", "APPROVED")
    assert profile_update_transition_allowed("APPROVED", "APPLIED")

    assert not profile_update_transition_allowed("PROPOSED", "APPROVED")
    assert not profile_update_transition_allowed("REVIEW_REQUIRED", "APPLIED")
    assert not profile_update_transition_allowed("APPLIED", "PROPOSED")


def test_profile_update_review_request_rejects_stale_version() -> None:
    _require_profile_update_expected_version(
        current_version=1,
        expected_version=1,
    )

    with pytest.raises(AppError) as exc_info:
        _require_profile_update_expected_version(
            current_version=2,
            expected_version=1,
        )

    assert exc_info.value.code == "VERSION_CONFLICT"
    assert exc_info.value.status_code == 409
    assert exc_info.value.details == {
        "expected_version": 1,
        "current_version": 2,
    }


def test_profile_update_review_request_is_tenant_scoped_before_lock() -> None:
    source = Path("app/flag_profile/application.py").read_text()
    segment = source.split(
        "async def request_profile_update_review",
        1,
    )[1].split(
        "@dataclass(frozen=True)\nclass ProfileUpdateEvidenceLineage",
        1,
    )[0]
    lookup = segment.split("select(ProfileUpdateCase)", 1)[1].split(
        ".with_for_update()",
        1,
    )[0]

    assert "ProfileUpdateCase.id == command.profile_update_case_id" in lookup
    assert "ProfileUpdateCase.organization_context_id" in lookup
    assert "command.organization_context_id" in lookup
    assert "ProfileUpdateCaseState.REVIEW_REQUIRED.value" in segment
    assert "update_case.version += 1" in segment
    assert "CapabilityClaim(" not in segment
    assert "profile.claim_changed.v1" not in segment


def test_profile_update_pre_review_reads_only_local_lineage_snapshots() -> None:
    source = Path("app/flag_profile/application.py").read_text()
    segment = source.split(
        "async def load_profile_update_case_pre_review",
        1,
    )[1]

    assert "ProfileUpdateCase.organization_context_id" in segment
    assert "ProfileUpdateCaseState.REVIEW_REQUIRED.value" in segment
    assert "ProfileUpdatePattern" in segment
    assert "ProfileUpdatePatternEvidence" in segment
    assert "app.patterns.models" not in segment
    assert "app.evidence" not in segment
    assert "source_observation_id" in segment
    assert "source_reference" in segment
    assert "evidence_relationship" in segment


def test_profile_update_pre_review_does_not_expose_gate_or_responsibility_state() -> None:
    source = Path("app/flag_profile/application.py").read_text()
    pre_review = source.split(
        "class ProfileUpdateCasePreReview",
        1,
    )[1]

    assert "GateAssessment" not in pre_review
    assert "ResponsibilityRecommendation" not in pre_review
    assert "gate_state" not in pre_review
    assert "responsibility_state" not in pre_review



def _profile_approval_command() -> ApproveProfileUpdateCaseCommand:
    return ApproveProfileUpdateCaseCommand(
        organization_context_id=UUID("00000000-0000-0000-0000-000000000001"),
        profile_update_case_id=UUID(
            "91000000-0000-0000-0000-000000000001"
        ),
        reviewer_id=UUID("00000000-0000-0000-0000-000000000105"),
        reviewed_claim_state="DEMONSTRATED",
        reviewed_level="L2",
        reviewed_proven_scope="PROJECT",
        reviewed_evidence_recency="CURRENT",
        reviewed_confidence_in_claim="MODERATE",
        reviewed_next_evidence_needed="Authority-pressure evidence.",
        rationale="Canonical Pattern lineage reviewed and accepted.",
        expected_version=2,
        idempotency_key="profile-update-review-1",
        trace_id="trace-profile-update-review-1",
    )


def test_profile_update_approval_contract_requires_human_reviewed_values() -> None:
    command = _profile_approval_command()
    _require_profile_update_approval_contract(command)

    with pytest.raises(AppError) as state_error:
        _require_profile_update_approval_contract(
            replace(command, reviewed_claim_state="PASS")
        )
    assert state_error.value.code == "PROFILE_CLAIM_STATE_INVALID"

    with pytest.raises(AppError) as level_error:
        _require_profile_update_approval_contract(
            replace(command, reviewed_level="L5")
        )
    assert level_error.value.code == "PROFILE_CAPABILITY_LEVEL_INVALID"

    with pytest.raises(AppError) as rationale_error:
        _require_profile_update_approval_contract(
            replace(command, rationale=" ")
        )
    assert rationale_error.value.code == "PROFILE_UPDATE_REVIEW_INVALID"


def test_profile_update_approval_preserves_proposed_and_reviewed_values_separately() -> None:
    models_source = Path("app/flag_profile/models.py").read_text()
    application_source = Path("app/flag_profile/application.py").read_text()

    for field in (
        "reviewed_claim_state",
        "reviewed_level",
        "reviewed_proven_scope",
        "reviewed_evidence_recency",
        "reviewed_confidence_in_claim",
        "reviewed_next_evidence_needed",
        "review_rationale",
    ):
        assert field in models_source

    approval_source = application_source.split(
        "async def approve_profile_update_case",
        1,
    )[1]
    assert "update_case.reviewed_claim_state = command.reviewed_claim_state" in approval_source
    assert "update_case.reviewed_level = command.reviewed_level" in approval_source
    assert "update_case.proposed_claim_state =" not in approval_source
    assert "update_case.proposed_level =" not in approval_source


def test_profile_update_approval_is_tenant_scoped_and_lineage_gated() -> None:
    source = Path("app/flag_profile/application.py").read_text()
    approval = source.split(
        "async def approve_profile_update_case",
        1,
    )[1]
    lookup = approval.split("select(ProfileUpdateCase)", 1)[1].split(
        ".with_for_update()",
        1,
    )[0]

    assert "ProfileUpdateCase.id == command.profile_update_case_id" in lookup
    assert "ProfileUpdateCase.organization_context_id" in lookup
    assert "command.organization_context_id" in lookup
    assert "load_profile_update_case_pre_review(" in approval
    assert "ProfileUpdateCaseState.APPROVED.value" in approval
    assert "update_case.version += 1" in approval


def test_profile_update_approval_does_not_apply_claim_or_emit_claim_changed() -> None:
    source = Path("app/flag_profile/application.py").read_text()
    approval = source.split(
        "async def approve_profile_update_case",
        1,
    )[1].split(
        "@dataclass(frozen=True)\nclass ApplyProfileUpdateCaseCommand",
        1,
    )[0]

    assert "CapabilityClaim(" not in approval
    assert 'event_type="profile.claim_changed.v1"' not in approval
    assert "CapabilityClaimPattern(" not in approval
    assert "GateAssessment" not in approval
    assert "ResponsibilityRecommendation" not in approval


def test_profile_update_approval_exact_retry_contract() -> None:
    command = _profile_approval_command()
    update_case = ProfileUpdateCase(
        id=command.profile_update_case_id,
        version=3,
        flag_profile_id=UUID("91000000-0000-0000-0000-000000000002"),
        organization_context_id=command.organization_context_id,
        subject_person_id=UUID("00000000-0000-0000-0000-000000000101"),
        track_code="PRODUCT_MANAGER",
        capability_id=UUID("10000000-0000-0000-0000-000000000003"),
        state="APPROVED",
        current_claim_id=None,
        current_claim_version=None,
        current_claim_state=None,
        current_level=None,
        current_proven_scope=None,
        current_evidence_recency=None,
        current_confidence_in_claim=None,
        current_next_evidence_needed=None,
        proposed_claim_state="DEMONSTRATED",
        proposed_level="L2",
        proposed_proven_scope="PROJECT",
        proposed_evidence_recency="CURRENT",
        proposed_confidence_in_claim="MODERATE",
        proposed_next_evidence_needed="Authority-pressure evidence.",
        rationale="Proposal.",
        reviewed_claim_state=command.reviewed_claim_state,
        reviewed_level=command.reviewed_level,
        reviewed_proven_scope=command.reviewed_proven_scope,
        reviewed_evidence_recency=command.reviewed_evidence_recency,
        reviewed_confidence_in_claim=command.reviewed_confidence_in_claim,
        reviewed_next_evidence_needed=command.reviewed_next_evidence_needed,
        review_rationale=command.rationale,
        created_by=UUID("00000000-0000-0000-0000-000000000104"),
        reviewed_by=command.reviewer_id,
        reviewed_at=datetime(2026, 10, 6, 12, 0, tzinfo=UTC),
        applied_by=None,
        applied_at=None,
        creation_idempotency_key="profile-update-create-1",
        review_idempotency_key=command.idempotency_key,
        apply_idempotency_key=None,
        created_at=datetime(2026, 10, 6, 11, 0, tzinfo=UTC),
        updated_at=datetime(2026, 10, 6, 12, 0, tzinfo=UTC),
    )

    assert _approval_retry_matches(
        update_case,
        command=command,
        idempotency_key=command.idempotency_key,
    )
    assert not _approval_retry_matches(
        update_case,
        command=replace(command, rationale="Different review."),
        idempotency_key=command.idempotency_key,
    )


def test_profile_review_migration_is_flag_profile_local() -> None:
    migration_source = Path(
        "alembic/versions/0017_profile_update_human_review_fields.py"
    ).read_text()

    assert 'schema="flag_profile"' in migration_source
    assert "patterns." not in migration_source
    assert "evidence." not in migration_source
    assert "curriculum." not in migration_source



def _profile_apply_command() -> ApplyProfileUpdateCaseCommand:
    return ApplyProfileUpdateCaseCommand(
        organization_context_id=UUID("00000000-0000-0000-0000-000000000001"),
        profile_update_case_id=UUID(
            "91000000-0000-0000-0000-000000000001"
        ),
        applied_by=UUID("00000000-0000-0000-0000-000000000106"),
        expected_version=3,
        idempotency_key="profile-update-apply-1",
        trace_id="trace-profile-update-apply-1",
    )


def test_profile_apply_event_contains_old_and_new_claim_facts() -> None:
    event = _new_profile_claim_changed_event(
        organization_context_id=UUID(
            "00000000-0000-0000-0000-000000000001"
        ),
        subject_person_id=UUID(
            "00000000-0000-0000-0000-000000000101"
        ),
        profile_update_case_id=UUID(
            "91000000-0000-0000-0000-000000000001"
        ),
        claim_id=UUID("92000000-0000-0000-0000-000000000001"),
        claim_version=2,
        capability_id=UUID(
            "10000000-0000-0000-0000-000000000003"
        ),
        track_code="PRODUCT_MANAGER",
        old_claim={
            "claim_id": "92000000-0000-0000-0000-000000000001",
            "version": 1,
            "state": "EMERGING",
            "level": "L1",
            "proven_scope": "SIMULATION",
            "evidence_recency": "CURRENT",
            "confidence_in_claim": "MODERATE",
            "next_evidence_needed": "Real project evidence.",
        },
        new_claim={
            "claim_id": "92000000-0000-0000-0000-000000000001",
            "version": 2,
            "state": "DEMONSTRATED",
            "level": "L2",
            "proven_scope": "PROJECT",
            "evidence_recency": "CURRENT",
            "confidence_in_claim": "MODERATE",
            "next_evidence_needed": "Authority-pressure evidence.",
        },
        pattern_refs=[
            {
                "pattern_id": "90000000-0000-0000-0000-000000000001",
                "pattern_version": 1,
                "relationship": "SUPPORTING",
            }
        ],
        applied_by=UUID("00000000-0000-0000-0000-000000000106"),
        trace_id="trace-profile-update-apply-1",
    )

    assert event.event_type == "profile.claim_changed.v1"
    assert event.aggregate_type == "CapabilityClaim"
    assert event.aggregate_version == 2
    assert event.payload["old_claim"]["state"] == "EMERGING"
    assert event.payload["new_claim"]["state"] == "DEMONSTRATED"
    assert event.payload["pattern_refs"][0]["relationship"] == "SUPPORTING"
    assert "review_rationale" not in event.payload
    assert "reviewed_by" not in event.payload


def test_profile_apply_detects_current_claim_changed_after_proposal() -> None:
    update_case = ProfileUpdateCase(
        current_claim_id=UUID("92000000-0000-0000-0000-000000000001"),
        current_claim_version=1,
        current_claim_state="EMERGING",
        current_level="L1",
        current_proven_scope="SIMULATION",
        current_evidence_recency="CURRENT",
        current_confidence_in_claim="MODERATE",
        current_next_evidence_needed="Real project evidence.",
    )
    current_claim = CapabilityClaim(
        id=UUID("92000000-0000-0000-0000-000000000001"),
        version=1,
        state="EMERGING",
        level="L1",
        proven_scope="SIMULATION",
        evidence_recency="CURRENT",
        confidence_in_claim="MODERATE",
        next_evidence_needed="Real project evidence.",
    )
    assert _claim_snapshot_matches_current(update_case, current_claim)

    current_claim.version = 2
    assert not _claim_snapshot_matches_current(update_case, current_claim)


def test_profile_apply_new_claim_requires_snapshot_to_still_be_empty() -> None:
    update_case = ProfileUpdateCase(
        current_claim_id=None,
        current_claim_version=None,
        current_claim_state=None,
        current_level=None,
        current_proven_scope=None,
        current_evidence_recency=None,
        current_confidence_in_claim=None,
        current_next_evidence_needed=None,
    )
    assert _claim_snapshot_matches_current(update_case, None)

    unexpected_claim = CapabilityClaim(
        id=UUID("92000000-0000-0000-0000-000000000001"),
        version=1,
        state="EMERGING",
        level="L1",
        proven_scope="SIMULATION",
        evidence_recency="CURRENT",
        confidence_in_claim="MODERATE",
        next_evidence_needed="More evidence.",
    )
    assert not _claim_snapshot_matches_current(update_case, unexpected_claim)


def test_profile_apply_is_approved_only_and_uses_reviewed_values() -> None:
    source = Path("app/flag_profile/application.py").read_text()
    apply_source = source.split("async def apply_profile_update_case", 1)[1]

    assert "ProfileUpdateCaseState.APPLIED.value" in apply_source
    assert "profile_update_transition_allowed(" in apply_source
    assert "update_case.reviewed_claim_state" in apply_source
    assert "update_case.reviewed_level" in apply_source
    assert "update_case.reviewed_proven_scope" in apply_source
    assert "claim.state = update_case.proposed_claim_state" not in apply_source
    assert "claim.level = update_case.proposed_level" not in apply_source


def test_profile_apply_replaces_claim_pattern_relationships_explicitly() -> None:
    source = Path("app/flag_profile/application.py").read_text()
    apply_source = source.split("async def apply_profile_update_case", 1)[1]

    assert "delete(CapabilityClaimPattern)" in apply_source
    assert "CapabilityClaimPattern(" in apply_source
    assert "relationship=pattern.relationship" in apply_source
    assert "pattern_version=pattern.pattern_version" in apply_source


def test_profile_apply_records_event_before_single_commit() -> None:
    source = Path("app/flag_profile/application.py").read_text()
    apply_source = source.split("async def apply_profile_update_case", 1)[1]

    event_index = apply_source.index("_new_profile_claim_changed_event(")
    commit_index = apply_source.index("await db.commit()")
    assert event_index < commit_index
    assert apply_source.count("await db.commit()") == 1
    assert "record_event(" in apply_source


def test_profile_apply_does_not_mutate_gate_or_responsibility() -> None:
    source = Path("app/flag_profile/application.py").read_text()
    apply_source = source.split("async def apply_profile_update_case", 1)[1]

    assert "GateAssessment" not in apply_source
    assert "ResponsibilityRecommendation" not in apply_source
    assert "gate." not in apply_source
    assert "responsibility." not in apply_source


def test_profile_apply_exact_retry_contract() -> None:
    command = _profile_apply_command()
    update_case = ProfileUpdateCase(
        state="APPLIED",
        apply_idempotency_key=command.idempotency_key,
        applied_by=command.applied_by,
    )
    assert _applied_retry_matches(
        update_case,
        command=command,
        idempotency_key=command.idempotency_key,
    )
    assert not _applied_retry_matches(
        update_case,
        command=replace(
            command,
            applied_by=UUID("00000000-0000-0000-0000-000000000107"),
        ),
        idempotency_key=command.idempotency_key,
    )


def test_profile_apply_is_tenant_scoped_before_lock() -> None:
    source = Path("app/flag_profile/application.py").read_text()
    apply_source = source.split("async def apply_profile_update_case", 1)[1]
    lookup = apply_source.split("select(ProfileUpdateCase)", 1)[1].split(
        ".with_for_update()",
        1,
    )[0]

    assert "ProfileUpdateCase.id == command.profile_update_case_id" in lookup
    assert "ProfileUpdateCase.organization_context_id" in lookup
    assert "command.organization_context_id" in lookup



def test_profile_update_review_request_exact_retry_is_audited() -> None:
    command = RequestProfileUpdateReviewCommand(
        organization_context_id=UUID("00000000-0000-0000-0000-000000000001"),
        profile_update_case_id=UUID(
            "91000000-0000-0000-0000-000000000001"
        ),
        requested_by=UUID("00000000-0000-0000-0000-000000000104"),
        expected_version=1,
        idempotency_key="profile-review-request-1",
        trace_id="trace-profile-review-request-1",
    )
    update_case = ProfileUpdateCase(
        state="REVIEW_REQUIRED",
        review_requested_by=command.requested_by,
        review_requested_at=datetime(2026, 10, 6, 12, 0, tzinfo=UTC),
        review_request_idempotency_key=command.idempotency_key,
    )

    assert _review_request_retry_matches(
        update_case,
        command=command,
        idempotency_key=command.idempotency_key,
    )
    assert not _review_request_retry_matches(
        update_case,
        command=replace(
            command,
            requested_by=UUID("00000000-0000-0000-0000-000000000105"),
        ),
        idempotency_key=command.idempotency_key,
    )


def test_profile_update_review_request_persists_actor_and_idempotency() -> None:
    source = Path("app/flag_profile/application.py").read_text()
    segment = source.split(
        "async def request_profile_update_review",
        1,
    )[1].split(
        "@dataclass(frozen=True)\nclass ProfileUpdateEvidenceLineage",
        1,
    )[0]

    assert "command.idempotency_key.strip()" in segment
    assert "update_case.review_requested_by = command.requested_by" in segment
    assert "update_case.review_requested_at = now" in segment
    assert (
        "update_case.review_request_idempotency_key = idempotency_key"
        in segment
    )


def test_profile_review_request_migration_is_flag_profile_local() -> None:
    migration_source = Path(
        "alembic/versions/0018_profile_update_review_request_audit.py"
    ).read_text()

    assert 'schema="flag_profile"' in migration_source
    assert "patterns." not in migration_source
    assert "evidence." not in migration_source
    assert "curriculum." not in migration_source



def test_gate_assessment_state_vocabulary_is_exact() -> None:
    assert {state.value for state in GateAssessmentState} == {
        "UNPROVEN",
        "PASS",
        "AT_RISK",
        "REVIEW_REQUIRED",
        "PASS_CONFIRMED",
        "FAIL",
        "REMEDIATION",
        "REASSESSMENT",
    }


def test_gate_assessment_transition_graph_matches_final_contract() -> None:
    assert gate_transition_allowed("UNPROVEN", "PASS")
    assert gate_transition_allowed("PASS", "AT_RISK")
    assert gate_transition_allowed("AT_RISK", "REVIEW_REQUIRED")
    assert gate_transition_allowed("REVIEW_REQUIRED", "PASS_CONFIRMED")
    assert gate_transition_allowed("REVIEW_REQUIRED", "FAIL")
    assert gate_transition_allowed("PASS_CONFIRMED", "AT_RISK")
    assert gate_transition_allowed("FAIL", "REMEDIATION")
    assert gate_transition_allowed("REMEDIATION", "REASSESSMENT")
    assert gate_transition_allowed("REASSESSMENT", "PASS")
    assert gate_transition_allowed("REASSESSMENT", "FAIL")

    assert not gate_transition_allowed("UNPROVEN", "FAIL")
    assert not gate_transition_allowed("AT_RISK", "FAIL")
    assert not gate_transition_allowed("REVIEW_REQUIRED", "PASS")
    assert not gate_transition_allowed("FAIL", "PASS")
    assert not gate_transition_allowed("PASS", "FAIL")


def test_gate_definition_registry_contains_only_canonical_gates() -> None:
    assert [item.code for item in GATE_DEFINITION_REGISTRY] == [
        GateCode.A,
        GateCode.B,
        GateCode.C,
        GateCode.D,
        GateCode.E,
    ]
    assert [item.name for item in GATE_DEFINITION_REGISTRY] == [
        "Foundation Readiness",
        "Product Judgment Readiness",
        "Real Project Readiness",
        "Ownership Trial Readiness",
        "Flag Board",
    ]
    assert GATE_DEFINITION_REGISTRY[0].outcomes == (
        "ENTER PRODUCT CORE",
        "NOT YET",
    )
    assert GATE_DEFINITION_REGISTRY[3].outcomes == (
        "GRANT OUTCOME OWNERSHIP",
        "REMEDIATE",
    )
    assert GATE_DEFINITION_REGISTRY[4].outcomes == (
        "READY",
        "NOT YET",
        "DIFFERENT SCOPE",
    )


def test_gate_definition_registry_has_no_scoring_policy() -> None:
    domain_source = Path("app/gate_assessment/domain.py").read_text()
    models_source = Path("app/gate_assessment/models.py").read_text()

    forbidden = (
        "overall_score",
        "weighted_score",
        "average_score",
        "threshold_value",
        "passing_score",
        "auto_evaluator",
    )
    for value in forbidden:
        assert value not in domain_source.lower()
        assert value not in models_source.lower()


def test_gate_definition_persistence_is_versioned_and_context_local() -> None:
    models_source = Path("app/gate_assessment/models.py").read_text()
    migration_source = Path(
        "alembic/versions/0019_gate_definition_registry_foundation.py"
    ).read_text()

    assert "GateDefinitionVersion" in models_source
    assert "GateDefinitionRequirement" in models_source
    assert "GateDefinitionOutcome" in models_source
    assert 'ForeignKey("gate_assessment.gate_definitions.id")' in models_source
    assert (
        'ForeignKey("gate_assessment.gate_definition_versions.id")'
        in models_source
    )

    assert '"flag_profile.' not in migration_source
    assert '"patterns.' not in migration_source
    assert '"evidence.' not in migration_source
    assert '"curriculum.' not in migration_source
    assert "JSONB" not in models_source


def test_gate_definition_name_is_part_of_the_versioned_definition() -> None:
    models_source = Path("app/gate_assessment/models.py").read_text()
    migration_source = Path(
        "alembic/versions/0019_gate_definition_registry_foundation.py"
    ).read_text()

    definition_model = models_source.split(
        "class GateDefinition(Base):", 1
    )[1].split("class GateDefinitionVersion(Base):", 1)[0]
    version_model = models_source.split(
        "class GateDefinitionVersion(Base):", 1
    )[1].split("class GateDefinitionRequirement(Base):", 1)[0]
    assert "name: Mapped[str]" not in definition_model
    assert "name: Mapped[str]" in version_model

    definition_table = migration_source.split(
        'op.create_table(\n        "gate_definitions"', 1
    )[1].split(
        'op.create_table(\n        "gate_definition_versions"', 1
    )[0]
    version_table = migration_source.split(
        'op.create_table(\n        "gate_definition_versions"', 1
    )[1].split(
        'op.create_table(\n        "gate_definition_requirements"', 1
    )[0]
    assert 'sa.Column("name"' not in definition_table
    assert 'sa.Column("name"' in version_table


def test_gate_definition_registry_rows_are_database_immutable() -> None:
    migration_source = Path(
        "alembic/versions/0019_gate_definition_registry_foundation.py"
    ).read_text()

    assert "reject_gate_definition_mutation" in migration_source
    assert "BEFORE UPDATE OR DELETE" in migration_source
    for table_name in (
        "gate_definitions",
        "gate_definition_versions",
        "gate_definition_requirements",
        "gate_definition_outcomes",
    ):
        assert f'"{table_name}"' in migration_source


def test_flag_profile_public_snapshot_contract_has_exact_gate_facts() -> None:
    from dataclasses import fields

    from app.flag_profile.contracts import (
        CapabilityClaimEvidenceLineageContract,
        CapabilityClaimPatternLineageContract,
        CurrentCapabilityClaimContract,
        CurrentFlagProfileSnapshotContract,
    )

    assert {field.name for field in fields(CurrentFlagProfileSnapshotContract)} == {
        "flag_profile_id",
        "flag_profile_version",
        "organization_context_id",
        "subject_person_id",
        "track_code",
        "profile_updated_at",
        "claims",
    }
    assert {field.name for field in fields(CurrentCapabilityClaimContract)} == {
        "claim_id",
        "claim_version",
        "capability_id",
        "state",
        "level",
        "proven_scope",
        "evidence_recency",
        "confidence_in_claim",
        "reviewed_at",
        "next_evidence_needed",
        "source_profile_update_case_id",
        "patterns",
    }
    assert {
        "pattern_id",
        "pattern_version",
        "relationship",
        "pattern_status",
        "behaviour_code",
        "scope",
        "reviewed_at",
        "evidence",
    } == {field.name for field in fields(CapabilityClaimPatternLineageContract)}
    assert {
        "evidence_case_id",
        "interpretation_id",
        "interpretation_version",
        "source_observation_id",
        "source_context",
        "source_reference",
        "observation_type",
    }.issubset(
        {field.name for field in fields(CapabilityClaimEvidenceLineageContract)}
    )


def test_flag_profile_public_snapshot_contract_is_tenant_subject_scoped() -> None:
    source = Path("app/flag_profile/contracts.py").read_text()

    assert "FlagProfile.organization_context_id == organization_context_id" in source
    assert "FlagProfile.subject_person_id == subject_person_id" in source
    assert "FlagProfile.track_code == normalized_track" in source
    assert (
        "CapabilityClaim.organization_context_id == organization_context_id"
        in source
    )
    assert "CapabilityClaim.subject_person_id == subject_person_id" in source
    assert "ProfileUpdateCase.organization_context_id" in source
    assert "ProfileUpdateCase.subject_person_id == subject_person_id" in source


def test_flag_profile_public_snapshot_contract_fails_closed_on_lineage_or_stale_read() -> None:
    source = Path("app/flag_profile/contracts.py").read_text()

    assert "FLAG_PROFILE_SNAPSHOT_LINEAGE_INCOMPLETE" in source
    assert "Current Capability Claim has no Reviewed Pattern lineage." in source
    assert "Current Capability Claim Pattern has no Evidence lineage." in source
    assert "claim_keys != set(source_by_key)" in source
    assert "current_version != profile.version" in source
    assert "FLAG_PROFILE_SNAPSHOT_STALE" in source


def test_flag_profile_public_snapshot_contract_hides_reviewer_private_fields() -> None:
    from dataclasses import fields

    from app.flag_profile.contracts import CurrentCapabilityClaimContract

    exposed = {field.name for field in fields(CurrentCapabilityClaimContract)}
    assert "reviewed_by" not in exposed
    assert "review_rationale" not in exposed
    assert "applied_by" not in exposed
    assert "creation_idempotency_key" not in exposed
    assert "review_idempotency_key" not in exposed
    assert "apply_idempotency_key" not in exposed


def test_flag_profile_public_snapshot_matches_applied_claim_source() -> None:
    from app.flag_profile.contracts import _source_case_matches_claim

    shared = {
        "flag_profile_id": UUID("91000000-0000-0000-0000-000000000001"),
        "organization_context_id": UUID(
            "00000000-0000-0000-0000-000000000001"
        ),
        "subject_person_id": UUID("00000000-0000-0000-0000-000000000101"),
        "track_code": "PRODUCT_MANAGER",
        "capability_id": UUID("10000000-0000-0000-0000-000000000003"),
    }
    reviewed_at = datetime(2026, 10, 7, 6, 0, tzinfo=UTC)
    reviewer_id = UUID("00000000-0000-0000-0000-000000000106")
    source_case = ProfileUpdateCase(
        **shared,
        state="APPLIED",
        reviewed_claim_state="DEMONSTRATED",
        reviewed_level="L2",
        reviewed_proven_scope="PROJECT",
        reviewed_evidence_recency="CURRENT",
        reviewed_confidence_in_claim="MODERATE",
        reviewed_next_evidence_needed="Authority-pressure evidence.",
        reviewed_at=reviewed_at,
        reviewed_by=reviewer_id,
    )
    claim = CapabilityClaim(
        **shared,
        state="DEMONSTRATED",
        level="L2",
        proven_scope="PROJECT",
        evidence_recency="CURRENT",
        confidence_in_claim="MODERATE",
        next_evidence_needed="Authority-pressure evidence.",
        reviewed_at=reviewed_at,
        reviewed_by=reviewer_id,
    )

    assert _source_case_matches_claim(source_case, claim)
    source_case.reviewed_level = "L3"
    assert not _source_case_matches_claim(source_case, claim)


def test_gate_profile_reader_uses_only_flag_profile_public_contract() -> None:
    source = Path("app/gate_assessment/profile_reader.py").read_text()

    assert "from app.flag_profile.contracts import" in source
    assert "load_current_flag_profile_snapshot" in source
    assert "app.flag_profile.models" not in source
    assert "app.flag_profile.application" not in source
    assert "CapabilityClaim" not in source
    assert "ProfileUpdateCase" not in source


def test_gate_assessment_persistence_matches_conceptual_identity() -> None:
    from app.gate_assessment.models import GateAssessment

    table = GateAssessment.__table__
    assert table.schema == "gate_assessment"
    assert set(table.c.keys()) == {
        "id",
        "version",
        "gate_definition_version_id",
        "organization_context_id",
        "subject_person_id",
        "state",
        "created_at",
        "updated_at",
    }

    models_source = Path("app/gate_assessment/models.py").read_text()
    assessment_source = models_source.split(
        "class GateAssessment(Base):", 1
    )[1].split("class GateProfileSnapshot(Base):", 1)[0]
    assert '"organization_context_id"' in assessment_source
    assert '"subject_person_id"' in assessment_source
    assert '"gate_definition_version_id"' in assessment_source
    assert 'name="uq_gate_assessment_identity"' in assessment_source


def test_gate_snapshot_persistence_is_relational_and_complete() -> None:
    from app.gate_assessment.models import (
        GateProfileSnapshot,
        GateProfileSnapshotClaim,
        GateSnapshotEvidenceRef,
        GateSnapshotPatternRef,
    )

    assert {
        "source_flag_profile_id",
        "source_flag_profile_version",
        "source_track_code",
        "source_profile_updated_at",
        "captured_at",
    }.issubset(GateProfileSnapshot.__table__.c.keys())
    assert {
        "source_claim_id",
        "source_claim_version",
        "capability_id",
        "state",
        "level",
        "proven_scope",
        "evidence_recency",
        "confidence_in_claim",
        "reviewed_at",
        "next_evidence_needed",
        "source_profile_update_case_id",
    }.issubset(GateProfileSnapshotClaim.__table__.c.keys())
    assert {
        "source_pattern_id",
        "source_pattern_version",
        "relationship",
        "pattern_status",
        "behaviour_code",
        "scope",
        "reviewed_at",
    }.issubset(GateSnapshotPatternRef.__table__.c.keys())
    assert {
        "evidence_case_id",
        "interpretation_id",
        "interpretation_version",
        "source_observation_id",
        "source_context",
        "source_reference",
        "observation_type",
    }.issubset(GateSnapshotEvidenceRef.__table__.c.keys())


def test_gate_snapshot_foreign_keys_are_intra_context_only() -> None:
    from app.gate_assessment.models import (
        GateAssessment,
        GateProfileSnapshot,
        GateProfileSnapshotClaim,
        GateSnapshotEvidenceRef,
        GateSnapshotPatternRef,
    )

    tables = (
        GateAssessment.__table__,
        GateProfileSnapshot.__table__,
        GateProfileSnapshotClaim.__table__,
        GateSnapshotPatternRef.__table__,
        GateSnapshotEvidenceRef.__table__,
    )
    targets = {
        fk.target_fullname
        for table in tables
        for fk in table.foreign_keys
    }
    assert targets
    assert all(target.startswith("gate_assessment.") for target in targets)
    for forbidden in (
        "flag_profile.",
        "patterns.",
        "evidence.",
        "curriculum.",
        "mission.",
    ):
        assert all(not target.startswith(forbidden) for target in targets)


def test_gate_profile_snapshot_rows_are_database_immutable() -> None:
    migration_source = Path(
        "alembic/versions/0020_gate_assessment_persistence_foundation.py"
    ).read_text()

    assert "reject_profile_snapshot_mutation" in migration_source
    assert "BEFORE UPDATE OR DELETE" in migration_source
    for table_name in (
        "gate_profile_snapshots",
        "gate_profile_snapshot_claims",
        "gate_snapshot_pattern_refs",
        "gate_snapshot_evidence_refs",
    ):
        assert f'"{table_name}"' in migration_source


def test_gate_persistence_foundation_has_no_cross_context_fk_or_jsonb() -> None:
    migration_source = Path(
        "alembic/versions/0020_gate_assessment_persistence_foundation.py"
    ).read_text()
    models_source = Path("app/gate_assessment/models.py").read_text()

    assert "JSONB" not in migration_source
    assert "JSONB" not in models_source
    for forbidden in (
        "flag_profile.",
        "patterns.",
        "evidence.",
        "curriculum.",
        "mission.",
    ):
        assert forbidden not in migration_source


def test_gate_persistence_foundation_adds_no_review_command_event_or_api() -> None:
    migration_source = Path(
        "alembic/versions/0020_gate_assessment_persistence_foundation.py"
    ).read_text()
    models_source = Path("app/gate_assessment/models.py").read_text().split(
        "class GateReview(Base):", 1
    )[0]

    for forbidden in (
        "GateReview",
        "open_review",
        "reviewer_id",
        "decision_rationale",
        "idempotency_key",
        "gate.review_completed.v1",
        "profile.snapshot_created.v1",
    ):
        assert forbidden not in migration_source
        assert forbidden not in models_source


def test_gate_review_opening_persistence_is_auditable_and_immutable() -> None:
    from app.gate_assessment.models import GateReview

    columns = set(GateReview.__table__.c.keys())
    assert {
        "gate_assessment_id",
        "gate_profile_snapshot_id",
        "gate_definition_version_id",
        "organization_context_id",
        "subject_person_id",
        "gate_assessment_version",
        "opened_by",
        "opened_at",
        "open_idempotency_key",
        "trace_id",
    }.issubset(columns)

    migration_source = Path(
        "alembic/versions/0021_gate_review_opening_audit.py"
    ).read_text()
    assert "reject_gate_review_mutation" in migration_source
    assert "BEFORE UPDATE OR DELETE" in migration_source
    assert "uq_gate_review_open_idempotency" in migration_source
    assert "uq_gate_review_assessment_version" in migration_source


def test_gate_review_opening_has_only_intra_context_foreign_keys() -> None:
    from app.gate_assessment.models import GateReview

    targets = {fk.target_fullname for fk in GateReview.__table__.foreign_keys}
    assert targets == {
        "gate_assessment.gate_assessments.id",
        "gate_assessment.gate_profile_snapshots.id",
        "gate_assessment.gate_definition_versions.id",
    }


def test_gate_open_review_uses_only_flag_profile_public_contract() -> None:
    source = Path("app/gate_assessment/application.py").read_text()
    reader_source = Path("app/gate_assessment/profile_reader.py").read_text()

    assert "from app.flag_profile.contracts import" in source
    assert "app.flag_profile.models" not in source
    assert "app.flag_profile.application" not in source
    assert "lock_profile=True" in reader_source


def test_flag_profile_public_contract_can_pin_profile_for_gate_snapshot() -> None:
    source = Path("app/flag_profile/contracts.py").read_text()
    load_source = source.split(
        "async def load_current_flag_profile_snapshot", 1
    )[1]

    assert "lock_profile: bool = False" in load_source
    assert "if lock_profile:" in load_source
    assert "profile_query = profile_query.with_for_update()" in load_source


def test_gate_open_review_is_tenant_scoped_versioned_and_transition_guarded() -> None:
    source = Path("app/gate_assessment/application.py").read_text()
    open_source = source.split("async def open_gate_review", 1)[1]
    lookup = open_source.split("select(GateAssessment)", 1)[1].split(
        ".with_for_update()", 1
    )[0]

    assert "GateAssessment.id == command.gate_assessment_id" in lookup
    assert "GateAssessment.organization_context_id" in lookup
    assert "command.organization_context_id" in lookup
    assert "_require_expected_version(" in open_source
    assert "gate_transition_allowed(" in open_source
    assert "GateAssessmentState.REVIEW_REQUIRED.value" in open_source


def test_gate_open_review_snapshots_full_public_lineage_before_single_commit() -> None:
    source = Path("app/gate_assessment/application.py").read_text()
    persist_source = source.split(
        "def _persist_profile_snapshot", 1
    )[1].split(
        "async def open_gate_review", 1
    )[0]
    open_source = source.split("async def open_gate_review", 1)[1].split(
        "@dataclass(frozen=True)\nclass CompleteGateReviewCommand",
        1,
    )[0]

    for value in (
        "source_flag_profile_version=source.flag_profile_version",
        "source_claim_version=claim.claim_version",
        "source_pattern_version=pattern.pattern_version",
        "interpretation_version=evidence.interpretation_version",
        "source_observation_id=evidence.source_observation_id",
        "source_reference=evidence.source_reference",
    ):
        assert value in persist_source

    assert open_source.count("await db.commit()") == 1
    assert "_persist_profile_snapshot(" in open_source
    assert "db.add(review)" in open_source


def test_gate_open_review_has_no_pass_fail_or_event_side_effect() -> None:
    source = Path("app/gate_assessment/application.py").read_text()
    open_source = source.split("async def open_gate_review", 1)[1].split(
        "@dataclass(frozen=True)\nclass CompleteGateReviewCommand",
        1,
    )[0]

    assert "PASS_CONFIRMED" not in open_source
    assert "GateAssessmentState.FAIL" not in open_source
    assert "gate.review_completed.v1" not in open_source
    assert "profile.snapshot_created.v1" not in open_source
    assert "record_event(" not in open_source
    assert "CapabilityClaim" not in open_source
    assert "ResponsibilityRecommendation" not in open_source


def test_gate_open_review_retry_requires_same_assessment_actor_and_track() -> None:
    from app.gate_assessment.application import (
        OpenGateReviewCommand,
        _open_review_retry_matches,
    )
    from app.gate_assessment.models import GateProfileSnapshot, GateReview

    assessment_id = UUID("a2000000-0000-0000-0000-000000000001")
    actor_id = UUID("00000000-0000-0000-0000-000000000106")
    command = OpenGateReviewCommand(
        organization_context_id=UUID(
            "00000000-0000-0000-0000-000000000001"
        ),
        gate_assessment_id=assessment_id,
        track_code="PRODUCT_MANAGER",
        opened_by=actor_id,
        expected_version=4,
        idempotency_key="gate-open-review-1",
        trace_id="trace-gate-open-review-1",
    )
    review = GateReview(
        gate_assessment_id=assessment_id,
        opened_by=actor_id,
    )
    snapshot = GateProfileSnapshot(
        gate_assessment_id=assessment_id,
        source_track_code="PRODUCT_MANAGER",
    )

    assert _open_review_retry_matches(
        review,
        snapshot,
        command=command,
        track_code="PRODUCT_MANAGER",
    )
    snapshot.source_track_code = "OTHER_TRACK"
    assert not _open_review_retry_matches(
        review,
        snapshot,
        command=command,
        track_code="PRODUCT_MANAGER",
    )


def test_gate_pre_decision_read_model_is_pinned_and_version_exact() -> None:
    source = Path("app/gate_assessment/read_models.py").read_text()
    load_source = source.split("async def load_assessor_pre_decision_read", 1)[1]

    assert "GateReview.id == gate_review_id" in load_source
    assert "GateReview.organization_context_id == organization_context_id" in load_source
    assert (
        "GateAssessment.gate_definition_version_id"
        in load_source
    )
    assert "== review.gate_definition_version_id" in load_source
    assert "assessment.version != review.gate_assessment_version" in load_source
    assert "GateProfileSnapshot.id == review.gate_profile_snapshot_id" in load_source


def test_gate_pre_decision_read_model_uses_only_gate_owned_snapshot() -> None:
    source = Path("app/gate_assessment/read_models.py").read_text()

    assert "app.flag_profile" not in source
    assert "app.patterns" not in source
    assert "app.evidence" not in source
    assert "GateProfileSnapshotClaim" in source
    assert "GateSnapshotPatternRef" in source
    assert "GateSnapshotEvidenceRef" in source


def test_gate_pre_decision_read_model_surfaces_exact_definition_version() -> None:
    source = Path("app/gate_assessment/read_models.py").read_text()
    definition_source = source.split(
        "async def _load_definition", 1
    )[1].split(
        "def _evidence_read", 1
    )[0]

    assert "GateDefinitionVersion.id == gate_definition_version_id" in definition_source
    assert "version_number=version.version_number" in definition_source
    assert "decision_question=version.decision_question" in definition_source
    assert "requirements=tuple(item.requirement_text" in definition_source
    assert "outcomes=tuple(item.outcome_text" in definition_source


def test_gate_pre_decision_read_model_preserves_supporting_and_contradictory_lineage() -> None:
    source = Path("app/gate_assessment/read_models.py").read_text()
    claim_source = source.split(
        "async def _load_claim", 1
    )[1].split(
        "async def load_assessor_pre_decision_read", 1
    )[0]

    assert 'pattern.relationship == "SUPPORTING"' in claim_source
    assert 'pattern.relationship == "CONTRADICTORY"' in claim_source
    assert "supporting_patterns=tuple(supporting)" in claim_source
    assert "contradictory_patterns=tuple(contradictory)" in claim_source
    assert "Pinned Gate Pattern relationship is not recognized." in claim_source


def test_gate_pre_decision_read_model_surfaces_gaps_and_risks_without_scoring() -> None:
    source = Path("app/gate_assessment/read_models.py").read_text()

    assert "next_evidence_needed=claim.next_evidence_needed" in source
    assert "for pattern in claim.contradictory_patterns" in source
    assert "risk_patterns=tuple(risk_patterns)" in source

    forbidden = (
        "overall_score",
        "weighted_score",
        "average_score",
        "passing_score",
        "threshold_value",
        "readiness_score",
        "auto_evaluator",
    )
    lowered = source.lower()
    for value in forbidden:
        assert value not in lowered


def test_gate_pre_decision_read_model_is_read_only() -> None:
    source = Path("app/gate_assessment/read_models.py").read_text()
    load_source = source.split("async def load_assessor_pre_decision_read", 1)[1]

    assert "await db.commit()" not in source
    assert "db.add(" not in source
    assert ".with_for_update()" not in source
    assert "record_event(" not in source
    assert "GateAssessmentState.REVIEW_REQUIRED.value" in load_source
    assert "GateAssessmentState.PASS_CONFIRMED" not in load_source
    assert "GateAssessmentState.FAIL" not in load_source


def test_gate_pre_decision_read_model_preserves_full_evidence_lineage() -> None:
    from dataclasses import fields

    from app.gate_assessment.read_models import (
        GateEvidenceLineageRead,
        GatePatternLineageRead,
    )

    evidence_fields = {field.name for field in fields(GateEvidenceLineageRead)}
    assert {
        "evidence_case_id",
        "interpretation_id",
        "interpretation_version",
        "source_observation_id",
        "source_context",
        "source_reference",
        "observation_type",
        "source_independence_group",
        "prompt_contamination",
    }.issubset(evidence_fields)

    pattern_fields = {field.name for field in fields(GatePatternLineageRead)}
    assert {
        "source_pattern_id",
        "source_pattern_version",
        "relationship",
        "evidence",
    }.issubset(pattern_fields)


def test_gate_human_decision_persistence_is_append_only_and_exact() -> None:
    from app.gate_assessment.models import GateReviewDecision

    columns = set(GateReviewDecision.__table__.c.keys())
    assert {
        "gate_review_id",
        "gate_assessment_id",
        "gate_profile_snapshot_id",
        "gate_profile_snapshot_version",
        "gate_definition_version_id",
        "organization_context_id",
        "subject_person_id",
        "prior_assessment_version",
        "resulting_assessment_version",
        "decision_state",
        "reviewer_id",
        "rationale",
        "decided_at",
        "decision_idempotency_key",
        "trace_id",
    }.issubset(columns)

    migration_source = Path(
        "alembic/versions/0022_gate_human_decision_audit.py"
    ).read_text()
    assert "decision_state IN ('PASS_CONFIRMED', 'FAIL')" in migration_source
    assert "reject_gate_decision_mutation" in migration_source
    assert "BEFORE UPDATE OR DELETE" in migration_source
    assert "uq_gate_review_decision_idempotency" in migration_source


def test_gate_human_decision_foreign_keys_are_context_local() -> None:
    from app.gate_assessment.models import GateReviewDecision

    targets = {
        fk.target_fullname for fk in GateReviewDecision.__table__.foreign_keys
    }
    assert targets == {
        "gate_assessment.gate_reviews.id",
        "gate_assessment.gate_assessments.id",
        "gate_assessment.gate_profile_snapshots.id",
        "gate_assessment.gate_definition_versions.id",
    }


def test_gate_human_decision_accepts_only_pass_confirmed_or_fail() -> None:
    source = Path("app/gate_assessment/application.py").read_text()
    decision_source = source.split(
        "def _require_gate_decision_contract", 1
    )[1].split(
        "async def _decision_by_idempotency_key", 1
    )[0]

    assert "GateAssessmentState.PASS_CONFIRMED.value" in decision_source
    assert "GateAssessmentState.FAIL.value" in decision_source
    assert "Human Gate decision must be PASS_CONFIRMED or FAIL." in decision_source
    assert "GATE_DECISION_RATIONALE_REQUIRED" in decision_source


def test_gate_human_decision_is_tenant_scoped_and_row_locked() -> None:
    source = Path("app/gate_assessment/application.py").read_text()
    complete_source = source.split("async def complete_gate_review", 1)[1]
    lookup = complete_source.split("select(GateAssessment)", 1)[1].split(
        ".with_for_update()", 1
    )[0]

    assert "GateReview.organization_context_id" in complete_source
    assert "command.organization_context_id" in complete_source
    assert "GateAssessment.organization_context_id" in lookup
    assert "GateAssessment.subject_person_id == review.subject_person_id" in lookup
    assert (
        "GateAssessment.gate_definition_version_id"
        in lookup
    )


def test_gate_human_decision_requires_exact_pinned_versions() -> None:
    source = Path("app/gate_assessment/application.py").read_text()
    complete_source = source.split("async def complete_gate_review", 1)[1]

    assert "_require_expected_version(" in complete_source
    assert "review.gate_assessment_version != command.expected_version" in complete_source
    assert (
        "review.gate_definition_version_id"
        in complete_source
        and "command.expected_gate_definition_version_id" in complete_source
    )
    assert "snapshot.id != command.expected_profile_snapshot_id" in complete_source
    assert (
        "snapshot.snapshot_version"
        in complete_source
        and "command.expected_profile_snapshot_version" in complete_source
    )
    assert "load_assessor_pre_decision_read(" in complete_source


def test_gate_human_decision_event_and_outbox_are_atomic() -> None:
    source = Path("app/gate_assessment/application.py").read_text()
    complete_source = source.split("async def complete_gate_review", 1)[1]

    event_index = complete_source.index("record_event(")
    commit_index = complete_source.index("await db.commit()")
    assert event_index < commit_index
    assert complete_source.count("await db.commit()") == 1

    event_source = source.split(
        "def _new_gate_review_completed_event", 1
    )[1].split(
        "async def complete_gate_review", 1
    )[0]
    assert 'event_type="gate.review_completed.v1"' in event_source
    assert 'aggregate_type="GateAssessment"' in event_source
    assert 'actor={"type": "PERSON"' in event_source
    assert '"profile_snapshot_id"' in event_source
    assert '"profile_snapshot_version"' in event_source
    assert '"gate_definition_version_id"' in event_source
    assert '"decision_state"' in event_source


def test_gate_human_decision_has_no_ai_system_or_cross_context_mutation() -> None:
    source = Path("app/gate_assessment/application.py").read_text()
    complete_source = source.split("async def complete_gate_review", 1)[1]

    assert "app.flag_profile" not in complete_source
    assert "CapabilityClaim" not in complete_source
    assert "ResponsibilityRecommendation" not in complete_source
    assert "FlagBoard" not in complete_source
    assert "Appointment" not in complete_source
    assert '"type": "SYSTEM"' not in complete_source
    assert '"type": "AI"' not in complete_source


def test_gate_human_decision_never_converts_missing_evidence_to_fail() -> None:
    source = Path("app/gate_assessment/application.py").read_text()
    complete_source = source.split("async def complete_gate_review", 1)[1]

    assert "evidence_gaps" not in complete_source
    assert "insufficient" not in complete_source.lower()
    assert "decision_state = GateAssessmentState.FAIL" not in complete_source
    assert "assessment.state = decision_state" in complete_source


def test_gate_human_decision_exact_retry_contract() -> None:
    from app.gate_assessment.application import (
        CompleteGateReviewCommand,
        _gate_decision_retry_matches,
    )
    from app.gate_assessment.models import GateReviewDecision

    review_id = UUID("a3000000-0000-0000-0000-000000000001")
    reviewer_id = UUID("00000000-0000-0000-0000-000000000106")
    definition_version_id = UUID("a3000000-0000-0000-0000-000000000002")
    snapshot_id = UUID("a3000000-0000-0000-0000-000000000003")
    command = CompleteGateReviewCommand(
        organization_context_id=UUID(
            "00000000-0000-0000-0000-000000000001"
        ),
        gate_review_id=review_id,
        reviewer_id=reviewer_id,
        decision_state="PASS_CONFIRMED",
        rationale="Pinned evidence supports the accountable decision.",
        expected_version=5,
        expected_gate_definition_version_id=definition_version_id,
        expected_profile_snapshot_id=snapshot_id,
        expected_profile_snapshot_version=2,
        idempotency_key="gate-decision-1",
        trace_id="trace-gate-decision-1",
    )
    decision = GateReviewDecision(
        gate_review_id=review_id,
        reviewer_id=reviewer_id,
        decision_state="PASS_CONFIRMED",
        rationale="Pinned evidence supports the accountable decision.",
        prior_assessment_version=5,
        gate_definition_version_id=definition_version_id,
        gate_profile_snapshot_id=snapshot_id,
        gate_profile_snapshot_version=2,
        decision_idempotency_key="gate-decision-1",
    )

    assert _gate_decision_retry_matches(
        decision,
        command=command,
        decision_state="PASS_CONFIRMED",
        rationale="Pinned evidence supports the accountable decision.",
        idempotency_key="gate-decision-1",
    )
    decision.decision_state = "FAIL"
    assert not _gate_decision_retry_matches(
        decision,
        command=command,
        decision_state="PASS_CONFIRMED",
        rationale="Pinned evidence supports the accountable decision.",
        idempotency_key="gate-decision-1",
    )


def test_gate_recovery_history_is_append_only_and_relational() -> None:
    from app.gate_assessment.models import (
        GateReassessment,
        GateReassessmentDecision,
        GateRemediation,
    )

    assert GateRemediation.__table__.schema == "gate_assessment"
    assert GateReassessment.__table__.schema == "gate_assessment"
    assert GateReassessmentDecision.__table__.schema == "gate_assessment"

    targets = {
        fk.target_fullname
        for table in (
            GateRemediation.__table__,
            GateReassessment.__table__,
            GateReassessmentDecision.__table__,
        )
        for fk in table.foreign_keys
    }
    assert targets
    assert all(target.startswith("gate_assessment.") for target in targets)

    migration_source = Path(
        "alembic/versions/0023_gate_remediation_reassessment.py"
    ).read_text()
    assert "reject_recovery_history_mutation" in migration_source
    assert migration_source.count("BEFORE UPDATE OR DELETE") == 1
    for table_name in (
        "gate_remediations",
        "gate_reassessments",
        "gate_reassessment_decisions",
    ):
        assert f'"{table_name}"' in migration_source


def test_gate_remediation_requires_human_backed_fail_state() -> None:
    source = Path("app/gate_assessment/recovery.py").read_text()
    failure_source = source.split(
        "async def _failure_is_human_decision", 1
    )[1].split(
        "async def _remediation_by_key", 1
    )[0]
    start_source = source.split(
        "async def start_gate_remediation", 1
    )[1].split(
        "async def _reassessment_by_key", 1
    )[0]

    assert "GateReviewDecision" in failure_source
    assert "GateReassessmentDecision" in failure_source
    assert "GateAssessmentState.FAIL.value" in failure_source
    assert "GateAssessmentState.REMEDIATION.value" in start_source
    assert "_failure_is_human_decision(" in start_source
    assert "GATE_FAILURE_DECISION_NOT_FOUND" in start_source
    assert ".with_for_update()" in start_source
    assert "_require_expected_version(" in start_source


def test_gate_reassessment_pins_new_current_profile_snapshot() -> None:
    source = Path("app/gate_assessment/recovery.py").read_text()
    open_source = source.split(
        "async def open_gate_reassessment", 1
    )[1].split(
        "async def _require_snapshot_lineage_complete", 1
    )[0]

    assert "reader: CurrentFlagProfileReader" in open_source
    assert "current_profile = await reader.load(" in open_source
    assert "_require_profile_scope(" in open_source
    assert "_next_snapshot_version(" in open_source
    assert "_persist_profile_snapshot(" in open_source
    assert "GateAssessmentState.REASSESSMENT.value" in open_source
    assert "GateRemediation.remediation_assessment_version" in open_source
    assert "GateProfileSnapshot" not in open_source.split(
        "snapshot = _persist_profile_snapshot(", 1
    )[0].split("current_profile = await reader.load(", 1)[0]


def test_gate_reassessment_decision_is_human_only_pass_or_fail() -> None:
    source = Path("app/gate_assessment/recovery.py").read_text()
    contract_source = source.split(
        "def _require_reassessment_decision_contract", 1
    )[1].split(
        "def _reassessment_decision_retry_matches", 1
    )[0]
    complete_source = source.split(
        "async def complete_gate_reassessment", 1
    )[1]

    assert "GateAssessmentState.PASS.value" in contract_source
    assert "GateAssessmentState.FAIL.value" in contract_source
    assert "PASS_CONFIRMED" not in contract_source
    assert "Human reassessment decision must be PASS or FAIL." in contract_source
    assert "GATE_DECISION_RATIONALE_REQUIRED" in contract_source
    assert "reviewer_id=command.reviewer_id" in complete_source
    assert "assessment.state = decision_state" in complete_source
    assert "gate_transition_allowed(assessment.state, decision_state)" in complete_source


def test_gate_reassessment_decision_requires_exact_pinned_versions() -> None:
    source = Path("app/gate_assessment/recovery.py").read_text()
    complete_source = source.split(
        "async def complete_gate_reassessment", 1
    )[1]

    assert "_require_expected_version(" in complete_source
    assert (
        "reassessment.reassessment_assessment_version"
        in complete_source
    )
    assert "command.expected_gate_definition_version_id" in complete_source
    assert "command.expected_profile_snapshot_id" in complete_source
    assert "command.expected_profile_snapshot_version" in complete_source
    assert "_require_snapshot_lineage_complete(" in complete_source
    assert ".with_for_update()" in complete_source


def test_gate_reassessment_decision_event_is_atomic_and_person_actor() -> None:
    source = Path("app/gate_assessment/recovery.py").read_text()
    event_source = source.split(
        "def _new_reassessment_completed_event", 1
    )[1].split(
        "async def complete_gate_reassessment", 1
    )[0]
    complete_source = source.split(
        "async def complete_gate_reassessment", 1
    )[1]

    assert 'event_type="gate.review_completed.v1"' in event_source
    assert '"review_kind": "REASSESSMENT"' in event_source
    assert 'actor={"type": "PERSON"' in event_source
    assert '"profile_snapshot_id"' in event_source
    assert '"profile_snapshot_version"' in event_source
    assert '"decision_state"' in event_source

    assert complete_source.count("await db.commit()") == 1
    assert complete_source.index("record_event(") < complete_source.index(
        "await db.commit()"
    )


def test_gate_recovery_never_auto_recovers_or_mutates_other_contexts() -> None:
    source = Path("app/gate_assessment/recovery.py").read_text()
    lowered = source.lower()

    for forbidden in (
        "overall_score",
        "weighted_score",
        "readiness_score",
        "threshold_value",
        "auto_recover",
        "automatic_recovery",
    ):
        assert forbidden not in lowered

    for forbidden in (
        "CapabilityClaim",
        "ResponsibilityRecommendation",
        "FlagBoard",
        "Appointment",
        "app.flag_profile.models",
        "app.patterns",
        "app.evidence",
    ):
        assert forbidden not in source

    assert '"type": "SYSTEM"' not in source
    assert '"type": "AI"' not in source


def test_gate_recovery_does_not_rewrite_prior_review_decisions() -> None:
    source = Path("app/gate_assessment/recovery.py").read_text()

    assert "GateReviewDecision." in source
    assert "GateReassessmentDecision." in source
    assert "GateReviewDecision(" not in source
    complete_source = source.split(
        "async def complete_gate_reassessment", 1
    )[1]
    assert "GateReassessmentDecision(" in complete_source

    migration_source = Path(
        "alembic/versions/0023_gate_remediation_reassessment.py"
    ).read_text()
    assert "gate_review_decisions" not in migration_source
    assert "gate_reviews" not in migration_source


def test_gate_reassessment_decision_db_allows_only_pass_or_fail() -> None:
    migration_source = Path(
        "alembic/versions/0023_gate_remediation_reassessment.py"
    ).read_text()
    assert "decision_state IN ('PASS', 'FAIL')" in migration_source
    assert "PASS_CONFIRMED" not in migration_source


def test_candidate_gate_projection_is_gate_owned_and_self_scoped() -> None:
    source = Path("app/gate_assessment/candidate_projection.py").read_text()

    assert "GateAssessment.organization_context_id" in source
    assert "GateAssessment.subject_person_id == subject_person_id" in source
    assert "GateProfileSnapshot.organization_context_id" in source
    assert "GateProfileSnapshot.subject_person_id == subject_person_id" in source

    for forbidden in (
        "app.flag_profile",
        "app.patterns",
        "app.evidence",
        "GateReviewDecision",
        "GateReassessmentDecision",
        "ProfileUpdateCase",
    ):
        assert forbidden not in source


def test_candidate_gate_projection_exposes_only_safe_gate_facts() -> None:
    from dataclasses import fields

    from app.gate_assessment.candidate_projection import CandidateGateItem

    assert {field.name for field in fields(CandidateGateItem)} == {
        "gate_code",
        "gate_name",
        "status",
        "evidence_gaps",
        "remediation_status",
    }


def test_candidate_gate_projection_uses_only_next_evidence_needed_for_gaps() -> None:
    source = Path("app/gate_assessment/candidate_projection.py").read_text()
    gap_source = source.split(
        "async def _latest_snapshot_gaps", 1
    )[1].split(
        "async def load_candidate_gate_projection", 1
    )[0]

    assert "claim.next_evidence_needed.strip()" in gap_source
    for forbidden in (
        "reviewed_by",
        "rationale",
        "source_reference",
        "source_observation_id",
        "interpretation_id",
        "evidence_set_member_id",
        "confidence_in_claim",
        "pattern_status",
        "relationship",
        "prompt_contamination",
        "source_independence_group",
    ):
        assert forbidden not in gap_source


def test_candidate_gate_projection_remediation_status_is_existing_state_only() -> None:
    from app.gate_assessment.candidate_projection import (
        _candidate_remediation_status,
    )

    assert _candidate_remediation_status("REMEDIATION") == "REMEDIATION"
    assert _candidate_remediation_status("REASSESSMENT") == "REASSESSMENT"
    for state in (
        "UNPROVEN",
        "PASS",
        "AT_RISK",
        "REVIEW_REQUIRED",
        "PASS_CONFIRMED",
        "FAIL",
    ):
        assert _candidate_remediation_status(state) is None


def test_candidate_gate_projection_has_no_score_threshold_or_hidden_trigger_logic() -> None:
    source = Path("app/gate_assessment/candidate_projection.py").read_text()
    lowered = source.lower()

    for forbidden in (
        "overall_score",
        "weighted_score",
        "readiness_score",
        "threshold_value",
        "trigger_reason",
        "risk_trigger",
        "hidden_trigger",
        "ai_proposal",
        "system_proposal",
    ):
        assert forbidden not in lowered
