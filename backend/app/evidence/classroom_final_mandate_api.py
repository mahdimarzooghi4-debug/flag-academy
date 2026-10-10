"""Human Academy Admin issuance and revocation of case-scoped final Evidence mandates.

No ASSESSOR role/ordinary Academy grant alone conveys final Evidence authority.
Commands are case-locked, tenant-bound, idempotent, append-only audited.
"""
from datetime import UTC, datetime
from typing import Annotated, Never
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.academy.assessor_grants_policy import GrantWindow, active_class_grant, current_utc
from app.academy.models import (
    AssessorClassGrant,
    ClassAssessorObservation,
    ClassOffering,
    Cohort,
)
from app.db import get_session
from app.errors import AppError
from app.evidence.api import (
    CLASSROOM_SOURCE_CONTEXT,
    _active_interpretation,
    _require_expected_version,
)
from app.evidence.classroom_review_safety import classroom_review_lineage_independent
from app.evidence.classroom_source_review_api import classroom_source_digest
from app.evidence.models import (
    ClassroomFinalEvidenceMandateRevision,
    ClassroomFinalEvidenceReviewMandate,
    ClassroomObservationSourceReview,
    EvidenceCase,
)
from app.identity.auth import ActorContext, require_role
from app.identity.public_reader import has_organization_role
from app.platform.events import new_event, record_event

router = APIRouter(prefix="/api/v1/admin/academy", tags=["evidence"])


def _deny() -> Never:
    raise AppError("FINAL_EVIDENCE_MANDATE_NOT_FOUND", "Authorized mandate or case not found.", status_code=404)


class IssueFinalMandate(BaseModel):
    reviewer_person_id: UUID
    expected_case_version: int = Field(ge=1)
    expected_source_sha256: str = Field(pattern="^[0-9a-f]{64}$")
    starts_at: datetime
    ends_at: datetime
    reason: str = Field(min_length=1, max_length=8000)
    idempotency_key: str = Field(min_length=1, max_length=160)

    @field_validator("starts_at", "ends_at")
    @classmethod
    def aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Timezone-aware timestamp required")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def window(self) -> "IssueFinalMandate":
        if self.ends_at <= self.starts_at:
            raise ValueError("End must be after start")
        if not self.reason.strip() or not self.idempotency_key.strip():
            raise ValueError("Nonblank reason and idempotency key are required")
        return self


class RevokeFinalMandate(BaseModel):
    expected_version: int = Field(ge=1)
    reason: str = Field(min_length=1, max_length=8000)
    idempotency_key: str = Field(min_length=1, max_length=160)

    @model_validator(mode="after")
    def nonblank(self) -> "RevokeFinalMandate":
        if not self.reason.strip() or not self.idempotency_key.strip():
            raise ValueError("Nonblank reason and idempotency key are required")
        return self


class FinalMandateResponse(BaseModel):
    mandate_id: UUID
    evidence_case_id: UUID
    reviewer_person_id: UUID
    version: int
    starts_at: datetime
    ends_at: datetime
    revoked_at: datetime | None


def _response(row: ClassroomFinalEvidenceReviewMandate) -> FinalMandateResponse:
    return FinalMandateResponse(
        mandate_id=row.id, evidence_case_id=row.evidence_case_id,
        reviewer_person_id=row.reviewer_person_id, version=row.version,
        starts_at=row.starts_at, ends_at=row.ends_at, revoked_at=row.revoked_at,
    )


async def _case_source(db: AsyncSession, *, case_id: UUID, organization_id: UUID
                       ) -> tuple[ClassAssessorObservation, EvidenceCase]:
    # Source is locked before case, identical ordering to source verification.
    source_id = (await db.execute(select(EvidenceCase.source_observation_id).where(
        EvidenceCase.id == case_id, EvidenceCase.organization_context_id == organization_id,
        EvidenceCase.source_context == CLASSROOM_SOURCE_CONTEXT,
    ))).scalar_one_or_none()
    if source_id is None:
        _deny()
    source = (await db.execute(select(ClassAssessorObservation).where(
        ClassAssessorObservation.id == source_id,
        ClassAssessorObservation.organization_context_id == organization_id,
    ).with_for_update())).scalar_one_or_none()
    if source is None:
        _deny()
    case = (await db.execute(select(EvidenceCase).where(
        EvidenceCase.id == case_id, EvidenceCase.organization_context_id == organization_id,
        EvidenceCase.source_observation_id == source.id,
        EvidenceCase.source_context == CLASSROOM_SOURCE_CONTEXT,
    ).with_for_update())).scalar_one_or_none()
    if case is None:
        _deny()
    return source, case


async def _review_attestation(db: AsyncSession, *, source: ClassAssessorObservation,
                              case: EvidenceCase) -> ClassroomObservationSourceReview:
    review = (await db.execute(select(ClassroomObservationSourceReview).where(
        ClassroomObservationSourceReview.organization_context_id == case.organization_context_id,
        ClassroomObservationSourceReview.source_observation_id == source.id,
    ))).scalar_one_or_none()
    if review is None or review.decision != "VERIFIED":
        _deny()
    return review


