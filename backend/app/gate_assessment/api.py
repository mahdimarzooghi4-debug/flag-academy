from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.gate_assessment.application import (
    CompleteGateReviewCommand,
    OpenGateReviewCommand,
    complete_gate_review,
    open_gate_review,
)
from app.gate_assessment.candidate_projection import (
    load_candidate_gate_projection,
)
from app.gate_assessment.models import (
    GateAssessment,
    GateDefinition,
    GateDefinitionVersion,
    GateReview,
)
from app.gate_assessment.profile_reader import FlagProfileSnapshotReader
from app.gate_assessment.read_models import (
    AssessorPreDecisionRead,
    GateClaimRead,
    GateEvidenceLineageRead,
    GatePatternLineageRead,
    load_assessor_pre_decision_read,
)
from app.identity.auth import ActorContext, require_role

router = APIRouter(prefix="/api/v1", tags=["gate-assessment"])


class CandidateGateResponse(BaseModel):
    gate_code: str
    gate_name: str
    status: str
    evidence_gaps: list[str]
    remediation_status: str | None


class CandidateGateProjectionResponse(BaseModel):
    gates: list[CandidateGateResponse]


class GateAssessmentResponse(BaseModel):
    id: UUID
    version: int
    subject_person_id: UUID
    state: str
    gate_definition_version_id: UUID
    gate_definition_version_number: int
    gate_code: str
    gate_name: str
    pending_review_id: UUID | None


class OpenGateReviewRequest(BaseModel):
    track_code: str = Field(min_length=1, max_length=128)
    expected_version: int = Field(ge=1)
    idempotency_key: str = Field(min_length=1, max_length=160)


class OpenGateReviewResponse(BaseModel):
    assessment: GateAssessmentResponse
    gate_review_id: UUID
    profile_snapshot_id: UUID
    profile_snapshot_version: int


class GateEvidenceLineageResponse(BaseModel):
    evidence_case_id: UUID
    interpretation_id: UUID
    interpretation_version: int
    evidence_relationship: str
    signal: str
    scope: str
    confidence: str
    accepted_at: datetime
    source_observation_id: UUID
    source_context: str
    source_reference: str
    observation_type: str


class GatePatternLineageResponse(BaseModel):
    source_pattern_id: UUID
    source_pattern_version: int
    relationship: str
    pattern_status: str
    behaviour_code: str
    scope: str
    reviewed_at: datetime
    evidence: list[GateEvidenceLineageResponse]


class GateClaimResponse(BaseModel):
    source_claim_id: UUID
    source_claim_version: int
    capability_id: UUID
    state: str
    level: str
    proven_scope: str
    evidence_recency: str
    reviewed_at: datetime
    next_evidence_needed: str
    supporting_patterns: list[GatePatternLineageResponse]
    contradictory_patterns: list[GatePatternLineageResponse]


class GateDefinitionReviewResponse(BaseModel):
    gate_definition_version_id: UUID
    gate_code: str
    version_number: int
    name: str
    decision_question: str
    requirements: list[str]
    outcomes: list[str]


class GatePinnedProfileResponse(BaseModel):
    profile_snapshot_id: UUID
    snapshot_version: int
    source_flag_profile_version: int
    source_track_code: str
    captured_at: datetime
    claims: list[GateClaimResponse]
    evidence_gaps: list[str]


class AssessorPreDecisionResponse(BaseModel):
    gate_assessment_id: UUID
    gate_assessment_version: int
    gate_assessment_state: str
    gate_review_id: UUID
    subject_person_id: UUID
    opened_at: datetime
    definition: GateDefinitionReviewResponse
    pinned_profile: GatePinnedProfileResponse


class CompleteGateReviewRequest(BaseModel):
    decision_state: Literal["PASS_CONFIRMED", "FAIL"]
    rationale: str = Field(min_length=1, max_length=8000)
    expected_version: int = Field(ge=1)
    expected_gate_definition_version_id: UUID
    expected_profile_snapshot_id: UUID
    expected_profile_snapshot_version: int = Field(ge=1)
    idempotency_key: str = Field(min_length=1, max_length=160)


class CompleteGateReviewResponse(BaseModel):
    assessment: GateAssessmentResponse
    gate_review_id: UUID
    decision_id: UUID
    decision_state: str
    decided_at: datetime


