from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.academy.models import ClassOffering, Cohort, Session
from app.db import get_session
from app.errors import AppError
from app.identity.auth import ActorContext, get_actor

router = APIRouter(prefix="/api/v1", tags=["academy"])


@router.get("/cohorts/{cohort_id}/schedule")
async def cohort_schedule(
    cohort_id: UUID,
    actor: Annotated[ActorContext, Depends(get_actor)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    cohort = (
        await session.execute(
            select(Cohort).where(
                Cohort.id == cohort_id,
                Cohort.organization_context_id == actor.organization_context_id,
            )
        )
    ).scalar_one_or_none()
    if cohort is None:
        raise AppError("COHORT_NOT_FOUND", "Cohort not found.", status_code=404)

    rows = (
        await session.execute(
            select(Session, ClassOffering)
            .join(ClassOffering, Session.class_offering_id == ClassOffering.id)
            .where(ClassOffering.cohort_id == cohort_id)
            .order_by(Session.starts_at)
        )
    ).all()
    return {
        "cohort_id": str(cohort.id),
        "items": [
            {
                "session_id": str(s.id),
                "class_title": c.title,
                "title": s.title,
                "starts_at": s.starts_at,
                "ends_at": s.ends_at,
                "delivery_mode": s.delivery_mode,
                "status": s.status,
            }
            for s, c in rows
        ],
    }