async def _reviewer_class_grant(db: AsyncSession, *, organization_id: UUID,
                               source: ClassAssessorObservation, reviewer_id: UUID
                               ) -> tuple[AssessorClassGrant, ClassOffering, Cohort]:
    row = (await db.execute(
        select(AssessorClassGrant, ClassOffering, Cohort)
        .join(ClassOffering, ClassOffering.id == AssessorClassGrant.class_offering_id)
        .join(Cohort, Cohort.id == ClassOffering.cohort_id)
        .where(
            AssessorClassGrant.organization_context_id == organization_id,
            AssessorClassGrant.class_offering_id == source.class_offering_id,
            AssessorClassGrant.assessor_person_id == reviewer_id,
            Cohort.organization_context_id == organization_id,
        )
        .with_for_update(of=(AssessorClassGrant, ClassOffering))
    )).first()
    if row is None:
        _deny()
    grant, offering, cohort = row
    if not active_class_grant(
        GrantWindow(grant.starts_at, grant.ends_at, grant.revoked_at),
        now=current_utc(), class_status=offering.status, cohort_status=cohort.status,
    ):
        _deny()
    if not await has_organization_role(
        db, person_id=reviewer_id, organization_id=organization_id, role="ASSESSOR",
    ):
        _deny()
    return grant, offering, cohort


async def _revision_by_key(db: AsyncSession, *, actor: ActorContext, key: str
                           ) -> ClassroomFinalEvidenceMandateRevision | None:
    return (await db.execute(select(ClassroomFinalEvidenceMandateRevision).where(
        ClassroomFinalEvidenceMandateRevision.organization_context_id
        == actor.organization_context_id,
        ClassroomFinalEvidenceMandateRevision.actor_person_id == actor.person_id,
        ClassroomFinalEvidenceMandateRevision.idempotency_key == key,
    ))).scalar_one_or_none()


def _assert_replay(old: ClassroomFinalEvidenceMandateRevision, *,
                   action: str, case_id: UUID, reviewer_id: UUID | None,
                   expected_version: int, reason: str,
                   starts_at: datetime | None = None,
                   ends_at: datetime | None = None) -> None:
    if (old.action != action or old.evidence_case_id != case_id
        or (reviewer_id is not None and old.reviewer_person_id != reviewer_id)
        or old.expected_version != expected_version or old.reason != reason.strip()
        or (starts_at is not None and old.starts_at != starts_at)
        or (ends_at is not None and old.ends_at != ends_at)):
        raise AppError("FINAL_MANDATE_IDEMPOTENCY_CONFLICT", "Changed idempotent command.", status_code=409)


def _old_response(row: ClassroomFinalEvidenceMandateRevision) -> FinalMandateResponse:
    return FinalMandateResponse(
        mandate_id=row.mandate_id, evidence_case_id=row.evidence_case_id,
        reviewer_person_id=row.reviewer_person_id, version=row.resulting_version,
        starts_at=row.starts_at, ends_at=row.ends_at, revoked_at=row.revoked_at,
    )


def _write_revision(db: AsyncSession, *, row: ClassroomFinalEvidenceReviewMandate,
                    actor: ActorContext, action: str, expected_version: int,
                    key: str, reason: str, now: datetime) -> None:
    db.add(ClassroomFinalEvidenceMandateRevision(
        id=uuid4(), mandate_id=row.id, organization_context_id=actor.organization_context_id,
        evidence_case_id=row.evidence_case_id, actor_person_id=actor.person_id,
        reviewer_person_id=row.reviewer_person_id, action=action,
        expected_version=expected_version, resulting_version=row.version,
        starts_at=row.starts_at, ends_at=row.ends_at, revoked_at=row.revoked_at,
        reason=reason.strip(), idempotency_key=key.strip(), occurred_at=now,
    ))
    record_event(db, new_event(
        event_type=("evidence.final_reviewer_mandate_issued.v1"
                    if action == "ISSUE" else "evidence.final_reviewer_mandate_revoked.v1"),
        aggregate_type="ClassroomFinalEvidenceReviewMandate", aggregate_id=row.id,
        aggregate_version=row.version, organization_context_id=actor.organization_context_id,
        actor={"type": "PERSON", "id": str(actor.person_id)},
        data_classification="CONFIDENTIAL", trace_id=actor.trace_id,
        payload={"evidence_case_id": str(row.evidence_case_id),
                 "reviewer_person_id": str(row.reviewer_person_id),
                 "action": action, "mandate_version": row.version},
    ))


@router.post("/classroom-evidence-cases/{case_id}/final-review-mandate",
             response_model=FinalMandateResponse, status_code=201)