async def _assessment_response(
    db: AsyncSession,
    assessment: GateAssessment,
) -> GateAssessmentResponse:
    row = (
        await db.execute(
            select(GateDefinitionVersion, GateDefinition)
            .join(
                GateDefinition,
                GateDefinition.id == GateDefinitionVersion.gate_definition_id,
            )
            .where(
                GateDefinitionVersion.id
                == assessment.gate_definition_version_id
            )
        )
    ).one()
    version, definition = row

    pending_review_id: UUID | None = None
    if assessment.state == "REVIEW_REQUIRED":
        pending_review_id = (
            await db.execute(
                select(GateReview.id)
                .where(
                    GateReview.gate_assessment_id == assessment.id,
                    GateReview.gate_assessment_version == assessment.version,
                    GateReview.organization_context_id
                    == assessment.organization_context_id,
                )
                .order_by(GateReview.opened_at.desc(), GateReview.id.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

    return GateAssessmentResponse(
        id=assessment.id,
        version=assessment.version,
        subject_person_id=assessment.subject_person_id,
        state=assessment.state,
        gate_definition_version_id=assessment.gate_definition_version_id,
        gate_definition_version_number=version.version_number,
        gate_code=definition.code,
        gate_name=version.name,
        pending_review_id=pending_review_id,
    )


def _evidence_response(
    evidence: GateEvidenceLineageRead,
) -> GateEvidenceLineageResponse:
    return GateEvidenceLineageResponse(
        evidence_case_id=evidence.evidence_case_id,
        interpretation_id=evidence.interpretation_id,
        interpretation_version=evidence.interpretation_version,
        evidence_relationship=evidence.evidence_relationship,
        signal=evidence.signal,
        scope=evidence.scope,
        confidence=evidence.confidence,
        accepted_at=evidence.accepted_at,
        source_observation_id=evidence.source_observation_id,
        source_context=evidence.source_context,
        source_reference=evidence.source_reference,
        observation_type=evidence.observation_type,
    )


def _pattern_response(
    pattern: GatePatternLineageRead,
) -> GatePatternLineageResponse:
    return GatePatternLineageResponse(
        source_pattern_id=pattern.source_pattern_id,
        source_pattern_version=pattern.source_pattern_version,
        relationship=pattern.relationship,
        pattern_status=pattern.pattern_status,
        behaviour_code=pattern.behaviour_code,
        scope=pattern.scope,
        reviewed_at=pattern.reviewed_at,
        evidence=[_evidence_response(item) for item in pattern.evidence],
    )


def _claim_response(claim: GateClaimRead) -> GateClaimResponse:
    return GateClaimResponse(
        source_claim_id=claim.source_claim_id,
        source_claim_version=claim.source_claim_version,
        capability_id=claim.capability_id,
        state=claim.state,
        level=claim.level,
        proven_scope=claim.proven_scope,
        evidence_recency=claim.evidence_recency,
        reviewed_at=claim.reviewed_at,
        next_evidence_needed=claim.next_evidence_needed,
        supporting_patterns=[
            _pattern_response(item) for item in claim.supporting_patterns
        ],
        contradictory_patterns=[
            _pattern_response(item) for item in claim.contradictory_patterns
        ],
    )


def _pre_decision_response(
    read: AssessorPreDecisionRead,
) -> AssessorPreDecisionResponse:
    return AssessorPreDecisionResponse(
        gate_assessment_id=read.gate_assessment_id,
        gate_assessment_version=read.gate_assessment_version,
        gate_assessment_state=read.gate_assessment_state,
        gate_review_id=read.gate_review_id,
        subject_person_id=read.subject_person_id,
        opened_at=read.opened_at,
        definition=GateDefinitionReviewResponse(
            gate_definition_version_id=(
                read.definition.gate_definition_version_id
            ),
            gate_code=read.definition.gate_code,
            version_number=read.definition.version_number,
            name=read.definition.name,
            decision_question=read.definition.decision_question,
            requirements=list(read.definition.requirements),
            outcomes=list(read.definition.outcomes),
        ),
        pinned_profile=GatePinnedProfileResponse(
            profile_snapshot_id=read.pinned_profile.profile_snapshot_id,
            snapshot_version=read.pinned_profile.snapshot_version,
            source_flag_profile_version=(
                read.pinned_profile.source_flag_profile_version
            ),
            source_track_code=read.pinned_profile.source_track_code,
            captured_at=read.pinned_profile.captured_at,
            claims=[_claim_response(item) for item in read.pinned_profile.claims],
            evidence_gaps=[
                item.next_evidence_needed
                for item in read.pinned_profile.evidence_gaps
            ],
        ),
    )


@router.get(
    "/gate-assessments",
    response_model=list[GateAssessmentResponse],
)
async def list_gate_assessments(
    actor: Annotated[ActorContext, Depends(require_role("ASSESSOR"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    subject_person_id: UUID | None = None,
) -> list[GateAssessmentResponse]:
    query = select(GateAssessment).where(
        GateAssessment.organization_context_id == actor.organization_context_id
    )
    if subject_person_id is not None:
        query = query.where(
            GateAssessment.subject_person_id == subject_person_id
        )
    assessments = (
        await db.execute(
            query.order_by(
                GateAssessment.subject_person_id,
                GateAssessment.created_at,
                GateAssessment.id,
            )
        )
    ).scalars().all()
    return [await _assessment_response(db, item) for item in assessments]


@router.post(
    "/gate-assessments/{assessment_id}/reviews",
    response_model=OpenGateReviewResponse,
)
async def open_gate_review_api(
    assessment_id: UUID,
    body: OpenGateReviewRequest,
    actor: Annotated[ActorContext, Depends(require_role("ASSESSOR"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> OpenGateReviewResponse:
    result = await open_gate_review(
        db,
        reader=FlagProfileSnapshotReader(db),
        command=OpenGateReviewCommand(
            organization_context_id=actor.organization_context_id,
            gate_assessment_id=assessment_id,
            track_code=body.track_code,
            opened_by=actor.person_id,
            expected_version=body.expected_version,
            idempotency_key=body.idempotency_key,
            trace_id=actor.trace_id,
        ),
    )
    return OpenGateReviewResponse(
        assessment=await _assessment_response(db, result.gate_assessment),
        gate_review_id=result.review.id,
        profile_snapshot_id=result.profile_snapshot.id,
        profile_snapshot_version=result.profile_snapshot.snapshot_version,
    )


@router.get(
    "/gate-reviews/{review_id}/pre-decision",
    response_model=AssessorPreDecisionResponse,
)
async def get_gate_review_pre_decision(
    review_id: UUID,
    actor: Annotated[ActorContext, Depends(require_role("ASSESSOR"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> AssessorPreDecisionResponse:
    read = await load_assessor_pre_decision_read(
        db,
        organization_context_id=actor.organization_context_id,
        gate_review_id=review_id,
    )
    return _pre_decision_response(read)


@router.post(
    "/gate-reviews/{review_id}/decision",
    response_model=CompleteGateReviewResponse,
)
async def complete_gate_review_api(
    review_id: UUID,
    body: CompleteGateReviewRequest,
    actor: Annotated[ActorContext, Depends(require_role("ASSESSOR"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> CompleteGateReviewResponse:
    result = await complete_gate_review(
        db,
        command=CompleteGateReviewCommand(
            organization_context_id=actor.organization_context_id,
            gate_review_id=review_id,
            reviewer_id=actor.person_id,
            decision_state=body.decision_state,
            rationale=body.rationale,
            expected_version=body.expected_version,
            expected_gate_definition_version_id=(
                body.expected_gate_definition_version_id
            ),
            expected_profile_snapshot_id=body.expected_profile_snapshot_id,
            expected_profile_snapshot_version=(
                body.expected_profile_snapshot_version
            ),
            idempotency_key=body.idempotency_key,
            trace_id=actor.trace_id,
        ),
    )
    return CompleteGateReviewResponse(
        assessment=await _assessment_response(db, result.gate_assessment),
        gate_review_id=result.review.id,
        decision_id=result.decision.id,
        decision_state=result.decision.decision_state,
        decided_at=result.decision.decided_at,
    )


@router.get(
    "/me/gate-assessments",
    response_model=CandidateGateProjectionResponse,
)
async def get_my_gate_assessments(
    actor: Annotated[ActorContext, Depends(require_role("CANDIDATE"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> CandidateGateProjectionResponse:
    projection = await load_candidate_gate_projection(
        db,
        organization_context_id=actor.organization_context_id,
        subject_person_id=actor.person_id,
    )
    return CandidateGateProjectionResponse(
        gates=[
            CandidateGateResponse(
                gate_code=item.gate_code,
                gate_name=item.gate_name,
                status=item.status,
                evidence_gaps=list(item.evidence_gaps),
                remediation_status=item.remediation_status,
            )
            for item in projection.gates
        ]
    )
