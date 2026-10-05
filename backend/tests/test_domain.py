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
    apply_world_effect,
    assignment_transition_allowed,
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
