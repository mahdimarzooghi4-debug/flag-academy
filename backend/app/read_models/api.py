from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.errors import AppError
from app.identity.auth import ActorContext, require_role
from app.read_models.models import CandidateHomeProjection, InstructorHomeProjection

router = APIRouter(prefix="/api/v1/me", tags=["read-models"])


class SessionSummary(BaseModel):
    session_id: str
    title: str
    starts_at: datetime
    ends_at: datetime
    delivery_mode: str


class JourneySummary(BaseModel):
    track: str
    state: str


class CohortSummary(BaseModel):
    id: str
    name: str


class WaveSummary(BaseModel):
    code: str
    name: str


class LearnItem(BaseModel):
    capability_version_id: str
    name: str
    learning_state: str
    next_session: SessionSummary | None = None


class ProveItem(BaseModel):
    capability_version_id: str
    name: str
    proof_state: str


class LearningTask(BaseModel):
    id: str
    task_type: str
    title: str
    class_offering_id: str
    capability_version_id: str
    status: str
    body: str
    due_at: datetime | None = None
    submission_id: str | None = None
    feedback_text: str | None = None


class ProfileSummary(BaseModel):
    status: str


class CandidateHomeResponse(BaseModel):
    journey: JourneySummary
    cohort: CohortSummary
    current_wave: WaveSummary
    upcoming_sessions: list[SessionSummary]
    what_to_learn: list[LearnItem]
    what_to_prove: list[ProveItem]
    learning_tasks: list[LearningTask]
    open_missions: list[dict]
    profile_summary: ProfileSummary
    processing_states: list[dict]


class AssignedClass(BaseModel):
    id: str
    title: str


class InstructorLearningUnit(BaseModel):
    id: str
    title: str
    phase: str
    unit_type: str
    body: str


class InstructorAssignment(BaseModel):
    id: str
    title: str
    instructions: str
    due_at: datetime | None = None
    status: str


class InstructorSubmission(BaseModel):
    id: str
    assignment_id: str
    assignment_title: str
    candidate_id: str
    candidate_name: str
    content_text: str
    status: str
    feedback_text: str | None = None


class InstructorHomeResponse(BaseModel):
    assigned_cohort: CohortSummary
    assigned_classes: list[AssignedClass]
    upcoming_sessions: list[SessionSummary]
    candidate_count: int
    capability_focus: str
    current_wave: WaveSummary
    learning_units: list[InstructorLearningUnit]
    assignments: list[InstructorAssignment]
    submissions: list[InstructorSubmission]


@router.get("/candidate-home", response_model=CandidateHomeResponse)
async def candidate_home(
    actor: Annotated[ActorContext, Depends(require_role("CANDIDATE"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CandidateHomeResponse:
    projection = (
        await session.execute(
            select(CandidateHomeProjection).where(
                CandidateHomeProjection.person_id == actor.person_id,
                CandidateHomeProjection.organization_context_id
                == actor.organization_context_id,
            )
        )
    ).scalar_one_or_none()
    if projection is None:
        raise AppError(
            "CANDIDATE_JOURNEY_NOT_FOUND",
            "Candidate journey was not found.",
            status_code=404,
        )
    return CandidateHomeResponse.model_validate(projection.payload)


@router.get("/instructor-home", response_model=InstructorHomeResponse)
async def instructor_home(
    actor: Annotated[ActorContext, Depends(require_role("INSTRUCTOR"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> InstructorHomeResponse:
    projection = (
        await session.execute(
            select(InstructorHomeProjection).where(
                InstructorHomeProjection.person_id == actor.person_id,
                InstructorHomeProjection.organization_context_id
                == actor.organization_context_id,
            )
        )
    ).scalar_one_or_none()
    if projection is None:
        raise AppError(
            "INSTRUCTOR_ASSIGNMENT_NOT_FOUND",
            "Instructor assignment was not found.",
            status_code=404,
        )
    return InstructorHomeResponse.model_validate(projection.payload)
