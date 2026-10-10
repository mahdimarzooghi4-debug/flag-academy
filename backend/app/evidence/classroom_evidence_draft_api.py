"""Evidence-owned, exact-source, human-requested private classroom Draft admission.

This is deliberately NOT formal Evidence submission/acceptance or AI training.
Generic organization-wide Evidence routes always deny this source context.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Never
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.errors import AppError
from app.evidence.api import CLASSROOM_SOURCE_CONTEXT
from app.evidence.classroom_source_review_api import (
    _source_and_mandate,
    classroom_source_digest,
)
from app.evidence.domain import EvidenceCaseStatus
from app.evidence.models import ClassroomObservationSourceReview, EvidenceCase
from app.identity.auth import ActorContext, require_role
from app.platform.events import new_event, record_event

router = APIRouter(prefix="/api/v1", tags=["evidence"])


class ClassroomDraftCommand(BaseModel):
    expected_review_id: UUID
    expected_source_sha256: str = Field(pattern="^[0-9a-f]{64}$")
    submission_reason: str = Field(min_length=1, max_length=8000)


class ClassroomDraftResponse(BaseModel):
    evidence_case_id: UUID
    version: int
    source_observation_id: UUID
    source_review_id: UUID
    source_sha256: str
    class_offering_id: UUID
    session_id: UUID
    subject_person_id: UUID
    observed_at: datetime
    observed_fact: str
    status: str
    candidate_visible: bool
    created_at: datetime


def _not_found() -> Never:
    raise AppError(
        "CLASSROOM_EVIDENCE_DRAFT_NOT_FOUND",
        "Classroom source or authorized Draft not found.",
        status_code=404,
    )


async def _verified_review(
    db: AsyncSession,
    *,
    actor: ActorContext,
    source,
    grant,
) -> ClassroomObservationSourceReview:
    review = (
        await db.execute(
            select(ClassroomObservationSourceReview).where(
                ClassroomObservationSourceReview.organization_context_id
                == actor.organization_context_id,
                ClassroomObservationSourceReview.source_observation_id == source.id,
            )
        )
    ).scalar_one_or_none()
    if (
        review is None
        or review.decision != "VERIFIED"
        or review.reviewer_person_id != actor.person_id
        or review.observer_person_id != source.observer_person_id
        or review.subject_person_id != source.candidate_person_id
        or review.class_offering_id != source.class_offering_id
        or review.session_id != source.session_id
        or review.source_sha256 != classroom_source_digest(source)
        or review.reviewer_grant_id != grant.id
        or review.reviewer_grant_version > grant.version
    ):
        _not_found()
    return review


def _lineage_matches(case: EvidenceCase, source, review, actor: ActorContext) -> bool:
    provenance = case.provenance
    return (
        case.organization_context_id == actor.organization_context_id
        and case.source_context == CLASSROOM_SOURCE_CONTEXT
        and case.source_observation_id == source.id
        and case.subject_person_id == source.candidate_person_id
        and case.observed_fact == source.observed_fact
        and case.occurred_at == source.observed_at
        and case.integrity_state == "SOURCE_REVIEWED"
        and case.status == EvidenceCaseStatus.DRAFT.value
        and case.candidate_visible is False
        and isinstance(provenance, dict)
        and provenance.get("source_review_id") == str(review.id)
        and provenance.get("source_sha256") == review.source_sha256
        and provenance.get("created_by_person_id") == str(actor.person_id)
        and provenance.get("class_offering_id") == str(source.class_offering_id)
        and provenance.get("session_id") == str(source.session_id)
        and provenance.get("source_grant_id") == str(source.grant_id)
        and provenance.get("source_grant_version") == source.grant_version
        and provenance.get("reviewer_grant_id") == str(review.reviewer_grant_id)
        and provenance.get("reviewer_grant_version") == review.reviewer_grant_version
    )


def _response(case: EvidenceCase, source, review) -> ClassroomDraftResponse:
    return ClassroomDraftResponse(
        evidence_case_id=case.id,
        version=case.version,
        source_observation_id=source.id,
        source_review_id=review.id,
        source_sha256=review.source_sha256,
        class_offering_id=source.class_offering_id,
        session_id=source.session_id,
        subject_person_id=source.candidate_person_id,
        observed_at=source.observed_at,
        observed_fact=case.observed_fact,
        status=case.status,
        candidate_visible=case.candidate_visible,
        created_at=case.created_at,
    )


@router.post(
    "/classroom-observations/{observation_id}/evidence-draft",
    response_model=ClassroomDraftResponse,
    status_code=201,
)
async def create_classroom_evidence_draft(
    observation_id: UUID,
    body: ClassroomDraftCommand,
    actor: Annotated[ActorContext, Depends(require_role("ASSESSOR"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> ClassroomDraftResponse:
    # Source row first, then reviewer mandate lock. Concurrent POSTs serialize
    # and Admin revocation cannot race a successful authorization.
    source, grant = await _source_and_mandate(
        db, actor=actor, observation_id=observation_id,
    )
    review = await _verified_review(db, actor=actor, source=source, grant=grant)
    digest = classroom_source_digest(source)
    if body.expected_review_id != review.id or body.expected_source_sha256 != digest:
        raise AppError(
            "CLASSROOM_DRAFT_STALE_REVIEW",
            "Refresh the approved classroom source and human review.",
            status_code=409,
        )
    reason = body.submission_reason.strip()
    if not reason:
        raise AppError("CLASSROOM_DRAFT_REASON_REQUIRED", "Reason is required.", status_code=422)

    existing = (
        await db.execute(
            select(EvidenceCase).where(EvidenceCase.source_observation_id == source.id)
        )
    ).scalar_one_or_none()
    if existing is not None:
        if not _lineage_matches(existing, source, review, actor) or (
            existing.provenance.get("submission_reason") != reason
        ):
            raise AppError(
                "CLASSROOM_DRAFT_CONFLICT",
                "The original source already belongs to a different Evidence case or command.",
                status_code=409,
            )
        return _response(existing, source, review)

    now = datetime.now(UTC)
    case = EvidenceCase(
        id=uuid4(),
        version=1,
        organization_context_id=actor.organization_context_id,
        subject_person_id=source.candidate_person_id,
        source_observation_id=source.id,
        source_context=CLASSROOM_SOURCE_CONTEXT,
        source_reference=f"academy.class_assessor_observations:{source.id}",
        source_runtime_event_id=None,
        observation_type=CLASSROOM_SOURCE_CONTEXT,
        observed_fact=source.observed_fact,
        observed_payload={
            "class_offering_id": str(source.class_offering_id),
            "session_id": str(source.session_id),
        },
        candidate_visible=False,
        candidate_visible_payload={},
        occurred_at=source.observed_at,
        # Correlate sources from the same class; do NOT claim independent proof.
        source_independence_group=f"ACADEMY_CLASS:{source.class_offering_id}",
        provenance={
            "source_review_id": str(review.id),
            "source_sha256": digest,
            "source_grant_id": str(source.grant_id),
            "source_grant_version": source.grant_version,
            "reviewer_grant_id": str(review.reviewer_grant_id),
            "reviewer_grant_version": review.reviewer_grant_version,
            "class_offering_id": str(source.class_offering_id),
            "session_id": str(source.session_id),
            "created_by_person_id": str(actor.person_id),
            "submission_reason": reason,
        },
        integrity_state="SOURCE_REVIEWED",
        status=EvidenceCaseStatus.DRAFT.value,
        context_request=None,
        created_at=now,
        updated_at=now,
        accepted_at=None,
        rejected_at=None,
    )
    db.add(case)
    record_event(
        db,
        new_event(
            event_type="evidence.classroom_draft_created.v1",
            aggregate_type="EvidenceCase",
            aggregate_id=case.id,
            aggregate_version=1,
            actor={"type": "PERSON", "id": str(actor.person_id)},
            organization_context_id=actor.organization_context_id,
            data_classification="CONFIDENTIAL",
            trace_id=actor.trace_id,
            payload={
                "evidence_case_id": str(case.id),
                "source_observation_id": str(source.id),
                "source_review_id": str(review.id),
                "source_sha256": digest,
                "class_offering_id": str(source.class_offering_id),
                "status": "DRAFT",
                "candidate_visible": False,
                "formal_evidence_accepted": False,
            },
        ),
    )
    await db.commit()
    return _response(case, source, review)


@router.get(
    "/classroom-evidence-drafts/{case_id}",
    response_model=ClassroomDraftResponse,
)
async def get_classroom_evidence_draft(
    case_id: UUID,
    actor: Annotated[ActorContext, Depends(require_role("ASSESSOR"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> ClassroomDraftResponse:
    # A guessed case ID or organization-wide Evidence role never authorizes a read.
    case = (
        await db.execute(
            select(EvidenceCase).where(
                EvidenceCase.id == case_id,
                EvidenceCase.organization_context_id == actor.organization_context_id,
                EvidenceCase.source_context == CLASSROOM_SOURCE_CONTEXT,
            )
        )
    ).scalar_one_or_none()
    if (
        case is None
        or not isinstance(case.provenance, dict)
        or case.provenance.get("created_by_person_id") != str(actor.person_id)
    ):
        _not_found()
    source, grant = await _source_and_mandate(
        db, actor=actor, observation_id=case.source_observation_id,
    )
    review = await _verified_review(db, actor=actor, source=source, grant=grant)
    if not _lineage_matches(case, source, review, actor):
        _not_found()
    return _response(case, source, review)
