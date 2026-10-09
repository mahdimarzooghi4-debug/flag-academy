"""Separate, explicit human attestation of an immutable classroom source.

No EvidenceCase, Evidence acceptance, Profile/Gate mutation or AI dataset action.
The reviewer must be a *different* live-appointed Assessor for the same class.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Annotated, Literal, Never
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.academy.assessor_grants_policy import GrantWindow, active_class_grant, current_utc
from app.academy.models import (
    AssessorClassGrant,
    AssessorClassGrantRevision,
    ClassAssessorObservation,
    ClassOffering,
    Cohort,
    Session,
)
from app.db import get_session
from app.errors import AppError
from app.evidence.models import ClassroomObservationSourceReview
from app.identity.auth import ActorContext, require_role
from app.identity.public_reader import has_organization_role
from app.platform.events import new_event, record_event

router = APIRouter(prefix="/api/v1", tags=["evidence"])


class ClassroomReviewCommand(BaseModel):
    expected_source_sha256: str = Field(pattern="^[0-9a-f]{64}$")
    decision: Literal["VERIFIED", "REJECTED"]
    rationale: str = Field(min_length=1, max_length=8000)


class ClassroomReviewSource(BaseModel):
    observation_id: UUID
    class_offering_id: UUID
    session_id: UUID
    candidate_person_id: UUID
    observer_person_id: UUID
    observed_at: datetime
    recorded_at: datetime
    observed_fact: str
    source_sha256: str
    # No accepted Evidence or automatic progression is implied.


class ClassroomReviewResult(BaseModel):
    review_id: UUID
    source_observation_id: UUID
    source_sha256: str
    reviewer_person_id: UUID
    decision: Literal["VERIFIED", "REJECTED"]
    decided_at: datetime
    # No EvidenceCase id: an explicit Evidence-owned ingestion contract is pending.


def _deny() -> Never:
    raise AppError(
        "CLASSROOM_SOURCE_REVIEW_NOT_FOUND",
        "Source or current independent review authorization not found.",
        status_code=404,
    )


def classroom_source_digest(source: ClassAssessorObservation) -> str:
    """Canonical pinned source content, identity, and immutable times."""
    payload = {
        "organization_context_id": str(source.organization_context_id),
        "source_observation_id": str(source.id),
        "class_offering_id": str(source.class_offering_id),
        "session_id": str(source.session_id),
        "candidate_person_id": str(source.candidate_person_id),
        "observer_person_id": str(source.observer_person_id),
        "grant_id": str(source.grant_id),
        "grant_version": source.grant_version,
        "observed_at": source.observed_at.isoformat(),
        "recorded_at": source.recorded_at.isoformat(),
        "observed_fact": source.observed_fact,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def _result(review: ClassroomObservationSourceReview) -> ClassroomReviewResult:
    return ClassroomReviewResult(
        review_id=review.id,
        source_observation_id=review.source_observation_id,
        source_sha256=review.source_sha256,
        reviewer_person_id=review.reviewer_person_id,
        decision=review.decision,
        decided_at=review.decided_at,
    )


async def _source_and_mandate(
    db: AsyncSession,
    *,
    actor: ActorContext,
    observation_id: UUID,
) -> tuple[ClassAssessorObservation, AssessorClassGrant]:
    if "ASSESSOR" not in actor.roles:
        _deny()
    source = (
        await db.execute(
            select(ClassAssessorObservation)
            .where(
                ClassAssessorObservation.id == observation_id,
                ClassAssessorObservation.organization_context_id
                == actor.organization_context_id,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if source is None or source.observer_person_id == actor.person_id:
        _deny()

    # Lock the reviewer mandate before relying on its current live state.
    scoped = (
        await db.execute(
            select(AssessorClassGrant, ClassOffering, Cohort)
            .join(ClassOffering, AssessorClassGrant.class_offering_id == ClassOffering.id)
            .join(Cohort, ClassOffering.cohort_id == Cohort.id)
            .where(
                AssessorClassGrant.organization_context_id == actor.organization_context_id,
                AssessorClassGrant.assessor_person_id == actor.person_id,
                AssessorClassGrant.class_offering_id == source.class_offering_id,
                Cohort.organization_context_id == actor.organization_context_id,
            )
            .with_for_update(of=(AssessorClassGrant, ClassOffering))
        )
    ).first()
    if scoped is None:
        _deny()
    grant, offering, cohort = scoped
    if not active_class_grant(
        GrantWindow(grant.starts_at, grant.ends_at, grant.revoked_at),
        now=current_utc(), class_status=offering.status, cohort_status=cohort.status,
    ):
        _deny()
    if not await has_organization_role(
        db, person_id=actor.person_id,
        organization_id=actor.organization_context_id, role="ASSESSOR",
    ):
        _deny()

    # Re-attest original source authorization from the immutable grant revision,
    # not from the current (possibly extended/revoked) grant window.
    prior = (
        await db.execute(
            select(AssessorClassGrantRevision).where(
                AssessorClassGrantRevision.grant_id == source.grant_id,
                AssessorClassGrantRevision.organization_context_id
                == actor.organization_context_id,
                AssessorClassGrantRevision.class_offering_id == source.class_offering_id,
                AssessorClassGrantRevision.assessor_person_id == source.observer_person_id,
                AssessorClassGrantRevision.resulting_version == source.grant_version,
            )
        )
    ).scalar_one_or_none()
    source_session = (
        await db.execute(
            select(Session).where(
                Session.id == source.session_id,
                Session.class_offering_id == source.class_offering_id,
            )
        )
    ).scalar_one_or_none()
    if (
        prior is None or source_session is None
        or not (prior.starts_at <= source.observed_at < prior.ends_at)
        or not (source_session.starts_at <= source.observed_at < source_session.ends_at)
        or source.recorded_at < source.observed_at
        or source.candidate_person_id == actor.person_id
    ):
        _deny()
    return source, grant


@router.get(
    "/classroom-observations/{observation_id}/review-source",
    response_model=ClassroomReviewSource,
)
async def read_classroom_review_source(
    observation_id: UUID,
    actor: Annotated[ActorContext, Depends(require_role("ASSESSOR"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> ClassroomReviewSource:
    source, _ = await _source_and_mandate(
        db, actor=actor, observation_id=observation_id,
    )
    return ClassroomReviewSource(
        observation_id=source.id,
        class_offering_id=source.class_offering_id,
        session_id=source.session_id,
        candidate_person_id=source.candidate_person_id,
        observer_person_id=source.observer_person_id,
        observed_at=source.observed_at,
        recorded_at=source.recorded_at,
        observed_fact=source.observed_fact,
        source_sha256=classroom_source_digest(source),
    )


@router.post(
    "/classroom-observations/{observation_id}/review-source",
    response_model=ClassroomReviewResult,
    status_code=201,
)
async def review_classroom_source(
    observation_id: UUID,
    body: ClassroomReviewCommand,
    actor: Annotated[ActorContext, Depends(require_role("ASSESSOR"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> ClassroomReviewResult:
    source, grant = await _source_and_mandate(
        db, actor=actor, observation_id=observation_id,
    )
    digest = classroom_source_digest(source)
    if digest != body.expected_source_sha256:
        raise AppError(
            "CLASSROOM_SOURCE_CHANGED",
            "The reviewed source digest does not match; refresh before deciding.",
            status_code=409,
        )
    rationale = body.rationale.strip()
    if not rationale:
        raise AppError(
            "CLASSROOM_REVIEW_REASON_REQUIRED",
            "An independent human review rationale is required.",
            status_code=422,
        )

    existing = (
        await db.execute(
            select(ClassroomObservationSourceReview).where(
                ClassroomObservationSourceReview.organization_context_id
                == actor.organization_context_id,
                ClassroomObservationSourceReview.source_observation_id == source.id,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        if (
            existing.source_sha256 != digest
            or existing.reviewer_person_id != actor.person_id
            or existing.decision != body.decision
            or existing.rationale != rationale
        ):
            raise AppError(
                "CLASSROOM_SOURCE_REVIEW_CONFLICT",
                "Independent review is already recorded with different input.",
                status_code=409,
            )
        return _result(existing)

    now = current_utc()
    review = ClassroomObservationSourceReview(
        id=uuid4(),
        organization_context_id=actor.organization_context_id,
        source_observation_id=source.id,
        class_offering_id=source.class_offering_id,
        session_id=source.session_id,
        subject_person_id=source.candidate_person_id,
        observer_person_id=source.observer_person_id,
        reviewer_person_id=actor.person_id,
        reviewer_grant_id=grant.id,
        reviewer_grant_version=grant.version,
        source_sha256=digest,
        decision=body.decision,
        rationale=rationale,
        decided_at=now,
    )
    db.add(review)
    record_event(
        db,
        new_event(
            event_type="evidence.classroom_source_reviewed.v1",
            aggregate_type="ClassroomObservationSourceReview",
            aggregate_id=review.id,
            aggregate_version=1,
            actor={"type": "PERSON", "id": str(actor.person_id)},
            organization_context_id=actor.organization_context_id,
            data_classification="INTERNAL",
            trace_id=actor.trace_id,
            payload={
                "source_observation_id": str(source.id),
                "source_sha256": digest,
                "class_offering_id": str(source.class_offering_id),
                "reviewer_grant_id": str(grant.id),
                "reviewer_grant_version": grant.version,
                "decision": body.decision,
                "evidence_accepted": False,
                "evidence_case_created": False,
            },
        ),
    )
    await db.commit()
    return _result(review)
