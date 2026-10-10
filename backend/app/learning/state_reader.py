"""Shared Learning-owned qualitative state computation.

This is educational progress only. It cannot create formal Evidence, a
CapabilityClaim, or a Gate decision. Absent requirements are UNKNOWN.
"""

from collections.abc import Sequence
from typing import Literal

LearningState = Literal["TO_LEARN", "IN_LEARNING", "LEARNING_COMPLETED"]


def derive_learning_state(
    *,
    unit_progress_states: Sequence[str | None],
    assignment_submitted: Sequence[bool],
) -> LearningState | None:
    """Reuse the established CandidateHome rule across class read models.

    The *presence* of a Submission counts as a submitted assignment, exactly
    as in the existing projection. Practice feedback is not a completion gate.
    No numeric scoring, attendance or formal proof is considered.
    """
    if not unit_progress_states and not assignment_submitted:
        return None
    if all(state == "COMPLETED" for state in unit_progress_states) and all(
        assignment_submitted
    ):
        return "LEARNING_COMPLETED"
    if any(state is not None for state in unit_progress_states) or any(
        assignment_submitted
    ):
        return "IN_LEARNING"
    return "TO_LEARN"
