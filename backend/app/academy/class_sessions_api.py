"""Read-only class sessions for authorized instructor/admin workspaces."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.academy.assessor_access import has_live_assessor_class_access
from app.academy.models import ClassOffering, Cohort, InstructorAssignment, Session
from app.db import get_session
from app.errors import AppError
from app.identity.auth import ActorContext, require_role

router = APIRouter(prefix="/api/v1", tags=["academy"])


class ClassSessionRead(BaseModel):
    session_id: UUID
    class_offering_id: UUID
    title: str
    starts_at: datetime
    ends_at: datetime
    delivery_mode: str
    status: str


@router.get(
    "/class-offerings/{class_offering_id}/sessions",
    response_model=list[ClassSessionRead],
)
async def class_offering_sessions(
    class_offering_id: UUID,
    actor: Annotated[
        ActorContext, Depends(require_role("INSTRUCTOR", "ACADEMY_ADMIN", "ASSESSOR"))
    ],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> list[ClassSessionRead]:
    """No session data leaves the real tenant/class assignment boundary."""
    row = (
        await db.execute(
            select(ClassOffering.id)
            .join(Cohort, ClassOffering.cohort_id == Cohort.id)
            .where(
                ClassOffering.id == class_offering_id,
                Cohort.organization_context_id == actor.organization_context_id,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise AppError("CLASS_NOT_FOUND", "Class not found.", status_code=404)

    if "ACADEMY_ADMIN" not in actor.roles:
        assigned_instructor = False
        if "INSTRUCTOR" in actor.roles:
            assignment = (
                await db.execute(
                    select(InstructorAssignment.id).where(
                        InstructorAssignment.class_offering_id == class_offering_id,
                        InstructorAssignment.person_id == actor.person_id,
                    )
                )
            ).scalar_one_or_none()
            assigned_instructor = assignment is not None
        if not assigned_instructor and not await has_live_assessor_class_access(
            db, actor=actor, class_offering_id=class_offering_id
        ):
            raise AppError("CLASS_NOT_FOUND", "Class not found.", status_code=404)

    sessions = (
        await db.execute(
            select(Session)
            .where(Session.class_offering_id == class_offering_id)
            .order_by(Session.starts_at, Session.id)
        )
    ).scalars().all()
    return [
        ClassSessionRead(
            session_id=item.id,
            class_offering_id=item.class_offering_id,
            title=item.title,
            starts_at=item.starts_at,
            ends_at=item.ends_at,
            delivery_mode=item.delivery_mode,
            status=item.status,
        )
        for item in sessions
    ]
