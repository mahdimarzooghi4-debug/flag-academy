from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.errors import AppError
from app.identity.auth import ActorContext, require_role
from app.patterns.application import (
    CreateEvidenceSetCommand,
    CreatePatternCandidateCommand,
    PatternCandidateEvidenceInput,
    ReviewPatternCandidateCommand,
    create_evidence_set,
    create_pattern_candidate,
    review_pattern_candidate,
)
from app.patterns.domain import PatternEvidenceRelationship, PatternStatus
from app.patterns.evidence_reader import SqlAcceptedEvidenceReader
from app.patterns.models import (
    BehaviourPattern,
    EvidenceSet,
    EvidenceSetMember,
    PatternCandidate,
    PatternCandidateEvidence,
    PatternReview,
)

router = APIRouter(prefix="/api/v1", tags=["patterns"])


class EvidenceSetCreateRequest(BaseModel):
    subject_person_id: UUID
    evidence_case_ids: list[UUID] = Field(min_length=1)
    expected_version: int = Field(ge=0)
    idempotency_key: str = Field(min_length=1, max_length=160)


class PatternCandidateEvidenceRequest(BaseModel):
    evidence_set_member_id: UUID
    relationship: PatternEvidenceRelationship


class PatternCandidateCreateRequest(BaseModel):
    subject_person_id: UUID
    evidence_set_id: UUID
    behaviour_code: str = Field(min_length=1, max_length=120)
    behaviour_description: str = Field(min_length=1, max_length=4000)
    proposed_pattern_status: PatternStatus
    scope: str = Field(min_length=1, max_length=255)
    rationale: str = Field(min_length=1, max_length=8000)
    evidence: list[PatternCandidateEvidenceRequest] = Field(min_length=1)
    expected_version: int = Field(ge=0)
    idempotency_key: str = Field(min_length=1, max_length=160)


class PatternReviewRequest(BaseModel):
    resulting_pattern_status: PatternStatus
    rationale: str = Field(min_length=1, max_length=8000)
    expected_version: int = Field(ge=1)
    idempotency_key: str = Field(min_length=1, max_length=160)


class EvidenceSetMemberResponse(BaseModel):
    id: UUID
    evidence_case_id: UUID
    interpretation_id: UUID
    interpretation_version: int
    behaviour_code: str
    signal: str
    scope: str
    confidence: str
    accepted_at: datetime
    target_links: list[dict]


class EvidenceSetResponse(BaseModel):
    id: UUID
    evidence_set_key: UUID
    version_number: int
    subject_person_id: UUID
    created_at: datetime
    members: list[EvidenceSetMemberResponse]


class PatternCandidateEvidenceResponse(BaseModel):
    evidence_set_member_id: UUID
    relationship: str


class PatternCandidateResponse(BaseModel):
    id: UUID
    version: int
    subject_person_id: UUID
    evidence_set_id: UUID
    behaviour_code: str
    behaviour_description: str
    proposed_pattern_status: str
    scope: str
    rationale: str
    created_at: datetime
    evidence: list[PatternCandidateEvidenceResponse]


class PatternSummaryResponse(BaseModel):
    id: UUID
    version: int
    subject_person_id: UUID
    behaviour_code: str
    behaviour_description: str
    pattern_status: str
    scope: str
    reviewed_by: UUID
    reviewed_at: datetime
    updated_at: datetime


class CandidatePatternResponse(BaseModel):
    id: UUID
    behaviour_code: str
    behaviour_description: str
    pattern_status: str
    scope: str
    reviewed_at: datetime
    updated_at: datetime


class PatternCandidateLineageResponse(BaseModel):
    id: UUID
    version: int
    proposed_pattern_status: str
    behaviour_code: str
    behaviour_description: str
    scope: str
    rationale: str
    created_by: UUID
    created_at: datetime


class EvidenceSetLineageResponse(BaseModel):
    id: UUID
    evidence_set_key: UUID
    version_number: int
    created_by: UUID
    created_at: datetime


class PatternReviewLineageResponse(BaseModel):
    id: UUID
    reviewer_id: UUID
    resulting_pattern_status: str
    rationale: str
    created_at: datetime


class PatternSourceLineageResponse(BaseModel):
    source_observation_id: str
    source_context: str
    source_reference: str
    observation_type: str


class PatternEvidenceLineageResponse(BaseModel):
    relationship: str
    evidence_set_member_id: UUID
    evidence_case_id: UUID
    interpretation_id: UUID
    interpretation_version: int
    behaviour_code: str
    signal: str
    scope: str
    confidence: str
    context_difficulty: str
    prompt_contamination: str
    source_independence_group: str
    accepted_at: datetime
    target_links: list[dict]
    source_lineage: PatternSourceLineageResponse


