"""P23-09C: factual, immutable Assessor classroom observation capture.

This is an Academy operational observation, NOT an EvidenceCase. There is no
automatic Evidence ingestion, CapabilityClaim/Gate mutation or AI-learning path.
Historic entry is permitted only while the writer's *current* class grant remains
valid and the original observation falls inside the grant and real Session window.
"""

from datetime import UTC, datetime
from hashlib import sha256
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.academy.assessor_grants_policy import GrantWindow, active_class_grant, current_utc
from app.academy.models import (
    AssessorClassGrant,
    ClassAssessorObservation,
    ClassOffering,
    Cohort,
    CohortMembership,
    Session,
)
from app.academy.assessor_access import has_live_assessor_class_access
from app.db import get_session
from app.errors import AppError
from app.identity.auth import ActorContext, require_role
from app.identity.public_reader import has_organization_role
from app.platform.events import new_event, record_event

router = APIRouter(prefix="/api/v1", tags=["academy"])


class ClassObservationCreate(BaseModel):
    session_id: UUID
    candidate_person_id: UUID
    observed_at: datetime
    observed_fact: str = Field(min_length=1, max_length=4000)
    idempotency_key: str = Field(min_length=1, max_length=160)

    @field_validator("observed_at")
    @classmethod
    def valid_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Explicit timezone is required")
        return value.astimezone(UTC)

    @field_validator("observed_fact", "idempotency_key")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Value must not be blank")
        return value.strip()


class ClassObservationRead(BaseModel):
    observation_id: UUID
    organization_context_id: UUID
    class_offering_id: UUID
    session_id: UUID
    candidate_person_id: UUID
    observer_person_id: UUID
    grant_id: UUID
    grant_version: int
    observed_at: datetime
    recorded_at: datetime
    observed_fact: str
    # No 'accepted Evidence' state exists on this Academy record.


def _response(item: ClassAssessorObservation) -> ClassObservationRead:
    return ClassObservationRead(
        observation_id=item.id,
        organization_context_id=item.organization_context_id,
        class_offering_id=item.class_offering_id,
        session_id=item.session_id,
        candidate_person_id=item.candidate_person_id,
        observer_person_id=item.observer_person_id,
        grant_id=item.grant_id,
        grant_version=item.grant_version,
        observed_at=item.observed_at,
        recorded_at=item.recorded_at,
        observed_fact=item.observed_fact,
    )


def _not_found() -> None:
    raise AppError("CLASS_OBSERVATION_SCOPE_NOT_FOUND", "Class context not found.", status_code=404)


def _replay_matches(
    old: ClassAssessorObservation,
    *,
    class_id: UUID,
    body: ClassObservationCreate,
) -> bool:
    return (
        old.class_offering_id == class_id
        and old.session_id == body.session_id
        and old.candidate_person_id == body.candidate_person_id
        and old.observed_at == body.observed_at
        and old.observed_fact == body.observed_fact
    )


