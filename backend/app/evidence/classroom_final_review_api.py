"""Private live-appointee final human review of classroom Evidence only.

No class ASSESSOR role alone authorizes this API. Source/grant/case/mandate
locks serialize review, revocation and stale concurrent decisions.
"""
from datetime import UTC, datetime
from typing import Annotated, Never
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.academy.models import ClassOffering, Cohort
from app.db import get_session
from app.errors import AppError
from app.evidence.api import (
    CLASSROOM_SOURCE_CONTEXT,
    EvidenceCaseResponse,
    EvidenceDecisionRequest,
    EvidenceReviewStartRequest,
    _active_interpretation,
    _full_response,
    _record_case_event,
    _require_expected_version,
)
from app.evidence.classroom_final_mandate_api import _review_attestation
from app.evidence.classroom_final_review_mandate import final_review_mandate_prerequisites
from app.evidence.classroom_source_review_api import (
    _source_and_mandate,
    classroom_source_digest,
)
from app.evidence.domain import EvidenceCaseStatus, case_transition_allowed
from app.evidence.models import (
    ClassroomFinalEvidenceReviewMandate,
    EvidenceCase,
    EvidenceReview,
)
from app.identity.auth import ActorContext, require_role
from app.identity.public_reader import has_organization_role

router = APIRouter(prefix="/api/v1", tags=["evidence"])


def _deny() -> Never:
    raise AppError("CLASSROOM_FINAL_REVIEW_NOT_FOUND",
                   "Authorized final Evidence review not found.", status_code=404)


async def _review_context(
    db: AsyncSession, *, case_id: UUID, actor: ActorContext,
    expected_version: int | None = None,
) -> tuple[EvidenceCase, ClassroomFinalEvidenceReviewMandate]:
    source_id = (await db.execute(select(EvidenceCase.source_observation_id).where(
        EvidenceCase.id == case_id,
        EvidenceCase.organization_context_id == actor.organization_context_id,
        EvidenceCase.source_context == CLASSROOM_SOURCE_CONTEXT,
    ))).scalar_one_or_none()
    if source_id is None:
        _deny()
    # Academy's source helper locks immutable source + current class grant and
    # rechecks original historical grant and current OIDC organization membership.
    source, grant = await _source_and_mandate(
        db, actor=actor, observation_id=source_id,
    )
    case = (await db.execute(select(EvidenceCase).where(
        EvidenceCase.id == case_id,
        EvidenceCase.source_observation_id == source.id,
        EvidenceCase.organization_context_id == actor.organization_context_id,
        EvidenceCase.source_context == CLASSROOM_SOURCE_CONTEXT,
    ).with_for_update())).scalar_one_or_none()
    if case is None:
        _deny()
    if expected_version is not None:
        _require_expected_version(case, expected_version)
    if case.status not in ("SUBMITTED", "UNDER_REVIEW"):
        _deny()
    mandate = (await db.execute(select(ClassroomFinalEvidenceReviewMandate).where(
        ClassroomFinalEvidenceReviewMandate.evidence_case_id == case.id,
        ClassroomFinalEvidenceReviewMandate.organization_context_id
        == actor.organization_context_id,
        ClassroomFinalEvidenceReviewMandate.reviewer_person_id == actor.person_id,
    ).with_for_update())).scalar_one_or_none()
    if mandate is None:
        _deny()
    review = await _review_attestation(db, source=source, case=case)
    interpretation = await _active_interpretation(db, case.id)
    if interpretation is None:
        _deny()
    offering_row = (await db.execute(select(ClassOffering, Cohort)
        .join(Cohort, Cohort.id == ClassOffering.cohort_id)
        .where(ClassOffering.id == source.class_offering_id,
               Cohort.organization_context_id == actor.organization_context_id)
    )).first()
    if offering_row is None:
        _deny()
    offering, cohort = offering_row
    member = await has_organization_role(
        db, person_id=actor.person_id,
        organization_id=actor.organization_context_id, role="ASSESSOR",
    )
    if not final_review_mandate_prerequisites(
        actor=actor, mandate=mandate, case=case, source=source,
        source_review=review, interpretation=interpretation,
        current_class_grant=grant,
        current_org_assessor_membership_confirmed=member,
        class_status=offering.status, cohort_status=cohort.status,
        current_source_sha256=classroom_source_digest(source),
        expected_case_version=case.version,
        expected_case_status=case.status,
        now=datetime.now(UTC),
    ):
        _deny()
    return case, mandate


@router.get("/classroom-evidence-cases/{case_id}/final-review",
            response_model=EvidenceCaseResponse)