class ReviewedPatternLineageResponse(BaseModel):
    id: UUID
    version: int
    organization_context_id: UUID
    subject_person_id: UUID
    behaviour_code: str
    behaviour_description: str
    pattern_status: str
    scope: str
    rationale: str
    reviewed_by: UUID
    reviewed_at: datetime
    created_at: datetime
    updated_at: datetime
    candidate: PatternCandidateLineageResponse
    evidence_set: EvidenceSetLineageResponse
    review: PatternReviewLineageResponse
    evidence: list[PatternEvidenceLineageResponse]


def _source_lineage_response(value: dict) -> PatternSourceLineageResponse:
    try:
        return PatternSourceLineageResponse(
            source_observation_id=str(value["source_observation_id"]),
            source_context=str(value["source_context"]),
            source_reference=str(value["source_reference"]),
            observation_type=str(value["observation_type"]),
        )
    except KeyError as exc:
        raise AppError(
            "PATTERN_LINEAGE_INCOMPLETE",
            "Pattern source lineage is incomplete.",
            status_code=409,
        ) from exc


async def _load_pattern(
    db: AsyncSession,
    *,
    actor: ActorContext,
    pattern_id: UUID,
) -> BehaviourPattern:
    pattern = (
        await db.execute(
            select(BehaviourPattern).where(
                BehaviourPattern.id == pattern_id,
                BehaviourPattern.organization_context_id
                == actor.organization_context_id,
            )
        )
    ).scalar_one_or_none()
    if pattern is None:
        raise AppError(
            "PATTERN_NOT_FOUND",
            "Reviewed Pattern not found.",
            status_code=404,
        )
    return pattern


async def _lineage_response(
    db: AsyncSession,
    pattern: BehaviourPattern,
) -> ReviewedPatternLineageResponse:
    candidate = (
        await db.execute(
            select(PatternCandidate).where(
                PatternCandidate.id == pattern.source_pattern_candidate_id,
                PatternCandidate.organization_context_id
                == pattern.organization_context_id,
                PatternCandidate.subject_person_id == pattern.subject_person_id,
            )
        )
    ).scalar_one_or_none()
    evidence_set = (
        await db.execute(
            select(EvidenceSet).where(
                EvidenceSet.id == pattern.evidence_set_id,
                EvidenceSet.organization_context_id
                == pattern.organization_context_id,
                EvidenceSet.subject_person_id == pattern.subject_person_id,
            )
        )
    ).scalar_one_or_none()
    review = (
        await db.execute(
            select(PatternReview).where(
                PatternReview.pattern_candidate_id
                == pattern.source_pattern_candidate_id,
                PatternReview.resulting_pattern_id == pattern.id,
            )
        )
    ).scalar_one_or_none()

    if candidate is None or evidence_set is None or review is None:
        raise AppError(
            "PATTERN_LINEAGE_INCOMPLETE",
            "Reviewed Pattern lineage is incomplete.",
            status_code=409,
        )

    rows = (
        await db.execute(
            select(PatternCandidateEvidence, EvidenceSetMember)
            .join(
                EvidenceSetMember,
                EvidenceSetMember.id
                == PatternCandidateEvidence.evidence_set_member_id,
            )
            .where(
                PatternCandidateEvidence.pattern_candidate_id == candidate.id,
                EvidenceSetMember.evidence_set_id == evidence_set.id,
            )
            .order_by(EvidenceSetMember.created_at, EvidenceSetMember.id)
        )
    ).all()
    if not rows:
        raise AppError(
            "PATTERN_LINEAGE_INCOMPLETE",
            "Reviewed Pattern has no Evidence lineage.",
            status_code=409,
        )

    evidence = [
        PatternEvidenceLineageResponse(
            relationship=relation.relationship,
            evidence_set_member_id=member.id,
            evidence_case_id=member.evidence_case_id,
            interpretation_id=member.interpretation_id,
            interpretation_version=member.interpretation_version,
            behaviour_code=member.behaviour_code,
            signal=member.signal,
            scope=member.scope,
            confidence=member.confidence,
            context_difficulty=member.context_difficulty,
            prompt_contamination=member.prompt_contamination,
            source_independence_group=member.source_independence_group,
            accepted_at=member.accepted_at,
            target_links=member.target_links,
            source_lineage=_source_lineage_response(member.source_lineage),
        )
        for relation, member in rows
    ]

    return ReviewedPatternLineageResponse(
        id=pattern.id,
        version=pattern.version,
        organization_context_id=pattern.organization_context_id,
        subject_person_id=pattern.subject_person_id,
        behaviour_code=pattern.behaviour_code,
        behaviour_description=pattern.behaviour_description,
        pattern_status=pattern.pattern_status,
        scope=pattern.scope,
        rationale=pattern.rationale,
        reviewed_by=pattern.reviewed_by,
        reviewed_at=pattern.reviewed_at,
        created_at=pattern.created_at,
        updated_at=pattern.updated_at,
        candidate=PatternCandidateLineageResponse(
            id=candidate.id,
            version=candidate.version,
            proposed_pattern_status=candidate.proposed_pattern_status,
            behaviour_code=candidate.behaviour_code,
            behaviour_description=candidate.behaviour_description,
            scope=candidate.scope,
            rationale=candidate.rationale,
            created_by=candidate.created_by,
            created_at=candidate.created_at,
        ),
        evidence_set=EvidenceSetLineageResponse(
            id=evidence_set.id,
            evidence_set_key=evidence_set.evidence_set_key,
            version_number=evidence_set.version_number,
            created_by=evidence_set.created_by,
            created_at=evidence_set.created_at,
        ),
        review=PatternReviewLineageResponse(
            id=review.id,
            reviewer_id=review.reviewer_id,
            resulting_pattern_status=review.resulting_pattern_status,
            rationale=review.rationale,
            created_at=review.created_at,
        ),
        evidence=evidence,
    )


