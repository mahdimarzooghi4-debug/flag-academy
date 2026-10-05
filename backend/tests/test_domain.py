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
    project_candidate_visible_state,
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
    assert MissionActionType.DECIDE.value == "DECIDE"


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


def test_scheduled_effect_payload_hides_internal_effect() -> None:
    assert candidate_event_visible("scheduled_effect.created")
    assert candidate_event_visible("scheduled_effect.applied")
    visible = candidate_event_payload(
        "scheduled_effect.applied",
        {
            "effect_code": "EXECUTIVE_CHECKPOINT_DUE",
            "label": "Executive recovery checkpoint",
            "due_at": "2026-10-05T10:00:00+00:00",
            "effect_applied": {
                "stakeholder": {"executive_checkpoint": "DUE"},
            },
            "world_version_before": 2,
            "world_version_after": 3,
        },
    )
    assert visible["effect_code"] == "EXECUTIVE_CHECKPOINT_DUE"
    assert visible["world_version_after"] == 3
    assert "effect_applied" not in visible


def test_scheduled_effect_observation_is_factual_and_explicit() -> None:
    assert candidate_observation_visible("SCHEDULED_EFFECT_OBSERVED")
    visible = candidate_observation_payload(
        "SCHEDULED_EFFECT_OBSERVED",
        {
            "effect_code": "EXECUTIVE_CHECKPOINT_DUE",
            "due_at": "2026-10-05T10:00:00+00:00",
            "world_version_before": 2,
            "world_version_after": 3,
            "judgment": "candidate waited too long",
        },
    )
    assert "judgment" not in visible
    assert visible["world_version_before"] == 2
    assert visible["world_version_after"] == 3
