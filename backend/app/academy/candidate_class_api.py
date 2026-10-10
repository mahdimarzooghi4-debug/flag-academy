"""Candidate-safe discovery of real classes for the report-card workspace."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.academy.models import ClassOffering, Cohort, CohortMembership
from app.db import get_session
from app.errors import AppError
from app.identity.auth import ActorContext, require_role

router = APIRouter(prefix="/api/v1", tags=["academy"])


class CandidateClassOfferingResponse(BaseModel):
    class_offering_id: UUID
    cohort_id: UUID
    title: str
    primary_capability_version_id: UUID
    status: str


@router.get(
    "/cohorts/{cohort_id}/class-offerings",
    response_model=list[CandidateClassOfferingResponse],
)
async def candidate_cohort_class_offerings(
    cohort_id: UUID,
    actor: Annotated[ActorContext, Depends(require_role("CANDIDATE"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> list[CandidateClassOfferingResponse]:
    """Show only classes belonging to the candidate's own tenant-scoped cohort."""
    membership = (
        await db.execute(
            select(CohortMembership.id)
            .join(Cohort, CohortMembership.cohort_id == Cohort.id)
            .where(
                Cohort.id == cohort_id,
                Cohort.organization_context_id == actor.organization_context_id,
                CohortMembership.person_id == actor.person_id,
                CohortMembership.member_type == "CANDIDATE",
            )
        )
    ).scalar_one_or_none()
    if membership is None:
        raise AppError("COHORT_NOT_FOUND", "Cohort not found.", status_code=404)

    classes = (
        await db.execute(
            select(ClassOffering)
            .where(ClassOffering.cohort_id == cohort_id)
            .order_by(ClassOffering.title, ClassOffering.id)
        )
    ).scalars().all()
    return [
        CandidateClassOfferingResponse(
            class_offering_id=item.id,
            cohort_id=item.cohort_id,
            title=item.title,
            primary_capability_version_id=item.primary_capability_version_id,
            status=item.status,
        )
        for item in classes
    ]
