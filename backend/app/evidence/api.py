from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.errors import AppError
from app.evidence.domain import (
    EvidenceCaseStatus,
    EvidenceSignal,
    InterpretationStatus,
    case_transition_allowed,
    interpretation_contract_valid,
)
from app.evidence.models import (
    CandidateResponse,
    EvidenceCase,
    EvidenceInterpretation,
    EvidenceLink,
    EvidenceReview,
)
from app.identity.auth import ActorContext, require_role
from app.platform.events import new_event, record_event

router = APIRouter(prefix="/api/v1", tags=["evidence"])


class EvidenceLinkInput(BaseModel):
    target_type: str = Field(pattern="^(CAPABILITY|COMPETENCY|GATE)$")
    target_ref: str = Field(min_length=1, max_length=255)
    signal: EvidenceSignal
    scope: str = Field(min_length=1, max_length=255)
    relevance: str = Field(pattern="^(LOW|MEDIUM|HIGH)$")
    confidence: str = Field(pattern="^(LOW|MEDIUM|HIGH)$")


class EvidenceInterpretationInput(BaseModel):
    behaviour_code: str = Field(min_length=1, max_length=120)
    behaviour_description: str = Field(min_length=1, max_length=4000)
    signal: EvidenceSignal
    scope: str = Field(min_length=1, max_length=255)
    confidence: str = Field(pattern="^(LOW|MEDIUM|HIGH)$")
    context_difficulty: str = Field(min_length=1, max_length=255)
    prompt_contamination: str = Field(min_length=1, max_length=255)
    ai_contribution: str = Field(pattern="^NONE$")
    mode: str = Field(min_length=1, max_length=32)
    rationale: str = Field(min_length=1, max_length=8000)
    links: list[EvidenceLinkInput] = Field(min_length=1)


class EvidenceSubmitRequest(BaseModel):
    expected_version: int = Field(ge=1)
    interpretation: EvidenceInterpretationInput


class EvidenceReviewStartRequest(BaseModel):
    expected_version: int = Field(ge=1)
    rationale: str = Field(min_length=1, max_length=8000)


class EvidenceDecisionRequest(BaseModel):
    expected_version: int = Field(ge=1)
    rationale: str = Field(min_length=1, max_length=8000)


class EvidenceContextRequest(BaseModel):
    expected_version: int = Field(ge=1)
    context_request: str = Field(min_length=1, max_length=8000)


class CandidateResponseCreate(BaseModel):
    expected_version: int = Field(ge=1)
    response_text: str = Field(min_length=1, max_length=8000)
    idempotency_key: str = Field(min_length=1, max_length=160)


class EvidenceLinkResponse(BaseModel):
    id: UUID
    target_type: str
    target_ref: str
    signal: str
    scope: str
    relevance: str
    confidence: str


class EvidenceInterpretationResponse(BaseModel):
    id: UUID
    version_number: int
    status: str
    behaviour_code: str
    behaviour_description: str
    signal: str
    scope: str
    confidence: str
    context_difficulty: str
    prompt_contamination: str
    ai_contribution: str
    mode: str
    rationale: str
    created_by: UUID
    created_at: datetime
    links: list[EvidenceLinkResponse]


class EvidenceReviewResponse(BaseModel):
    id: UUID
    reviewer_id: UUID
    decision: str
    rationale: str
    created_at: datetime


class CandidateResponseItem(BaseModel):
    id: UUID
    candidate_id: UUID
    response_text: str
    created_at: datetime


class EvidenceCaseResponse(BaseModel):
    id: UUID
    version: int
    organization_context_id: UUID
    subject_person_id: UUID
    source_observation_id: UUID
    source_context: str
    source_reference: str
    source_runtime_event_id: UUID | None
    observation_type: str
    observed_fact: str
    observed_payload: dict
    occurred_at: datetime
    source_independence_group: str
    provenance: dict
    integrity_state: str
    status: str
    context_request: str | None
    interpretation: EvidenceInterpretationResponse | None
    reviews: list[EvidenceReviewResponse]
    candidate_responses: list[CandidateResponseItem]
    created_at: datetime
    updated_at: datetime
    accepted_at: datetime | None
    rejected_at: datetime | None


class CandidateEvidenceCaseResponse(BaseModel):
    id: UUID
    version: int
    source_observation_id: UUID
    source_context: str
    source_reference: str
    observation_type: str
    observed_fact: str
    observed_payload: dict
    occurred_at: datetime
    integrity_state: str
    status: str
    context_request: str | None
    accepted_interpretation: EvidenceInterpretationResponse | None
    candidate_responses: list[CandidateResponseItem]
    created_at: datetime
    updated_at: datetime


