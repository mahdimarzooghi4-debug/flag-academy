from uuid import UUID

from app.curriculum.domain import CAPABILITY_CODES, LearningState, ProofState
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
    delegation_preserves_candidate_accountability,
    preserves_candidate_accountability,
    project_candidate_visible_state,
    resource_allocation_transition_valid,
    runtime_transition_allowed,
)
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
