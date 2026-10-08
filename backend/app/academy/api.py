from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.academy.domain import attendance_resulting_version
from app.academy.models import (
    AttendanceRecord,
    AttendanceRevision,
    ClassOffering,
    Cohort,
    CohortMembership,
    InstructorAssignment,
    Session,
)
from app.db import get_session
from app.errors import AppError
from app.identity.auth import ActorContext, get_actor, require_role
from app.platform.events import new_event, record_event

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

    membership = (
        await session.execute(
            select(CohortMembership.id).where(
                CohortMembership.cohort_id == cohort_id,
                CohortMembership.person_id == actor.person_id,
            )
        )
    ).scalar_one_or_none()
    if membership is None and "ACADEMY_ADMIN" not in actor.roles:
        # Hide cohort existence from users who are not members.
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



class AttendanceMutationRequest(BaseModel):
    status: Literal["PRESENT", "ABSENT"]
    expected_version: int = Field(ge=0)
    idempotency_key: str = Field(min_length=1, max_length=160)


class AttendanceRecordResponse(BaseModel):
    id: UUID
    version: int
    session_id: UUID
    person_id: UUID
    status: str
    updated_by: UUID
    updated_at: datetime


class AttendanceListResponse(BaseModel):
    session_id: UUID
    items: list[AttendanceRecordResponse]


async def _load_session_context(
    db: AsyncSession,
    *,
    session_id: UUID,
    organization_context_id: UUID,
    for_update: bool = False,
) -> tuple[Session, ClassOffering, Cohort]:
    query = (
        select(Session, ClassOffering, Cohort)
        .join(
            ClassOffering,
            Session.class_offering_id == ClassOffering.id,
        )
        .join(
            Cohort,
            ClassOffering.cohort_id == Cohort.id,
        )
        .where(
            Session.id == session_id,
            Cohort.organization_context_id == organization_context_id,
        )
    )
    if for_update:
        query = query.with_for_update(of=Session)
    row = (await db.execute(query)).first()
    if row is None:
        raise AppError(
            "SESSION_NOT_FOUND",
            "Session not found.",
            status_code=404,
        )
    return row[0], row[1], row[2]


async def _require_attendance_subject(
    db: AsyncSession,
    *,
    cohort_id: UUID,
    person_id: UUID,
) -> None:
    membership = (
        await db.execute(
            select(CohortMembership.id).where(
                CohortMembership.cohort_id == cohort_id,
                CohortMembership.person_id == person_id,
            )
        )
    ).scalar_one_or_none()
    if membership is None:
        raise AppError(
            "ATTENDANCE_SUBJECT_NOT_FOUND",
            "Attendance subject not found.",
            status_code=404,
        )


async def _require_attendance_read_access(
    db: AsyncSession,
    *,
    actor: ActorContext,
    class_offering_id: UUID,
) -> None:
    if "ACADEMY_ADMIN" in actor.roles:
        return
    assignment = (
        await db.execute(
            select(InstructorAssignment.id).where(
                InstructorAssignment.class_offering_id == class_offering_id,
                InstructorAssignment.person_id == actor.person_id,
            )
        )
    ).scalar_one_or_none()
    if assignment is None:
        raise AppError(
            "SESSION_NOT_FOUND",
            "Session not found.",
            status_code=404,
        )


def _attendance_response(
    item: AttendanceRecord,
) -> AttendanceRecordResponse:
    return AttendanceRecordResponse(
        id=item.id,
        version=item.version,
        session_id=item.session_id,
        person_id=item.person_id,
        status=item.status,
        updated_by=item.updated_by,
        updated_at=item.updated_at,
    )


def _attendance_revision_response(
    item: AttendanceRevision,
) -> AttendanceRecordResponse:
    return AttendanceRecordResponse(
        id=item.attendance_record_id,
        version=item.resulting_version,
        session_id=item.session_id,
        person_id=item.person_id,
        status=item.resulting_status,
        updated_by=item.changed_by,
        updated_at=item.changed_at,
    )