async def issue_final_review_mandate(
    case_id: UUID, body: IssueFinalMandate,
    actor: Annotated[ActorContext, Depends(require_role("ACADEMY_ADMIN"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> FinalMandateResponse:
    source, case = await _case_source(db, case_id=case_id,
                                      organization_id=actor.organization_context_id)
    old = await _revision_by_key(db, actor=actor, key=body.idempotency_key.strip())
    if old is not None:
        _assert_replay(old, action="ISSUE", case_id=case.id,
                       reviewer_id=body.reviewer_person_id, expected_version=body.expected_case_version,
                       reason=body.reason, starts_at=body.starts_at, ends_at=body.ends_at)
        return _old_response(old)
    _require_expected_version(case, body.expected_case_version)
    if case.status != "SUBMITTED":
        raise AppError("FINAL_MANDATE_CASE_STATE", "Only SUBMITTED classroom cases may be assigned.", status_code=409)
    if actor.person_id == body.reviewer_person_id:
        _deny()
    review = await _review_attestation(db, source=source, case=case)
    interpretation = await _active_interpretation(db, case.id)
    if interpretation is None or not classroom_review_lineage_independent(
        case=case, source=source, source_review=review, interpretation=interpretation,
        final_reviewer_id=body.reviewer_person_id, expected_version=case.version,
        current_source_sha256=classroom_source_digest(source),
    ):
        _deny()
    if body.expected_source_sha256 != classroom_source_digest(source):
        raise AppError("FINAL_MANDATE_SOURCE_CHANGED", "Source digest changed.", status_code=409)
    grant, _, _ = await _reviewer_class_grant(
        db, organization_id=actor.organization_context_id,
        source=source, reviewer_id=body.reviewer_person_id,
    )
    now = current_utc()
    if (body.starts_at < grant.starts_at or body.ends_at > grant.ends_at
        or body.ends_at <= now):
        raise AppError("FINAL_MANDATE_WINDOW_INVALID", "Window outside live class grant.", status_code=409)
    existing = (await db.execute(select(ClassroomFinalEvidenceReviewMandate.id).where(
        ClassroomFinalEvidenceReviewMandate.evidence_case_id == case.id,
    ))).scalar_one_or_none()
    if existing is not None:
        raise AppError("FINAL_MANDATE_EXISTS", "Case already has a final mandate.", status_code=409)
    row = ClassroomFinalEvidenceReviewMandate(
        id=uuid4(), version=1, organization_context_id=actor.organization_context_id,
        evidence_case_id=case.id, class_offering_id=source.class_offering_id,
        reviewer_person_id=body.reviewer_person_id, issued_by_person_id=actor.person_id,
        issued_at=now, starts_at=body.starts_at, ends_at=body.ends_at,
        revoked_at=None,
    )
    db.add(row)
    _write_revision(db, row=row, actor=actor, action="ISSUE",
                    expected_version=body.expected_case_version,
                    key=body.idempotency_key, reason=body.reason, now=now)
    await db.commit()
    return _response(row)


@router.post("/final-review-mandates/{mandate_id}/revoke",
             response_model=FinalMandateResponse)
async def revoke_final_review_mandate(
    mandate_id: UUID, body: RevokeFinalMandate,
    actor: Annotated[ActorContext, Depends(require_role("ACADEMY_ADMIN"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> FinalMandateResponse:
    case_id = (await db.execute(select(ClassroomFinalEvidenceReviewMandate.evidence_case_id).where(
        ClassroomFinalEvidenceReviewMandate.id == mandate_id,
        ClassroomFinalEvidenceReviewMandate.organization_context_id
        == actor.organization_context_id,
    ))).scalar_one_or_none()
    if case_id is None:
        _deny()
    _, case = await _case_source(db, case_id=case_id,
                                 organization_id=actor.organization_context_id)
    row = (await db.execute(select(ClassroomFinalEvidenceReviewMandate).where(
        ClassroomFinalEvidenceReviewMandate.id == mandate_id,
        ClassroomFinalEvidenceReviewMandate.evidence_case_id == case.id,
        ClassroomFinalEvidenceReviewMandate.organization_context_id
        == actor.organization_context_id,
    ).with_for_update())).scalar_one_or_none()
    if row is None:
        _deny()
    old = await _revision_by_key(db, actor=actor, key=body.idempotency_key.strip())
    if old is not None:
        _assert_replay(old, action="REVOKE", case_id=case.id, reviewer_id=None,
                       expected_version=body.expected_version, reason=body.reason)
        if old.mandate_id != row.id:
            raise AppError("FINAL_MANDATE_IDEMPOTENCY_CONFLICT", "Wrong mandate replay.", status_code=409)
        return _old_response(old)
    if row.version != body.expected_version:
        raise AppError("FINAL_MANDATE_VERSION_CONFLICT", "Refresh mandate version.", status_code=409)
    if row.revoked_at is not None:
        raise AppError("FINAL_MANDATE_REVOKED", "Mandate already revoked.", status_code=409)
    now = current_utc()
    row.version += 1
    row.revoked_at = now
    _write_revision(db, row=row, actor=actor, action="REVOKE",
                    expected_version=body.expected_version,
                    key=body.idempotency_key, reason=body.reason, now=now)
    await db.commit()
    return _response(row)
