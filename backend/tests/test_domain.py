from uuid import UUID

from app.curriculum.domain import CAPABILITY_CODES, LearningState, ProofState
from app.journey.domain import CandidateJourneyState
from app.learning.domain import (
    LearningPhase,
    LearningUnitProgressState,
    LearningUnitType,
    PracticeAttemptStatus,
    SubmissionStatus,
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
    assert LearningUnitProgressState.IN_PROGRESS.value == "IN_PROGRESS"
    assert LearningUnitProgressState.COMPLETED.value == "COMPLETED"
    assert PracticeAttemptStatus.SUBMITTED.value == "SUBMITTED"
    assert PracticeAttemptStatus.FEEDBACK_PROVIDED.value == "FEEDBACK_PROVIDED"
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