async def _evidence_set_response(
    db: AsyncSession,
    evidence_set: EvidenceSet,
) -> EvidenceSetResponse:
    members = (
        await db.execute(
            select(EvidenceSetMember)
            .where(EvidenceSetMember.evidence_set_id == evidence_set.id)
            .order_by(EvidenceSetMember.created_at, EvidenceSetMember.id)
        )
    ).scalars().all()
    return EvidenceSetResponse(
        id=evidence_set.id,
        evidence_set_key=evidence_set.evidence_set_key,
        version_number=evidence_set.version_number,
        subject_person_id=evidence_set.subject_person_id,
        created_at=evidence_set.created_at,
        members=[
            EvidenceSetMemberResponse(
                id=member.id,
                evidence_case_id=member.evidence_case_id,
                interpretation_id=member.interpretation_id,
                interpretation_version=member.interpretation_version,
                behaviour_code=member.behaviour_code,
                signal=member.signal,
                scope=member.scope,
                confidence=member.confidence,
                accepted_at=member.accepted_at,
                target_links=member.target_links,
            )
            for member in members
        ],
    )


async def _pattern_candidate_response(
    db: AsyncSession,
    candidate: PatternCandidate,
) -> PatternCandidateResponse:
    evidence = (
        await db.execute(
            select(PatternCandidateEvidence)
            .where(PatternCandidateEvidence.pattern_candidate_id == candidate.id)
            .order_by(PatternCandidateEvidence.evidence_set_member_id)
        )
    ).scalars().all()
    return PatternCandidateResponse(
        id=candidate.id,
        version=candidate.version,
        subject_person_id=candidate.subject_person_id,
        evidence_set_id=candidate.evidence_set_id,
        behaviour_code=candidate.behaviour_code,
        behaviour_description=candidate.behaviour_description,
        proposed_pattern_status=candidate.proposed_pattern_status,
        scope=candidate.scope,
        rationale=candidate.rationale,
        created_at=candidate.created_at,
        evidence=[
            PatternCandidateEvidenceResponse(
                evidence_set_member_id=item.evidence_set_member_id,
                relationship=item.relationship,
            )
            for item in evidence
        ],
    )


