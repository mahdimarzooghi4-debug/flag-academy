from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.errors import AppError
from app.identity.auth import ActorContext, require_role
from app.read_models.models import CandidateHomeProjection, InstructorHomeProjection

router = APIRouter(prefix="/api/v1/me", tags=["read-models"])


@router.get("/candidate-home")
async def candidate_home(
    actor: Annotated[ActorContext, Depends(require_role("CANDIDATE"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
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
    return projection.payload


@router.get("/instructor-home")
async def instructor_home(
    actor: Annotated[ActorContext, Depends(require_role("INSTRUCTOR"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
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
    return projection.payload