async def _load_case(
    db: AsyncSession,
    *,
    actor: ActorContext,
    case_id: UUID,
    for_update: bool = False,
) -> EvidenceCase:
    stmt = select(EvidenceCase).where(
        EvidenceCase.id == case_id,
        EvidenceCase.organization_context_id == actor.organization_context_id,
    )
    if for_update:
        stmt = stmt.with_for_update()
    case = (await db.execute(stmt)).scalar_one_or_none()
    if case is None:
        raise AppError("EVIDENCE_CASE_NOT_FOUND", "Evidence case not found.", status_code=404)
    return case


def _require_expected_version(case: EvidenceCase, expected_version: int) -> None:
    if case.version != expected_version:
        raise AppError(
            "VERSION_CONFLICT",
            "Evidence case changed. Refresh and retry.",
            status_code=409,
            details={
                "expected_version": expected_version,
                "current_version": case.version,
            },
        )


async def _active_interpretation(
    db: AsyncSession,
    case_id: UUID,
) -> EvidenceInterpretation | None:
    return (
        await db.execute(
            select(EvidenceInterpretation)
            .where(
                EvidenceInterpretation.evidence_case_id == case_id,
                EvidenceInterpretation.status == InterpretationStatus.ACTIVE.value,
            )
            .order_by(EvidenceInterpretation.version_number.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


async def _interpretation_response(
    db: AsyncSession,
    interpretation: EvidenceInterpretation | None,
) -> EvidenceInterpretationResponse | None:
    if interpretation is None:
        return None
    links = (
        await db.execute(
            select(EvidenceLink)
            .where(EvidenceLink.interpretation_id == interpretation.id)
            .order_by(EvidenceLink.target_type, EvidenceLink.target_ref, EvidenceLink.id)
        )
    ).scalars().all()
    return EvidenceInterpretationResponse(
        id=interpretation.id,
        version_number=interpretation.version_number,
        status=interpretation.status,
        behaviour_code=interpretation.behaviour_code,
        behaviour_description=interpretation.behaviour_description,
        signal=interpretation.signal,
        scope=interpretation.scope,
        confidence=interpretation.confidence,
        context_difficulty=interpretation.context_difficulty,
        prompt_contamination=interpretation.prompt_contamination,
        ai_contribution=interpretation.ai_contribution,
        mode=interpretation.mode,
        rationale=interpretation.rationale,
        created_by=interpretation.created_by,
        created_at=interpretation.created_at,
        links=[
            EvidenceLinkResponse(
                id=item.id,
                target_type=item.target_type,
                target_ref=item.target_ref,
                signal=item.signal,
                scope=item.scope,
                relevance=item.relevance,
                confidence=item.confidence,
            )
            for item in links
        ],
    )


async def _candidate_responses(
    db: AsyncSession,
    case_id: UUID,
) -> list[CandidateResponseItem]:
    rows = (
        await db.execute(
            select(CandidateResponse)
            .where(CandidateResponse.evidence_case_id == case_id)
            .order_by(CandidateResponse.created_at, CandidateResponse.id)
        )
    ).scalars().all()
    return [
        CandidateResponseItem(
            id=item.id,
            candidate_id=item.candidate_id,
            response_text=item.response_text,
            created_at=item.created_at,
        )
        for item in rows
    ]


async def _full_response(db: AsyncSession, case: EvidenceCase) -> EvidenceCaseResponse:
    interpretation = await _active_interpretation(db, case.id)
    reviews = (
        await db.execute(
            select(EvidenceReview)
            .where(EvidenceReview.evidence_case_id == case.id)
            .order_by(EvidenceReview.created_at, EvidenceReview.id)
        )
    ).scalars().all()
    return EvidenceCaseResponse(
        id=case.id,
        version=case.version,
        organization_context_id=case.organization_context_id,
        subject_person_id=case.subject_person_id,
        source_observation_id=case.source_observation_id,
        source_context=case.source_context,
        source_reference=case.source_reference,
        source_runtime_event_id=case.source_runtime_event_id,
        observation_type=case.observation_type,
        observed_fact=case.observed_fact,
        observed_payload=case.observed_payload,
        occurred_at=case.occurred_at,
        source_independence_group=case.source_independence_group,
        provenance=case.provenance,
        integrity_state=case.integrity_state,
        status=case.status,
        context_request=case.context_request,
        interpretation=await _interpretation_response(db, interpretation),
        reviews=[
            EvidenceReviewResponse(
                id=item.id,
                reviewer_id=item.reviewer_id,
                decision=item.decision,
                rationale=item.rationale,
                created_at=item.created_at,
            )
            for item in reviews
        ],
        candidate_responses=await _candidate_responses(db, case.id),
        created_at=case.created_at,
        updated_at=case.updated_at,
        accepted_at=case.accepted_at,
        rejected_at=case.rejected_at,
    )


async def _candidate_case_response(
    db: AsyncSession,
    case: EvidenceCase,
) -> CandidateEvidenceCaseResponse:
    interpretation = None
    if case.status == EvidenceCaseStatus.ACCEPTED.value:
        interpretation = await _interpretation_response(
            db,
            await _active_interpretation(db, case.id),
        )
    return CandidateEvidenceCaseResponse(
        id=case.id,
        version=case.version,
        source_observation_id=case.source_observation_id,
        source_context=case.source_context,
        source_reference=case.source_reference,
        observation_type=case.observation_type,
        observed_fact=case.observed_fact,
        observed_payload=case.candidate_visible_payload,
        occurred_at=case.occurred_at,
        integrity_state=case.integrity_state,
        status=case.status,
        context_request=case.context_request,
        accepted_interpretation=interpretation,
        candidate_responses=await _candidate_responses(db, case.id),
        created_at=case.created_at,
        updated_at=case.updated_at,
    )


def _record_case_event(
    db: AsyncSession,
    *,
    case: EvidenceCase,
    actor: ActorContext,
    event_type: str,
    payload: dict,
) -> None:
    record_event(
        db,
        new_event(
            event_type=event_type,
            aggregate_type="EvidenceCase",
            aggregate_id=case.id,
            aggregate_version=case.version,
            actor={"type": "PERSON", "id": str(actor.person_id)},
            organization_context_id=actor.organization_context_id,
            data_classification="CONFIDENTIAL",
            payload={"evidence_case_id": str(case.id), **payload},
            trace_id=actor.trace_id,
        ),
    )


@router.get("/evidence-cases", response_model=list[EvidenceCaseResponse])
async def list_evidence_cases(
    actor: Annotated[ActorContext, Depends(require_role("ASSESSOR"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> list[EvidenceCaseResponse]:
    cases = (
        await db.execute(
            select(EvidenceCase)
            .where(EvidenceCase.organization_context_id == actor.organization_context_id)
            .order_by(EvidenceCase.created_at, EvidenceCase.id)
        )
    ).scalars().all()
    return [await _full_response(db, case) for case in cases]


@router.get("/evidence-cases/{case_id}", response_model=EvidenceCaseResponse)
async def get_evidence_case(
    case_id: UUID,
    actor: Annotated[ActorContext, Depends(require_role("ASSESSOR"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> EvidenceCaseResponse:
    return await _full_response(
        db,
        await _load_case(db, actor=actor, case_id=case_id),
    )


@router.get("/me/evidence-cases", response_model=list[CandidateEvidenceCaseResponse])
async def list_my_evidence_cases(
    actor: Annotated[ActorContext, Depends(require_role("CANDIDATE"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> list[CandidateEvidenceCaseResponse]:
    cases = (
        await db.execute(
            select(EvidenceCase)
            .where(
                EvidenceCase.organization_context_id == actor.organization_context_id,
                EvidenceCase.subject_person_id == actor.person_id,
                EvidenceCase.candidate_visible.is_(True),
            )
            .order_by(EvidenceCase.created_at, EvidenceCase.id)
        )
    ).scalars().all()
    return [await _candidate_case_response(db, case) for case in cases]


@router.post("/evidence-cases/{case_id}/submit", response_model=EvidenceCaseResponse)
async def submit_evidence_case(
    case_id: UUID,
    body: EvidenceSubmitRequest,
    actor: Annotated[ActorContext, Depends(require_role("ASSESSOR"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> EvidenceCaseResponse:
    case = await _load_case(db, actor=actor, case_id=case_id, for_update=True)
    _require_expected_version(case, body.expected_version)
    if not case_transition_allowed(case.status, EvidenceCaseStatus.SUBMITTED.value):
        raise AppError(
            "EVIDENCE_STATUS_TRANSITION_INVALID",
            "Evidence case cannot be submitted from its current state.",
            status_code=422,
            details={"current": case.status, "target": EvidenceCaseStatus.SUBMITTED.value},
        )

    contract = body.interpretation.model_dump(mode="json")
    if not interpretation_contract_valid(contract):
        raise AppError(
            "EVIDENCE_INTERPRETATION_INVALID",
            "Evidence interpretation contract is invalid.",
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
        db.add(
            EvidenceLink(
                id=uuid4(),
                interpretation_id=interpretation.id,
                target_type=link.target_type,
                target_ref=link.target_ref.strip(),
                signal=link.signal.value,
                scope=link.scope.strip(),
                relevance=link.relevance,
                confidence=link.confidence,
            )
        )

    case.status = EvidenceCaseStatus.SUBMITTED.value
    case.version += 1
    case.updated_at = now
    _record_case_event(
        db,
        case=case,
        actor=actor,
        event_type="evidence.interpretation_submitted.v1",
        payload={
            "interpretation_id": str(interpretation.id),
            "interpretation_version": interpretation.version_number,
            "source_observation_id": str(case.source_observation_id),
        },
    )
    await db.commit()
    return await _full_response(db, case)


@router.post("/evidence-cases/{case_id}/reviews", response_model=EvidenceCaseResponse)
async def start_evidence_review(
    case_id: UUID,
    body: EvidenceReviewStartRequest,
    actor: Annotated[ActorContext, Depends(require_role("ASSESSOR"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> EvidenceCaseResponse:
    case = await _load_case(db, actor=actor, case_id=case_id, for_update=True)
    _require_expected_version(case, body.expected_version)
    if not case_transition_allowed(case.status, EvidenceCaseStatus.UNDER_REVIEW.value):
        raise AppError(
            "EVIDENCE_STATUS_TRANSITION_INVALID",
            "Evidence case cannot enter review from its current state.",
            status_code=422,
            details={"current": case.status, "target": EvidenceCaseStatus.UNDER_REVIEW.value},
        )
    if case.status == EvidenceCaseStatus.NEEDS_CONTEXT.value:
        latest_request_at = (
            await db.execute(
                select(EvidenceReview.created_at)
                .where(
                    EvidenceReview.evidence_case_id == case.id,
                    EvidenceReview.decision == "NEEDS_CONTEXT",
                )
                .order_by(EvidenceReview.created_at.desc(), EvidenceReview.id.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        latest_response_at = (
            await db.execute(
                select(CandidateResponse.created_at)
                .where(CandidateResponse.evidence_case_id == case.id)
                .order_by(CandidateResponse.created_at.desc(), CandidateResponse.id.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if (
            latest_request_at is None
            or latest_response_at is None
            or latest_response_at < latest_request_at
        ):
            raise AppError(
                "CANDIDATE_CONTEXT_REQUIRED",
                "Candidate context must be added after the latest request before review can resume.",
                status_code=409,
            )

    now = datetime.now(UTC)
    previous = case.status
    case.status = EvidenceCaseStatus.UNDER_REVIEW.value
    case.version += 1
    case.updated_at = now
    db.add(
        EvidenceReview(
            id=uuid4(),
            evidence_case_id=case.id,
            reviewer_id=actor.person_id,
            decision="REVIEW_STARTED",
            rationale=body.rationale.strip(),
            created_at=now,
        )
    )
    _record_case_event(
        db,
        case=case,
        actor=actor,
        event_type="evidence.review_started.v1",
        payload={"from_status": previous, "to_status": case.status},
    )
    await db.commit()
    return await _full_response(db, case)


@router.post("/evidence-cases/{case_id}/request-context", response_model=EvidenceCaseResponse)
async def request_candidate_context(
    case_id: UUID,
    body: EvidenceContextRequest,
    actor: Annotated[ActorContext, Depends(require_role("ASSESSOR"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> EvidenceCaseResponse:
    case = await _load_case(db, actor=actor, case_id=case_id, for_update=True)
    _require_expected_version(case, body.expected_version)
    if not case_transition_allowed(case.status, EvidenceCaseStatus.NEEDS_CONTEXT.value):
        raise AppError(
            "EVIDENCE_STATUS_TRANSITION_INVALID",
            "Candidate context cannot be requested from the current state.",
            status_code=422,
            details={"current": case.status, "target": EvidenceCaseStatus.NEEDS_CONTEXT.value},
        )

    now = datetime.now(UTC)
    case.status = EvidenceCaseStatus.NEEDS_CONTEXT.value
    case.context_request = body.context_request.strip()
    case.version += 1
    case.updated_at = now
    db.add(
        EvidenceReview(
            id=uuid4(),
            evidence_case_id=case.id,
            reviewer_id=actor.person_id,
            decision="NEEDS_CONTEXT",
            rationale=body.context_request.strip(),
            created_at=now,
        )
    )
    _record_case_event(
        db,
        case=case,
        actor=actor,
        event_type="evidence.context_requested.v1",
        payload={"subject_person_id": str(case.subject_person_id)},
    )
    await db.commit()
    return await _full_response(db, case)


@router.post("/evidence-cases/{case_id}/candidate-response", response_model=CandidateEvidenceCaseResponse)
async def add_candidate_response(
    case_id: UUID,
    body: CandidateResponseCreate,
    actor: Annotated[ActorContext, Depends(require_role("CANDIDATE"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> CandidateEvidenceCaseResponse:
    case = await _load_case(db, actor=actor, case_id=case_id, for_update=True)
    if case.subject_person_id != actor.person_id or not case.candidate_visible:
        raise AppError("EVIDENCE_CASE_NOT_FOUND", "Evidence case not found.", status_code=404)

    existing = (
        await db.execute(
            select(CandidateResponse).where(
                CandidateResponse.evidence_case_id == case.id,
                CandidateResponse.idempotency_key == body.idempotency_key,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return await _candidate_case_response(db, case)

    _require_expected_version(case, body.expected_version)
    if case.status != EvidenceCaseStatus.NEEDS_CONTEXT.value:
        raise AppError(
            "EVIDENCE_CONTEXT_NOT_REQUESTED",
            "Candidate context can only be added when it has been requested.",
            status_code=422,
        )

    now = datetime.now(UTC)
    response = CandidateResponse(
        id=uuid4(),
        evidence_case_id=case.id,
        candidate_id=actor.person_id,
        response_text=body.response_text.strip(),
        idempotency_key=body.idempotency_key,
        created_at=now,
    )
    db.add(response)
    case.version += 1
    case.updated_at = now
    _record_case_event(
        db,
        case=case,
        actor=actor,
        event_type="evidence.candidate_context_added.v1",
        payload={"candidate_response_id": str(response.id)},
    )
    await db.commit()
    return await _candidate_case_response(db, case)


async def _decide_evidence_case(
    *,
    db: AsyncSession,
    actor: ActorContext,
    case_id: UUID,
    body: EvidenceDecisionRequest,
    target: EvidenceCaseStatus,
) -> EvidenceCaseResponse:
    case = await _load_case(db, actor=actor, case_id=case_id, for_update=True)
    _require_expected_version(case, body.expected_version)
    if not case_transition_allowed(case.status, target.value):
        raise AppError(
            "EVIDENCE_STATUS_TRANSITION_INVALID",
            "Evidence decision is invalid from the current state.",
            status_code=422,
            details={"current": case.status, "target": target.value},
        )
    interpretation = await _active_interpretation(db, case.id)
    if interpretation is None:
        raise AppError(
            "EVIDENCE_INTERPRETATION_REQUIRED",
            "An active interpretation is required before a review decision.",
            status_code=409,
        )

    now = datetime.now(UTC)
    case.status = target.value
    case.version += 1
    case.updated_at = now
    if target == EvidenceCaseStatus.ACCEPTED:
        case.accepted_at = now
    else:
        case.rejected_at = now

    decision = "ACCEPT" if target == EvidenceCaseStatus.ACCEPTED else "REJECT"
    db.add(
        EvidenceReview(
            id=uuid4(),
            evidence_case_id=case.id,
            reviewer_id=actor.person_id,
            decision=decision,
            rationale=body.rationale.strip(),
            created_at=now,
        )
    )
    _record_case_event(
        db,
        case=case,
        actor=actor,
        event_type=(
            "evidence.accepted.v1"
            if target == EvidenceCaseStatus.ACCEPTED
            else "evidence.rejected.v1"
        ),
        payload={
            "subject_person_id": str(case.subject_person_id),
            "source_observation_id": str(case.source_observation_id),
            "interpretation_id": str(interpretation.id),
            "interpretation_version": interpretation.version_number,
        },
    )
    await db.commit()
    return await _full_response(db, case)


@router.post("/evidence-cases/{case_id}/accept", response_model=EvidenceCaseResponse)
async def accept_evidence_case(
    case_id: UUID,
    body: EvidenceDecisionRequest,
    actor: Annotated[ActorContext, Depends(require_role("ASSESSOR"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> EvidenceCaseResponse:
    return await _decide_evidence_case(
        db=db,
        actor=actor,
        case_id=case_id,
        body=body,
        target=EvidenceCaseStatus.ACCEPTED,
    )


@router.post("/evidence-cases/{case_id}/reject", response_model=EvidenceCaseResponse)
async def reject_evidence_case(
    case_id: UUID,
    body: EvidenceDecisionRequest,
    actor: Annotated[ActorContext, Depends(require_role("ASSESSOR"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> EvidenceCaseResponse:
    return await _decide_evidence_case(
        db=db,
        actor=actor,
        case_id=case_id,
        body=body,
        target=EvidenceCaseStatus.REJECTED,
    )