@router.post("/pattern-evidence-sets", response_model=EvidenceSetResponse)
async def create_pattern_evidence_set(
    body: EvidenceSetCreateRequest,
    actor: Annotated[ActorContext, Depends(require_role("ASSESSOR"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> EvidenceSetResponse:
    evidence_set = await create_evidence_set(
        db,
        reader=SqlAcceptedEvidenceReader(db),
        command=CreateEvidenceSetCommand(
            organization_context_id=actor.organization_context_id,
            subject_person_id=body.subject_person_id,
            created_by=actor.person_id,
            evidence_case_ids=tuple(body.evidence_case_ids),
            expected_version=body.expected_version,
            idempotency_key=body.idempotency_key,
            trace_id=actor.trace_id,
        ),
    )
    return await _evidence_set_response(db, evidence_set)


@router.post("/pattern-candidates", response_model=PatternCandidateResponse)
async def create_pattern_candidate_api(
    body: PatternCandidateCreateRequest,
    actor: Annotated[ActorContext, Depends(require_role("ASSESSOR"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> PatternCandidateResponse:
    candidate = await create_pattern_candidate(
        db,
        command=CreatePatternCandidateCommand(
            organization_context_id=actor.organization_context_id,
            subject_person_id=body.subject_person_id,
            evidence_set_id=body.evidence_set_id,
            behaviour_code=body.behaviour_code,
            behaviour_description=body.behaviour_description,
            proposed_pattern_status=body.proposed_pattern_status.value,
            scope=body.scope,
            rationale=body.rationale,
            evidence=tuple(
                PatternCandidateEvidenceInput(
                    evidence_set_member_id=item.evidence_set_member_id,
                    relationship=item.relationship.value,
                )
                for item in body.evidence
            ),
            created_by=actor.person_id,
            expected_version=body.expected_version,
            idempotency_key=body.idempotency_key,
            trace_id=actor.trace_id,
        ),
    )
    return await _pattern_candidate_response(db, candidate)


@router.post(
    "/pattern-candidates/{candidate_id}/review",
    response_model=PatternSummaryResponse,
)
async def review_pattern_candidate_api(
    candidate_id: UUID,
    body: PatternReviewRequest,
    actor: Annotated[ActorContext, Depends(require_role("ASSESSOR"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> PatternSummaryResponse:
    pattern = await review_pattern_candidate(
        db,
        command=ReviewPatternCandidateCommand(
            organization_context_id=actor.organization_context_id,
            pattern_candidate_id=candidate_id,
            reviewer_id=actor.person_id,
            resulting_pattern_status=body.resulting_pattern_status.value,
            rationale=body.rationale,
            expected_version=body.expected_version,
            idempotency_key=body.idempotency_key,
            trace_id=actor.trace_id,
        ),
    )
    return PatternSummaryResponse(
        id=pattern.id,
        version=pattern.version,
        subject_person_id=pattern.subject_person_id,
        behaviour_code=pattern.behaviour_code,
        behaviour_description=pattern.behaviour_description,
        pattern_status=pattern.pattern_status,
        scope=pattern.scope,
        reviewed_by=pattern.reviewed_by,
        reviewed_at=pattern.reviewed_at,
        updated_at=pattern.updated_at,
    )


@router.get("/me/patterns", response_model=list[CandidatePatternResponse])
async def list_my_reviewed_patterns(
    actor: Annotated[ActorContext, Depends(require_role("CANDIDATE"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> list[CandidatePatternResponse]:
    patterns = (
        await db.execute(
            select(BehaviourPattern)
            .where(
                BehaviourPattern.organization_context_id
                == actor.organization_context_id,
                BehaviourPattern.subject_person_id == actor.person_id,
            )
            .order_by(BehaviourPattern.updated_at.desc(), BehaviourPattern.id)
        )
    ).scalars().all()
    return [
        CandidatePatternResponse(
            id=pattern.id,
            behaviour_code=pattern.behaviour_code,
            behaviour_description=pattern.behaviour_description,
            pattern_status=pattern.pattern_status,
            scope=pattern.scope,
            reviewed_at=pattern.reviewed_at,
            updated_at=pattern.updated_at,
        )
        for pattern in patterns
    ]


@router.get("/patterns", response_model=list[PatternSummaryResponse])
async def list_reviewed_patterns(
    actor: Annotated[ActorContext, Depends(require_role("ASSESSOR"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> list[PatternSummaryResponse]:
    patterns = (
        await db.execute(
            select(BehaviourPattern)
            .where(
                BehaviourPattern.organization_context_id
                == actor.organization_context_id
            )
            .order_by(BehaviourPattern.updated_at.desc(), BehaviourPattern.id)
        )
    ).scalars().all()
    return [
        PatternSummaryResponse(
            id=pattern.id,
            version=pattern.version,
            subject_person_id=pattern.subject_person_id,
            behaviour_code=pattern.behaviour_code,
            behaviour_description=pattern.behaviour_description,
            pattern_status=pattern.pattern_status,
            scope=pattern.scope,
            reviewed_by=pattern.reviewed_by,
            reviewed_at=pattern.reviewed_at,
            updated_at=pattern.updated_at,
        )
        for pattern in patterns
    ]


@router.get(
    "/patterns/{pattern_id}/lineage",
    response_model=ReviewedPatternLineageResponse,
)
async def get_reviewed_pattern_lineage(
    pattern_id: UUID,
    actor: Annotated[ActorContext, Depends(require_role("ASSESSOR"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> ReviewedPatternLineageResponse:
    pattern = await _load_pattern(
        db,
        actor=actor,
        pattern_id=pattern_id,
    )
    return await _lineage_response(db, pattern)