@router.get(
    "/sessions/{session_id}/attendance",
    response_model=AttendanceListResponse,
)
async def list_session_attendance(
    session_id: UUID,
    actor: Annotated[
        ActorContext,
        Depends(require_role("ACADEMY_ADMIN", "INSTRUCTOR")),
    ],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> AttendanceListResponse:
    _, class_offering, _ = await _load_session_context(
        db,
        session_id=session_id,
        organization_context_id=actor.organization_context_id,
    )
    await _require_attendance_read_access(
        db,
        actor=actor,
        class_offering_id=class_offering.id,
    )
    items = (
        await db.execute(
            select(AttendanceRecord)
            .where(
                AttendanceRecord.organization_context_id
                == actor.organization_context_id,
                AttendanceRecord.session_id == session_id,
            )
            .order_by(
                AttendanceRecord.person_id,
                AttendanceRecord.id,
            )
        )
    ).scalars().all()
    return AttendanceListResponse(
        session_id=session_id,
        items=[_attendance_response(item) for item in items],
    )


@router.post(
    "/sessions/{session_id}/attendance/{person_id}",
    response_model=AttendanceRecordResponse,
)
async def record_session_attendance(
    session_id: UUID,
    person_id: UUID,
    body: AttendanceMutationRequest,
    actor: Annotated[
        ActorContext,
        Depends(require_role("ACADEMY_ADMIN")),
    ],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> AttendanceRecordResponse:
    class_session, class_offering, cohort = await _load_session_context(
        db,
        session_id=session_id,
        organization_context_id=actor.organization_context_id,
        for_update=True,
    )
    await _require_attendance_subject(
        db,
        cohort_id=cohort.id,
        person_id=person_id,
    )

    previous_command = (
        await db.execute(
            select(AttendanceRevision).where(
                AttendanceRevision.organization_context_id
                == actor.organization_context_id,
                AttendanceRevision.changed_by == actor.person_id,
                AttendanceRevision.idempotency_key
                == body.idempotency_key,
            )
        )
    ).scalar_one_or_none()
    if previous_command is not None:
        if (
            previous_command.session_id != session_id
            or previous_command.person_id != person_id
            or previous_command.expected_version != body.expected_version
            or previous_command.resulting_status != body.status
        ):
            raise AppError(
                "IDEMPOTENCY_CONFLICT",
                "Idempotency key was already used with different attendance input.",
                status_code=409,
            )
        return _attendance_revision_response(previous_command)

    current = (
        await db.execute(
            select(AttendanceRecord)
            .where(
                AttendanceRecord.organization_context_id
                == actor.organization_context_id,
                AttendanceRecord.session_id == session_id,
                AttendanceRecord.person_id == person_id,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()

    current_version = 0 if current is None else current.version
    if body.expected_version != current_version:
        raise AppError(
            "ATTENDANCE_VERSION_CONFLICT",
            "Attendance record changed. Refresh before retrying.",
            status_code=409,
            details={"current_version": current_version},
        )

    now = datetime.now(UTC)
    prior_version = None if current is None else current.version
    prior_status = None if current is None else current.status
    resulting_version = attendance_resulting_version(
        current_status=prior_status,
        current_version=current_version,
        requested_status=body.status,
    )

    created = current is None
    changed = created or prior_status != body.status
    if current is None:
        current = AttendanceRecord(
            id=uuid4(),
            version=resulting_version,
            organization_context_id=actor.organization_context_id,
            session_id=class_session.id,
            person_id=person_id,
            status=body.status,
            created_by=actor.person_id,
            updated_by=actor.person_id,
            created_at=now,
            updated_at=now,
        )
        db.add(current)
    elif changed:
        current.version = resulting_version
        current.status = body.status
        current.updated_by = actor.person_id
        current.updated_at = now
    else:
        # Keep the business version stable for a semantic no-op while making
        # the accepted command response exactly reproducible from its audit
        # revision on an idempotent retry.
        current.updated_by = actor.person_id
        current.updated_at = now

    revision = AttendanceRevision(
        id=uuid4(),
        attendance_record_id=current.id,
        organization_context_id=actor.organization_context_id,
        session_id=class_session.id,
        person_id=person_id,
        expected_version=body.expected_version,
        prior_version=prior_version,
        prior_status=prior_status,
        resulting_version=resulting_version,
        resulting_status=body.status,
        changed_by=actor.person_id,
        changed_at=now,
        idempotency_key=body.idempotency_key,
    )
    db.add(revision)

    if changed:
        record_event(
            db,
            new_event(
                event_type=(
                    "academy.attendance_recorded.v1"
                    if created
                    else "academy.attendance_corrected.v1"
                ),
                aggregate_type="AttendanceRecord",
                aggregate_id=current.id,
                aggregate_version=resulting_version,
                actor={
                    "type": "PERSON",
                    "id": str(actor.person_id),
                },
                organization_context_id=actor.organization_context_id,
                data_classification="INTERNAL",
                payload={
                    "attendance_record_id": str(current.id),
                    "session_id": str(class_session.id),
                    "class_offering_id": str(class_offering.id),
                    "cohort_id": str(cohort.id),
                    "person_id": str(person_id),
                    "status": body.status,
                    "prior_status": prior_status,
                },
                trace_id=actor.trace_id,
            ),
        )

    await db.commit()
    return _attendance_response(current)
