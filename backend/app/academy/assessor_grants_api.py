"""P23-09 administrative Assessor grants. No Evidence, Gate or classroom read grant yet."""

from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.academy.assessor_grants_policy import current_utc
from app.academy.models import (
    AssessorClassGrant,
    AssessorClassGrantRevision,
    ClassOffering,
    Cohort,
)
from app.db import get_session
from app.errors import AppError
from app.identity.auth import ActorContext, require_role
from app.identity.public_reader import has_organization_role
from app.platform.events import new_event, record_event

router = APIRouter(prefix="/api/v1/admin/academy", tags=["academy"])


def _aware_time(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("An explicit timezone-aware datetime is required")
    return value.astimezone(UTC)


class GrantCreateRequest(BaseModel):
    assessor_person_id: UUID
    starts_at: datetime
    ends_at: datetime
    idempotency_key: str = Field(min_length=1, max_length=160)

    @field_validator("starts_at", "ends_at")
    @classmethod
    def aware_timestamp(cls, value: datetime) -> datetime:
        return _aware_time(value)

    @model_validator(mode="after")
    def window(self) -> "GrantCreateRequest":
        if self.ends_at <= self.starts_at:
            raise ValueError("Grant end must be after start")
        return self


class GrantExtendRequest(BaseModel):
    expected_version: int = Field(ge=1)
    ends_at: datetime
    reason: str = Field(min_length=1, max_length=500)
    idempotency_key: str = Field(min_length=1, max_length=160)

    @field_validator("ends_at")
    @classmethod
    def aware_timestamp(cls, value: datetime) -> datetime:
        return _aware_time(value)


class GrantRevokeRequest(BaseModel):
    expected_version: int = Field(ge=1)
    reason: str = Field(min_length=1, max_length=500)
    idempotency_key: str = Field(min_length=1, max_length=160)


class GrantResponse(BaseModel):
    grant_id: UUID
    version: int
    organization_context_id: UUID
    class_offering_id: UUID
    assessor_person_id: UUID
    starts_at: datetime
    ends_at: datetime
    revoked_at: datetime | None


def _response(grant: AssessorClassGrant) -> GrantResponse:
    return GrantResponse(
        grant_id=grant.id,
        version=grant.version,
        organization_context_id=grant.organization_context_id,
        class_offering_id=grant.class_offering_id,
        assessor_person_id=grant.assessor_person_id,
        starts_at=grant.starts_at,
        ends_at=grant.ends_at,
        revoked_at=grant.revoked_at,
    )


def _response_from_revision(item: AssessorClassGrantRevision) -> GrantResponse:
    """Idempotent replay returns the original accepted command result, not live mutable state."""
    return GrantResponse(
        grant_id=item.grant_id,
        version=item.resulting_version,
        organization_context_id=item.organization_context_id,
        class_offering_id=item.class_offering_id,
        assessor_person_id=item.assessor_person_id,
        starts_at=item.starts_at,
        ends_at=item.ends_at,
        revoked_at=item.revoked_at,
    )


async def _class_in_tenant(
    db: AsyncSession, *, class_offering_id: UUID, organization_id: UUID
) -> tuple[ClassOffering, Cohort]:
    row = (
        await db.execute(
            select(ClassOffering, Cohort)
            .join(Cohort, ClassOffering.cohort_id == Cohort.id)
            .where(
                ClassOffering.id == class_offering_id,
                Cohort.organization_context_id == organization_id,
            )
            .with_for_update(of=ClassOffering)
        )
    ).first()
    if row is None:
        raise AppError("CLASS_NOT_FOUND", "Class not found.", status_code=404)
    return row[0], row[1]


def _require_operational_class(offering: ClassOffering, cohort: Cohort) -> None:
    # No assumed terminal-class lifecycle: only explicitly ACTIVE records
    # are eligible. Future class-status semantics require a separate contract.
    if offering.status != "ACTIVE" or cohort.status != "ACTIVE":
        raise AppError(
            "CLASS_NOT_ACTIVE", "Class is not operational.", status_code=409
        )


async def _prior_command(
    db: AsyncSession, *, actor: ActorContext, key: str
) -> AssessorClassGrantRevision | None:
    return (
        await db.execute(
            select(AssessorClassGrantRevision).where(
                AssessorClassGrantRevision.organization_context_id
                == actor.organization_context_id,
                AssessorClassGrantRevision.actor_id == actor.person_id,
                AssessorClassGrantRevision.idempotency_key == key,
            )
        )
    ).scalar_one_or_none()


def _assert_replay(
    prior: AssessorClassGrantRevision,
    *,
    action: Literal["CREATE", "EXTEND", "REVOKE"],
    grant: AssessorClassGrant | None = None,
    class_id: UUID | None = None,
    assessor_id: UUID | None = None,
    expected_version: int,
    end: datetime | None = None,
    start: datetime | None = None,
    reason: str | None = None,
) -> None:
    ok = (
        prior.action == action
        and prior.expected_version == expected_version
        and (grant is None or prior.grant_id == grant.id)
        and (class_id is None or prior.class_offering_id == class_id)
        and (assessor_id is None or prior.assessor_person_id == assessor_id)
        and (end is None or prior.ends_at == end)
        and (start is None or prior.starts_at == start)
        and prior.reason == reason
    )
    if not ok:
        raise AppError(
            "ASSESSOR_GRANT_IDEMPOTENCY_CONFLICT",
            "Idempotency key reused with different command.",
            status_code=409,
        )


def _revision(
    grant: AssessorClassGrant, *,
    action: Literal["CREATE", "EXTEND", "REVOKE"],
    actor: ActorContext, expected_version: int, key: str,
    reason: str | None, now: datetime,
) -> AssessorClassGrantRevision:
    return AssessorClassGrantRevision(
        id=uuid4(), grant_id=grant.id,
        organization_context_id=actor.organization_context_id,
        class_offering_id=grant.class_offering_id,
        assessor_person_id=grant.assessor_person_id,
        actor_id=actor.person_id, action=action, reason=reason,
        expected_version=expected_version, resulting_version=grant.version,
        starts_at=grant.starts_at, ends_at=grant.ends_at,
        revoked_at=grant.revoked_at, idempotency_key=key,
        occurred_at=now,
    )


async def _save_command(
    db: AsyncSession, *,
    grant: AssessorClassGrant, actor: ActorContext,
    action: Literal["CREATE", "EXTEND", "REVOKE"],
    expected_version: int, key: str, reason: str | None, now: datetime,
) -> None:
    db.add(_revision(
        grant, action=action, actor=actor, expected_version=expected_version,
        key=key, reason=reason, now=now,
    ))
    record_event(
        db,
        new_event(
            event_type={
                "CREATE": "academy.assessor_grant_created.v1",
                "EXTEND": "academy.assessor_grant_extended.v1",
                "REVOKE": "academy.assessor_grant_revoked.v1",
            }[action],
            aggregate_type="AssessorClassGrant",
            aggregate_id=grant.id,
            aggregate_version=grant.version,
            actor={"type": "PERSON", "id": str(actor.person_id)},
            organization_context_id=actor.organization_context_id,
            data_classification="INTERNAL",
            payload={
                "class_offering_id": str(grant.class_offering_id),
                "assessor_person_id": str(grant.assessor_person_id),
                "action": action,
                "effective_start": grant.starts_at.isoformat(),
                "effective_end": grant.ends_at.isoformat(),
                "revoked_at": grant.revoked_at.isoformat()
                if grant.revoked_at else None,
            },
            trace_id=actor.trace_id,
        ),
    )
    await db.commit()


@router.post(
    "/classes/{class_offering_id}/assessor-grants",
    response_model=GrantResponse,
)
async def create_assessor_class_grant(
    class_offering_id: UUID,
    body: GrantCreateRequest,
    actor: Annotated[ActorContext, Depends(require_role("ACADEMY_ADMIN"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> GrantResponse:
    offering, cohort = await _class_in_tenant(
        db, class_offering_id=class_offering_id,
        organization_id=actor.organization_context_id,
    )
    _require_operational_class(offering, cohort)
    if not await has_organization_role(
        db, person_id=body.assessor_person_id,
        organization_id=actor.organization_context_id, role="ASSESSOR",
    ):
        raise AppError("ASSESSOR_NOT_FOUND", "Assessor not found.", status_code=404)
    previous = await _prior_command(db, actor=actor, key=body.idempotency_key)
    if previous is not None:
        _assert_replay(
            previous, action="CREATE", class_id=class_offering_id,
            assessor_id=body.assessor_person_id, expected_version=0,
            start=body.starts_at, end=body.ends_at,
        )
        return _response_from_revision(previous)

    existing = (
        await db.execute(
            select(AssessorClassGrant.id).where(
                AssessorClassGrant.class_offering_id == class_offering_id,
                AssessorClassGrant.assessor_person_id == body.assessor_person_id,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        # Reappointment after revocation/expiry needs explicit lifecycle policy.
        raise AppError("ASSESSOR_GRANT_EXISTS", "Grant already exists.", status_code=409)
    now = current_utc()
    if body.ends_at <= now:
        raise AppError("GRANT_WINDOW_ENDED", "Grant must end in the future.", status_code=409)
    row = AssessorClassGrant(
        id=uuid4(), version=1, organization_context_id=actor.organization_context_id,
        class_offering_id=class_offering_id,
        assessor_person_id=body.assessor_person_id,
        starts_at=body.starts_at, ends_at=body.ends_at, revoked_at=None,
        created_by=actor.person_id, updated_by=actor.person_id,
        created_at=now, updated_at=now,
    )
    db.add(row)
    await _save_command(
        db, grant=row, actor=actor, action="CREATE", expected_version=0,
        key=body.idempotency_key, reason=None, now=now,
    )
    return _response(row)


async def _locked_grant(
    db: AsyncSession, *, grant_id: UUID, actor: ActorContext
) -> AssessorClassGrant:
    row = (
        await db.execute(
            select(AssessorClassGrant)
            .where(
                AssessorClassGrant.id == grant_id,
                AssessorClassGrant.organization_context_id
                == actor.organization_context_id,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if row is None:
        raise AppError("GRANT_NOT_FOUND", "Grant not found.", status_code=404)
    return row


@router.post("/assessor-grants/{grant_id}/extend", response_model=GrantResponse)
async def extend_assessor_class_grant(
    grant_id: UUID,
    body: GrantExtendRequest,
    actor: Annotated[ActorContext, Depends(require_role("ACADEMY_ADMIN"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> GrantResponse:
    row = await _locked_grant(db, grant_id=grant_id, actor=actor)
    old = await _prior_command(db, actor=actor, key=body.idempotency_key)
    if old is not None:
        _assert_replay(
            old, action="EXTEND", grant=row,
            expected_version=body.expected_version, end=body.ends_at,
            start=row.starts_at, reason=body.reason,
        )
        return _response_from_revision(old)
    if body.expected_version != row.version:
        raise AppError("GRANT_VERSION_CONFLICT", "Refresh grant version.", status_code=409)
    now = current_utc()
    if row.revoked_at is not None or row.ends_at <= now:
        raise AppError("GRANT_ENDED", "Ended grant cannot be revived.", status_code=409)
    if body.ends_at <= row.ends_at:
        raise AppError("NOT_AN_EXTENSION", "New end must be later.", status_code=409)
    offering, cohort = await _class_in_tenant(
        db, class_offering_id=row.class_offering_id,
        organization_id=actor.organization_context_id,
    )
    _require_operational_class(offering, cohort)
    row.ends_at = body.ends_at
    row.version += 1
    row.updated_by = actor.person_id
    row.updated_at = now
    await _save_command(
        db, grant=row, actor=actor, action="EXTEND",
        expected_version=body.expected_version,
        key=body.idempotency_key, reason=body.reason, now=now,
    )
    return _response(row)


@router.post("/assessor-grants/{grant_id}/revoke", response_model=GrantResponse)
async def revoke_assessor_class_grant(
    grant_id: UUID,
    body: GrantRevokeRequest,
    actor: Annotated[ActorContext, Depends(require_role("ACADEMY_ADMIN"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> GrantResponse:
    row = await _locked_grant(db, grant_id=grant_id, actor=actor)
    old = await _prior_command(db, actor=actor, key=body.idempotency_key)
    if old is not None:
        _assert_replay(
            old, action="REVOKE", grant=row,
            expected_version=body.expected_version,
            start=row.starts_at, end=row.ends_at, reason=body.reason,
        )
        return _response_from_revision(old)
    if body.expected_version != row.version:
        raise AppError("GRANT_VERSION_CONFLICT", "Refresh grant version.", status_code=409)
    now = current_utc()
    if row.revoked_at is not None:
        raise AppError("GRANT_ALREADY_REVOKED", "Grant was revoked.", status_code=409)
    row.revoked_at = now
    row.version += 1
    row.updated_by = actor.person_id
    row.updated_at = now
    await _save_command(
        db, grant=row, actor=actor, action="REVOKE",
        expected_version=body.expected_version,
        key=body.idempotency_key, reason=body.reason, now=now,
    )
    return _response(row)
