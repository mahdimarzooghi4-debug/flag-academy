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
from app.flag_profile.domain import (
    CapabilityClaimState,
    CapabilityLevel,
    ClaimPatternRelationship,
    ProfileUpdateCaseState,
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
from app.patterns.contracts import _source_contract
from app.patterns.application import (
    AcceptedEvidenceSnapshot,
    _accepted_snapshot_matches_context,
    _new_pattern_updated_event,
    _require_create_expected_version,
    _require_pattern_candidate_create_expected_version,
    _require_pattern_review_expected_version,
    _reviewed_pattern_status_valid,
)
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