async def get_final_review_workspace(
    case_id: UUID,
    actor: Annotated[ActorContext, Depends(require_role("ASSESSOR"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> EvidenceCaseResponse:
    case, _ = await _review_context(db, case_id=case_id, actor=actor)
    return await _full_response(db, case)


@router.post("/classroom-evidence-cases/{case_id}/review-start",
             response_model=EvidenceCaseResponse)
async def start_classroom_final_review(
    case_id: UUID, body: EvidenceReviewStartRequest,
    actor: Annotated[ActorContext, Depends(require_role("ASSESSOR"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> EvidenceCaseResponse:
    case, _ = await _review_context(
        db, case_id=case_id, actor=actor, expected_version=body.expected_version,
    )
    if not case_transition_allowed(case.status, EvidenceCaseStatus.UNDER_REVIEW.value):
        raise AppError("FINAL_REVIEW_INVALID_STATE", "Review cannot start from this state.",
                       status_code=409)
    if not body.rationale.strip():
        raise AppError("FINAL_REVIEW_REASON_REQUIRED", "Human reason is required.", status_code=422)
    history = (await db.execute(select(EvidenceReview.id).where(
        EvidenceReview.evidence_case_id == case.id,
    ))).scalar_one_or_none()
    if history is not None:
        raise AppError("FINAL_REVIEW_ALREADY_STARTED", "Review already started.", status_code=409)
    now = datetime.now(UTC)
    db.add(EvidenceReview(
        id=uuid4(), evidence_case_id=case.id, reviewer_id=actor.person_id,
        decision="REVIEW_STARTED", rationale=body.rationale.strip(), created_at=now,
    ))
    await db.flush()  # DB transition trigger must observe this accountable human row.
    case.status = EvidenceCaseStatus.UNDER_REVIEW.value
    case.version += 1
    case.updated_at = now
    _record_case_event(db, case=case, actor=actor,
                       event_type="evidence.classroom_review_started.v1",
                       payload={"to_status": case.status})
    await db.commit()
    return await _full_response(db, case)


async def _decide(
    *, db: AsyncSession, case_id: UUID, body: EvidenceDecisionRequest,
    actor: ActorContext, target: EvidenceCaseStatus,
) -> EvidenceCaseResponse:
    case, _ = await _review_context(
        db, case_id=case_id, actor=actor, expected_version=body.expected_version,
    )
    if not case_transition_allowed(case.status, target.value):
        raise AppError("FINAL_REVIEW_INVALID_STATE", "Decision cannot be made from this state.",
                       status_code=409)
    if not body.rationale.strip():
        raise AppError("FINAL_REVIEW_REASON_REQUIRED", "Human reason is required.", status_code=422)
    start = (await db.execute(select(EvidenceReview).where(
        EvidenceReview.evidence_case_id == case.id,
        EvidenceReview.decision == "REVIEW_STARTED",
    ))).scalar_one_or_none()
    if start is None or start.reviewer_id != actor.person_id:
        _deny()
    now = datetime.now(UTC)
    accepted = target == EvidenceCaseStatus.ACCEPTED
    db.add(EvidenceReview(
        id=uuid4(), evidence_case_id=case.id, reviewer_id=actor.person_id,
        decision="ACCEPT" if accepted else "REJECT",
        rationale=body.rationale.strip(), created_at=now,
    ))
    await db.flush()
    case.status = target.value
    case.version += 1
    case.updated_at = now
    if accepted:
        case.accepted_at = now
    else:
        case.rejected_at = now
    _record_case_event(db, case=case, actor=actor,
                       event_type=("evidence.classroom_accepted.v1" if accepted
                                   else "evidence.classroom_rejected.v1"),
                       payload={"to_status": case.status,
                                "final_reviewer_person_id": str(actor.person_id),
                                "formal_evidence_accepted": accepted})
    await db.commit()
    return await _full_response(db, case)


@router.post("/classroom-evidence-cases/{case_id}/accept",
             response_model=EvidenceCaseResponse)
async def accept_classroom_evidence(
    case_id: UUID, body: EvidenceDecisionRequest,
    actor: Annotated[ActorContext, Depends(require_role("ASSESSOR"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> EvidenceCaseResponse:
    return await _decide(db=db, case_id=case_id, body=body, actor=actor,
                         target=EvidenceCaseStatus.ACCEPTED)


@router.post("/classroom-evidence-cases/{case_id}/reject",
             response_model=EvidenceCaseResponse)
async def reject_classroom_evidence(
    case_id: UUID, body: EvidenceDecisionRequest,
    actor: Annotated[ActorContext, Depends(require_role("ASSESSOR"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> EvidenceCaseResponse:
    return await _decide(db=db, case_id=case_id, body=body, actor=actor,
                         target=EvidenceCaseStatus.REJECTED)
