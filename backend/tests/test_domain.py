from app.curriculum.domain import CAPABILITY_CODES, LearningState, ProofState
from app.journey.domain import CandidateJourneyState


def test_pm_curriculum_has_15_capabilities() -> None:
    assert len(CAPABILITY_CODES) == 15
    assert len(set(CAPABILITY_CODES)) == 15


def test_learning_completion_is_not_proof() -> None:
    assert LearningState.LEARNING_COMPLETED.value != ProofState.PROVEN.value


def test_candidate_journey_states_are_explicit() -> None:
    assert CandidateJourneyState.ACTIVE.value == "ACTIVE"
    assert CandidateJourneyState.WITHDRAWN.value == "WITHDRAWN"
