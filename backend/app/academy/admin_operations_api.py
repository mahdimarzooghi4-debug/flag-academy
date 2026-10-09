"""Tenant-scoped Academy Admin discovery for real Cohort and ClassOffering records.

The catalog never synthesizes enrollment, class ownership, or permission.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.academy.models import ClassOffering, Cohort
from app.db import get_session
from app.errors import AppError
from app.identity.auth import ActorContext, require_role

router = APIRouter(prefix="/api/v1/admin/academy", tags=["academy"])


class AdminCohortItem(BaseModel):
    cohort_id: UUID
    code: str
    name: str
    track_code: str
    status: str


class AdminCohortPage(BaseModel):
    items: list[AdminCohortItem]
    next_offset: int | None


class AdminClassItem(BaseModel):
    class_offering_id: UUID
    cohort_id: UUID
    title: str
    primary_capability_version_id: UUID
    status: str


class AdminClassPage(BaseModel):
    cohort_id: UUID
    items: list[AdminClassItem]
    next_offset: int | None


@router.get("/cohorts", response_model=AdminCohortPage)
async def admin_academy_cohorts(
    actor: Annotated[ActorContext, Depends(require_role("ACADEMY_ADMIN"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AdminCohortPage:
    """Discover only cohorts in the actor's authorized organization."""
    rows = (
        await db.execute(
            select(Cohort)
            .where(Cohort.organization_context_id == actor.organization_context_id)
            .order_by(Cohort.code, Cohort.id)
            .offset(offset)
            .limit(limit + 1)
        )
    ).scalars().all()
    return AdminCohortPage(
        items=[
            AdminCohortItem(
                cohort_id=item.id,
                code=item.code,
                name=item.name,
                track_code=item.track_code,
                status=item.status,
            )
            for item in rows[:limit]
        ],
        next_offset=offset + limit if len(rows) > limit else None,
    )


@router.get("/cohorts/{cohort_id}/classes", response_model=AdminClassPage)
async def admin_academy_cohort_classes(
    cohort_id: UUID,
    actor: Annotated[ActorContext, Depends(require_role("ACADEMY_ADMIN"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AdminClassPage:
    """Validate organization ownership before revealing a cohort's class list."""
    cohort = (
        await db.execute(
            select(Cohort.id).where(
                Cohort.id == cohort_id,
                Cohort.organization_context_id == actor.organization_context_id,
            )
        )
    ).scalar_one_or_none()
    if cohort is None:
        raise AppError("COHORT_NOT_FOUND", "Cohort not found.", status_code=404)

    rows = (
        await db.execute(
            select(ClassOffering)
            .where(ClassOffering.cohort_id == cohort_id)
            .order_by(ClassOffering.title, ClassOffering.id)
            .offset(offset)
            .limit(limit + 1)
        )
    ).scalars().all()
    return AdminClassPage(
        cohort_id=cohort_id,
        items=[
            AdminClassItem(
                class_offering_id=item.id,
                cohort_id=item.cohort_id,
                title=item.title,
                primary_capability_version_id=item.primary_capability_version_id,
                status=item.status,
            )
            for item in rows[:limit]
        ],
        next_offset=offset + limit if len(rows) > limit else None,
    )
