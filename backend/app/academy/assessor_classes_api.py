"""P23-09B: Assessor-owned discovery of currently authorized Academy classes.

No global class catalog, no historic grants, no Evidence/Gate delegation.
Every classroom resource independently re-checks the live grant.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.academy.assessor_grants_policy import current_utc
from app.academy.models import AssessorClassGrant, ClassOffering, Cohort
from app.db import get_session
from app.identity.auth import ActorContext, require_role
from app.identity.public_reader import has_organization_role

router = APIRouter(prefix="/api/v1/me/academy", tags=["academy"])


class AssignedAssessorClass(BaseModel):
    class_offering_id: UUID
    cohort_id: UUID
    title: str
    grant_id: UUID
    grant_version: int
    starts_at: str
    ends_at: str


class AssignedAssessorClassPage(BaseModel):
    items: list[AssignedAssessorClass]
    next_offset: int | None


@router.get("/assessor-classes", response_model=AssignedAssessorClassPage)
async def list_my_assessor_classes(
    actor: Annotated[ActorContext, Depends(require_role("ASSESSOR"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AssignedAssessorClassPage:
    """Read only the actor's live mandates in their current organization."""
    if not await has_organization_role(
        db,
        person_id=actor.person_id,
        organization_id=actor.organization_context_id,
        role="ASSESSOR",
    ):
        return AssignedAssessorClassPage(items=[], next_offset=None)

    now = current_utc()
    rows = (
        await db.execute(
            select(AssessorClassGrant, ClassOffering, Cohort)
            .join(ClassOffering, AssessorClassGrant.class_offering_id == ClassOffering.id)
            .join(Cohort, ClassOffering.cohort_id == Cohort.id)
            .where(
                AssessorClassGrant.organization_context_id == actor.organization_context_id,
                Cohort.organization_context_id == actor.organization_context_id,
                AssessorClassGrant.assessor_person_id == actor.person_id,
                AssessorClassGrant.revoked_at.is_(None),
                AssessorClassGrant.starts_at <= now,
                AssessorClassGrant.ends_at > now,
                ClassOffering.status == "ACTIVE",
                Cohort.status == "ACTIVE",
            )
            .order_by(ClassOffering.id, AssessorClassGrant.id)
            .offset(offset)
            .limit(limit + 1)
        )
    ).all()
    return AssignedAssessorClassPage(
        items=[
            AssignedAssessorClass(
                class_offering_id=offering.id,
                cohort_id=cohort.id,
                title=offering.title,
                grant_id=grant.id,
                grant_version=grant.version,
                starts_at=grant.starts_at.isoformat(),
                ends_at=grant.ends_at.isoformat(),
            )
            for grant, offering, cohort in rows[:limit]
        ],
        next_offset=offset + limit if len(rows) > limit else None,
    )
