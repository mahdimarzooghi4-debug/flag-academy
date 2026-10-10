"""Private human submission into the existing Evidence state machine."""

from datetime import UTC, datetime
from typing import Annotated, Never
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.errors import AppError
from app.evidence.api import (
    CLASSROOM_SOURCE_CONTEXT,
    EvidenceSubmitRequest,
    _record_case_event,
    _require_expected_version,
)
from app.evidence.classroom_evidence_draft_api import _lineage_matches, _verified_review
from app.evidence.classroom_source_review_api import _source_and_mandate
from app.evidence.domain import (
    EvidenceCaseStatus,
    InterpretationStatus,
    case_transition_allowed,
    interpretation_contract_valid,
)
from app.evidence.models import EvidenceCase, EvidenceInterpretation, EvidenceLink
from app.identity.auth import ActorContext, require_role

router = APIRouter(prefix="/api/v1", tags=["evidence"])


class ClassroomSubmissionResponse(BaseModel):
    case_id: UUID
    version: int
    status: str
    interpretation_id: UUID
    interpretation_version: int
    candidate_visible: bool


def _deny() -> Never:
    raise AppError(
        "CLASSROOM_EVIDENCE_NOT_FOUND",
        "Classroom case or authorization not found.",
        status_code=404,
    )


@router.post(
    "/classroom-evidence-cases/{case_id}/submit",
    response_model=ClassroomSubmissionResponse,
)
async def submit_classroom_evidence(
    case_id: UUID,
    body: EvidenceSubmitRequest,
    actor: Annotated[ActorContext, Depends(require_role("ASSESSOR"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> ClassroomSubmissionResponse:
    # The initial tenant-scoped lookup obtains an opaque ID only, not access.
    source_id = (
        await db.execute(
            select(EvidenceCase.source_observation_id).where(
                EvidenceCase.id == case_id,
                EvidenceCase.organization_context_id == actor.organization_context_id,
                EvidenceCase.source_context == CLASSROOM_SOURCE_CONTEXT,
            )
        )
    ).scalar_one_or_none()
    if source_id is None:
        _deny()
    # Preserve the Draft creation lock order: source -> grant -> EvidenceCase.
    source, grant = await _source_and_mandate(
        db, actor=actor, observation_id=source_id,
    )
    review = await _verified_review(db, actor=actor, source=source, grant=grant)
    case = (
        await db.execute(
            select(EvidenceCase)
            .where(
                EvidenceCase.id == case_id,
                EvidenceCase.organization_context_id == actor.organization_context_id,
                EvidenceCase.source_observation_id == source.id,
                EvidenceCase.source_context == CLASSROOM_SOURCE_CONTEXT,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if case is None or not _lineage_matches(case, source, review, actor):
        _deny()

    _require_expected_version(case, body.expected_version)
    if not case_transition_allowed(case.status, EvidenceCaseStatus.SUBMITTED.value):
        raise AppError(
            "EVIDENCE_STATUS_TRANSITION_INVALID",
            "Classroom case cannot be submitted from this state.",
            status_code=422,
        )
    contract = body.interpretation.model_dump(mode="json")
    if not interpretation_contract_valid(contract):
        raise AppError(
            "EVIDENCE_INTERPRETATION_INVALID",
            "Interpretation contract is invalid.",
            status_code=422,
        )

    now = datetime.now(UTC)
    interpretation = EvidenceInterpretation(
        id=uuid4(),
        evidence_case_id=case.id,
        version_number=1,
        status=InterpretationStatus.ACTIVE.value,
        behaviour_code=body.interpretation.behaviour_code.strip(),
        behaviour_description=body.interpretation.behaviour_description.strip(),
        signal=body.interpretation.signal.value,
        scope=body.interpretation.scope.strip(),
        confidence=body.interpretation.confidence,
        context_difficulty=body.interpretation.context_difficulty.strip(),
        prompt_contamination=body.interpretation.prompt_contamination.strip(),
        ai_contribution=body.interpretation.ai_contribution.strip(),
        mode=body.interpretation.mode.strip(),
        rationale=body.interpretation.rationale.strip(),
        created_by=actor.person_id,
        created_at=now,
    )
    db.add(interpretation)
    await db.flush()
    for link in body.interpretation.links:
        db.add(EvidenceLink(
            id=uuid4(),
            interpretation_id=interpretation.id,
            target_type=link.target_type,
            target_ref=link.target_ref.strip(),
            signal=link.signal.value,
            scope=link.scope.strip(),
            relevance=link.relevance,
            confidence=link.confidence,
        ))
    case.status = EvidenceCaseStatus.SUBMITTED.value
    case.version += 1
    case.updated_at = now
    _record_case_event(
        db, case=case, actor=actor,
        event_type="evidence.interpretation_submitted.v1",
        payload={
            "interpretation_id": str(interpretation.id),
            "interpretation_version": interpretation.version_number,
            "source_observation_id": str(source.id),
        },
    )
    await db.commit()
    return ClassroomSubmissionResponse(
        case_id=case.id,
        version=case.version,
        status=case.status,
        interpretation_id=interpretation.id,
        interpretation_version=interpretation.version_number,
        candidate_visible=case.candidate_visible,
    )