@router.post(
    "/class-offerings/{class_offering_id}/observations",
    response_model=ClassObservationRead,
    status_code=201,
)
async def create_class_observation(
    class_offering_id: UUID,
    body: ClassObservationCreate,
    actor: Annotated[ActorContext, Depends(require_role("ASSESSOR"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> ClassObservationRead:
    if "ASSESSOR" not in actor.roles:
        _not_found()

    # Serialize same actor + tenant + idempotency key even across different classes.
    # Signed 64-bit transaction advisory lock; also DB unique key is authoritative.
    identity = (
        f"{actor.organization_context_id}:{actor.person_id}:{body.idempotency_key}"
    ).encode()
    lock_key = int.from_bytes(sha256(identity).digest()[:8], "big", signed=True)
    await db.execute(select(func.pg_advisory_xact_lock(lock_key)))

    # Lock the current mandate before dereferencing any private class facts.
    grant = (
        await db.execute(
            select(AssessorClassGrant)
            .where(
                AssessorClassGrant.organization_context_id == actor.organization_context_id,
                AssessorClassGrant.assessor_person_id == actor.person_id,
                AssessorClassGrant.class_offering_id == class_offering_id,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if grant is None:
        _not_found()
    context = (
        await db.execute(
            select(ClassOffering, Cohort)
            .join(Cohort, ClassOffering.cohort_id == Cohort.id)
            .where(
                ClassOffering.id == class_offering_id,
                Cohort.organization_context_id == actor.organization_context_id,
            )
            .with_for_update(of=ClassOffering)
        )
    ).first()
    if context is None:
        _not_found()
    offering, cohort = context
    now = current_utc()
    if not active_class_grant(
        GrantWindow(grant.starts_at, grant.ends_at, grant.revoked_at),
        now=now, class_status=offering.status, cohort_status=cohort.status,
    ):
        _not_found()
    if not await has_organization_role(
        db, person_id=actor.person_id,
        organization_id=actor.organization_context_id, role="ASSESSOR",
    ):
        _not_found()

    prior = (
        await db.execute(
            select(ClassAssessorObservation).where(
                ClassAssessorObservation.organization_context_id
                == actor.organization_context_id,
                ClassAssessorObservation.observer_person_id == actor.person_id,
                ClassAssessorObservation.idempotency_key == body.idempotency_key,
            )
        )
    ).scalar_one_or_none()
    if prior is not None:
        if not _replay_matches(prior, class_id=class_offering_id, body=body):
            raise AppError(
                "CLASS_OBSERVATION_IDEMPOTENCY_CONFLICT",
                "Idempotency key was already used with different input.",
                status_code=409,
            )
        return _response(prior)

    session = (
        await db.execute(
            select(Session).where(
                Session.id == body.session_id,
                Session.class_offering_id == class_offering_id,
            )
        )
    ).scalar_one_or_none()
    candidate = (
        await db.execute(
            select(CohortMembership.id).where(
                CohortMembership.cohort_id == cohort.id,
                CohortMembership.person_id == body.candidate_person_id,
                CohortMembership.member_type == "CANDIDATE",
            )
        )
    ).scalar_one_or_none()
    if session is None or candidate is None:
        _not_found()

    if not (
        body.observed_at <= now
        and grant.starts_at <= body.observed_at < grant.ends_at
        and session.starts_at <= body.observed_at < session.ends_at
    ):
        raise AppError(
            "CLASS_OBSERVATION_TIME_CONFLICT",
            "Observed time must be within the real authorized session and mandate.",
            status_code=409,
        )

    item = ClassAssessorObservation(
        id=uuid4(),
        organization_context_id=actor.organization_context_id,
        class_offering_id=class_offering_id,
        session_id=body.session_id,
        candidate_person_id=body.candidate_person_id,
        observer_person_id=actor.person_id,
        grant_id=grant.id,
        grant_version=grant.version,
        observed_at=body.observed_at,
        recorded_at=now,
        observed_fact=body.observed_fact,
        idempotency_key=body.idempotency_key,
    )
    db.add(item)
    record_event(
        db,
        new_event(
            event_type="academy.class_observation_recorded.v1",
            aggregate_type="ClassAssessorObservation",
            aggregate_id=item.id,
            aggregate_version=1,
            actor={"type": "PERSON", "id": str(actor.person_id)},
            organization_context_id=actor.organization_context_id,
            data_classification="INTERNAL",
            trace_id=actor.trace_id,
            payload={
                "class_offering_id": str(class_offering_id),
                "session_id": str(body.session_id),
                "candidate_person_id": str(body.candidate_person_id),
                "grant_id": str(grant.id),
                "grant_version": grant.version,
                "observed_at": body.observed_at.isoformat(),
                "recorded_at": now.isoformat(),
                "evidence_accepted": False,
            },
        ),
    )
    await db.commit()
    return _response(item)


@router.get(
    "/class-offerings/{class_offering_id}/observations",
    response_model=list[ClassObservationRead],
)
async def list_my_class_observations(
    class_offering_id: UUID,
    actor: Annotated[ActorContext, Depends(require_role("ASSESSOR"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[ClassObservationRead]:
    # No historical or global Assessor read access after grant expiry/revocation.
    if not await has_live_assessor_class_access(
        db, actor=actor, class_offering_id=class_offering_id,
    ):
        _not_found()
    rows = (
        await db.execute(
            select(ClassAssessorObservation)
            .where(
                ClassAssessorObservation.organization_context_id
                == actor.organization_context_id,
                ClassAssessorObservation.class_offering_id == class_offering_id,
                ClassAssessorObservation.observer_person_id == actor.person_id,
            )
            .order_by(
                ClassAssessorObservation.recorded_at.desc(),
                ClassAssessorObservation.id.desc(),
            )
            .limit(limit)
        )
    ).scalars().all()
    return [_response(item) for item in rows]
