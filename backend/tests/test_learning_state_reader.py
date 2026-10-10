"""Shared educational progress state must match existing CandidateHome semantics."""

from pathlib import Path

import pytest

from app.learning.state_reader import derive_learning_state


@pytest.mark.parametrize(
    ("unit_states", "submitted", "expected"),
    [
        ([], [], None),  # No active requirement: missing, not TO_LEARN
        ([None], [], "TO_LEARN"),
        ([], [False], "TO_LEARN"),
        (["IN_PROGRESS"], [], "IN_LEARNING"),
        ([None], [True], "IN_LEARNING"),
        (["COMPLETED"], [False], "IN_LEARNING"),
        ([None, "COMPLETED"], [True], "IN_LEARNING"),
        (["COMPLETED"], [True], "LEARNING_COMPLETED"),
        (["COMPLETED", "COMPLETED"], [True, True], "LEARNING_COMPLETED"),
        ([], [True], "LEARNING_COMPLETED"),
    ],
)
def test_shared_learning_state_rule(unit_states, submitted, expected) -> None:
    assert (
        derive_learning_state(
            unit_progress_states=unit_states,
            assignment_submitted=submitted,
        )
        == expected
    )


def test_candidate_home_and_report_card_use_same_learning_owned_rule() -> None:
    projector = Path("app/read_models/projector.py").read_text()
    report = Path("app/academy/report_card_api.py").read_text()
    assert "from app.learning.state_reader import derive_learning_state" in projector
    assert "from app.learning.state_reader import derive_learning_state" in report
    assert "learning_state = derive_learning_state(" in projector
    assert "learning_state=derive_learning_state(" in report
    assert 'unit.status == "ACTIVE"' in report
    assert 'assignment.status == "ACTIVE"' in report
    assert "proof_state=None" in report
    assert "next_learning_focus=None" in report
    assert "CapabilityClaim(" not in report
    assert "GateAssessment(" not in report
    assert "db.commit(" not in report
