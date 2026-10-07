from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import AppError
from app.gate_assessment.domain import GateAssessmentState
from app.gate_assessment.models import (
    GateAssessment,
    GateDefinition,
    GateDefinitionOutcome,
    GateDefinitionRequirement,
    GateDefinitionVersion,
    GateProfileSnapshot,
    GateProfileSnapshotClaim,
    GateReview,
    GateSnapshotEvidenceRef,
    GateSnapshotPatternRef,
)


@dataclass(frozen=True)
class GateDefinitionRead:
    gate_definition_id: UUID
    gate_definition_version_id: UUID
    gate_code: str
    version_number: int
    name: str
    decision_question: str
    requirements: tuple[str, ...]
    outcomes: tuple[str, ...]


@dataclass(frozen=True)
class GateEvidenceLineageRead:
    evidence_set_member_id: UUID
    evidence_case_id: UUID
    interpretation_id: UUID
    interpretation_version: int
    evidence_relationship: str
    signal: str
    scope: str
    confidence: str
    context_difficulty: str
    prompt_contamination: str
    source_independence_group: str
    accepted_at: datetime
    source_observation_id: UUID
    source_context: str
    source_reference: str
    observation_type: str


@dataclass(frozen=True)
class GatePatternLineageRead:
    source_pattern_id: UUID
    source_pattern_version: int
    relationship: str
    pattern_status: str
    behaviour_code: str
    scope: str
    reviewed_at: datetime
    evidence: tuple[GateEvidenceLineageRead, ...]


@dataclass(frozen=True)
class GateClaimRead:
    source_claim_id: UUID
    source_claim_version: int
    capability_id: UUID
    state: str
    level: str
    proven_scope: str
    evidence_recency: str
    confidence_in_claim: str
    reviewed_at: datetime
    next_evidence_needed: str
    source_profile_update_case_id: UUID
    supporting_patterns: tuple[GatePatternLineageRead, ...]
    contradictory_patterns: tuple[GatePatternLineageRead, ...]


@dataclass(frozen=True)
class GateEvidenceGapRead:
    source_claim_id: UUID
    capability_id: UUID
    next_evidence_needed: str


@dataclass(frozen=True)
class GateRiskPatternRead:
    source_claim_id: UUID
    capability_id: UUID
    pattern: GatePatternLineageRead


@dataclass(frozen=True)
class GatePinnedProfileRead:
    profile_snapshot_id: UUID
    snapshot_version: int
    source_flag_profile_id: UUID
    source_flag_profile_version: int
    source_track_code: str
    source_profile_updated_at: datetime
    captured_at: datetime
    claims: tuple[GateClaimRead, ...]
    evidence_gaps: tuple[GateEvidenceGapRead, ...]
    risk_patterns: tuple[GateRiskPatternRead, ...]


@dataclass(frozen=True)
class AssessorPreDecisionRead:
    gate_assessment_id: UUID
    gate_assessment_version: int
    gate_assessment_state: str
    gate_review_id: UUID
    organization_context_id: UUID
    subject_person_id: UUID
    opened_by: UUID
    opened_at: datetime
    definition: GateDefinitionRead
    pinned_profile: GatePinnedProfileRead


def _lineage_error(message: str, *, details: dict | None = None) -> AppError:
    return AppError(
        "GATE_PRE_DECISION_LINEAGE_INCOMPLETE",
        message,
        status_code=409,
        details=details,
    )


async def _load_definition(
    db: AsyncSession,
    *,
    gate_definition_version_id: UUID,
) -> GateDefinitionRead:
    row = (
        await db.execute(
            select(GateDefinitionVersion, GateDefinition)
            .join(
                GateDefinition,
                GateDefinition.id == GateDefinitionVersion.gate_definition_id,
            )
            .where(GateDefinitionVersion.id == gate_definition_version_id)
        )
    ).one_or_none()
    if row is None:
        raise _lineage_error("Pinned Gate Definition version could not be found.")

    version, definition = row
    requirements = (
        await db.execute(
            select(GateDefinitionRequirement)
            .where(
                GateDefinitionRequirement.gate_definition_version_id
                == version.id
            )
            .order_by(
                GateDefinitionRequirement.position,
                GateDefinitionRequirement.id,
            )
        )
    ).scalars().all()
    outcomes = (
        await db.execute(
            select(GateDefinitionOutcome)
            .where(
                GateDefinitionOutcome.gate_definition_version_id == version.id
            )
            .order_by(
                GateDefinitionOutcome.position,
                GateDefinitionOutcome.id,
            )
        )
    ).scalars().all()
    if not requirements or not outcomes:
        raise _lineage_error(
            "Pinned Gate Definition version is missing requirements or outcomes.",
            details={"gate_definition_version_id": str(version.id)},
        )

    return GateDefinitionRead(
        gate_definition_id=definition.id,
        gate_definition_version_id=version.id,
        gate_code=definition.code,
        version_number=version.version_number,
        name=version.name,
        decision_question=version.decision_question,
        requirements=tuple(item.requirement_text for item in requirements),
        outcomes=tuple(item.outcome_text for item in outcomes),
    )


def _evidence_read(row: GateSnapshotEvidenceRef) -> GateEvidenceLineageRead:
    return GateEvidenceLineageRead(
        evidence_set_member_id=row.evidence_set_member_id,
        evidence_case_id=row.evidence_case_id,
        interpretation_id=row.interpretation_id,
        interpretation_version=row.interpretation_version,
        evidence_relationship=row.evidence_relationship,
        signal=row.signal,
        scope=row.scope,
        confidence=row.confidence,
        context_difficulty=row.context_difficulty,
        prompt_contamination=row.prompt_contamination,
        source_independence_group=row.source_independence_group,
        accepted_at=row.accepted_at,
        source_observation_id=row.source_observation_id,
        source_context=row.source_context,
        source_reference=row.source_reference,
        observation_type=row.observation_type,
    )


async def _load_pattern(
    db: AsyncSession,
    *,
    row: GateSnapshotPatternRef,
) -> GatePatternLineageRead:
    evidence_rows = (
        await db.execute(
            select(GateSnapshotEvidenceRef)
            .where(
                GateSnapshotEvidenceRef.gate_snapshot_pattern_ref_id == row.id
            )
            .order_by(
                GateSnapshotEvidenceRef.accepted_at,
                GateSnapshotEvidenceRef.evidence_set_member_id,
            )
        )
    ).scalars().all()
    if not evidence_rows:
        raise _lineage_error(
            "Pinned Gate Pattern has no Evidence lineage.",
            details={"source_pattern_id": str(row.source_pattern_id)},
        )

    return GatePatternLineageRead(
        source_pattern_id=row.source_pattern_id,
        source_pattern_version=row.source_pattern_version,
        relationship=row.relationship,
        pattern_status=row.pattern_status,
        behaviour_code=row.behaviour_code,
        scope=row.scope,
        reviewed_at=row.reviewed_at,
        evidence=tuple(_evidence_read(item) for item in evidence_rows),
    )


async def _load_claim(
    db: AsyncSession,
    *,
    row: GateProfileSnapshotClaim,
) -> GateClaimRead:
    pattern_rows = (
        await db.execute(
            select(GateSnapshotPatternRef)
            .where(
                GateSnapshotPatternRef.gate_profile_snapshot_claim_id == row.id
            )
            .order_by(
                GateSnapshotPatternRef.relationship,
                GateSnapshotPatternRef.reviewed_at,
                GateSnapshotPatternRef.source_pattern_id,
            )
        )
    ).scalars().all()
    if not pattern_rows:
        raise _lineage_error(
            "Pinned Gate Claim has no Pattern lineage.",
            details={"source_claim_id": str(row.source_claim_id)},
        )

    supporting: list[GatePatternLineageRead] = []
    contradictory: list[GatePatternLineageRead] = []
    for pattern_row in pattern_rows:
        pattern = await _load_pattern(db, row=pattern_row)
        if pattern.relationship == "SUPPORTING":
            supporting.append(pattern)
        elif pattern.relationship == "CONTRADICTORY":
            contradictory.append(pattern)
        else:
            raise _lineage_error(
                "Pinned Gate Pattern relationship is not recognized.",
                details={
                    "source_pattern_id": str(pattern.source_pattern_id),
                    "relationship": pattern.relationship,
                },
            )

    return GateClaimRead(
        source_claim_id=row.source_claim_id,
        source_claim_version=row.source_claim_version,
        capability_id=row.capability_id,
        state=row.state,
        level=row.level,
        proven_scope=row.proven_scope,
        evidence_recency=row.evidence_recency,
        confidence_in_claim=row.confidence_in_claim,
        reviewed_at=row.reviewed_at,
        next_evidence_needed=row.next_evidence_needed,
        source_profile_update_case_id=row.source_profile_update_case_id,
        supporting_patterns=tuple(supporting),
        contradictory_patterns=tuple(contradictory),
    )


async def load_assessor_pre_decision_read(
    db: AsyncSession,
    *,
    organization_context_id: UUID,
    gate_review_id: UUID,
) -> AssessorPreDecisionRead:
    review = (
        await db.execute(
            select(GateReview).where(
                GateReview.id == gate_review_id,
                GateReview.organization_context_id == organization_context_id,
            )
        )
    ).scalar_one_or_none()
    if review is None:
        raise AppError(
            "GATE_REVIEW_NOT_FOUND",
            "Gate Review not found.",
            status_code=404,
        )

    assessment = (
        await db.execute(
            select(GateAssessment).where(
                GateAssessment.id == review.gate_assessment_id,
                GateAssessment.organization_context_id
                == organization_context_id,
                GateAssessment.subject_person_id == review.subject_person_id,
                GateAssessment.gate_definition_version_id
                == review.gate_definition_version_id,
            )
        )
    ).scalar_one_or_none()
    if assessment is None:
        raise _lineage_error("Gate Review is missing its Gate Assessment.")
    if assessment.state != GateAssessmentState.REVIEW_REQUIRED.value:
        raise AppError(
            "GATE_REVIEW_NOT_PENDING_DECISION",
            "Gate Review is not in REVIEW_REQUIRED.",
            status_code=409,
            details={"current_state": assessment.state},
        )
    if assessment.version != review.gate_assessment_version:
        raise AppError(
            "GATE_REVIEW_ASSESSMENT_VERSION_CHANGED",
            "Gate Assessment version changed after this review was opened.",
            status_code=409,
            details={
                "review_version": review.gate_assessment_version,
                "current_version": assessment.version,
            },
        )

    snapshot = (
        await db.execute(
            select(GateProfileSnapshot).where(
                GateProfileSnapshot.id == review.gate_profile_snapshot_id,
                GateProfileSnapshot.gate_assessment_id == assessment.id,
                GateProfileSnapshot.organization_context_id
                == organization_context_id,
                GateProfileSnapshot.subject_person_id == review.subject_person_id,
            )
        )
    ).scalar_one_or_none()
    if snapshot is None:
        raise _lineage_error("Gate Review is missing its pinned Profile Snapshot.")

    definition = await _load_definition(
        db,
        gate_definition_version_id=review.gate_definition_version_id,
    )

    claim_rows = (
        await db.execute(
            select(GateProfileSnapshotClaim)
            .where(
                GateProfileSnapshotClaim.gate_profile_snapshot_id == snapshot.id
            )
            .order_by(
                GateProfileSnapshotClaim.capability_id,
                GateProfileSnapshotClaim.source_claim_id,
            )
        )
    ).scalars().all()

    claims: list[GateClaimRead] = []
    evidence_gaps: list[GateEvidenceGapRead] = []
    risk_patterns: list[GateRiskPatternRead] = []
    for claim_row in claim_rows:
        claim = await _load_claim(db, row=claim_row)
        claims.append(claim)
        evidence_gaps.append(
            GateEvidenceGapRead(
                source_claim_id=claim.source_claim_id,
                capability_id=claim.capability_id,
                next_evidence_needed=claim.next_evidence_needed,
            )
        )
        risk_patterns.extend(
            GateRiskPatternRead(
                source_claim_id=claim.source_claim_id,
                capability_id=claim.capability_id,
                pattern=pattern,
            )
            for pattern in claim.contradictory_patterns
        )

    return AssessorPreDecisionRead(
        gate_assessment_id=assessment.id,
        gate_assessment_version=assessment.version,
        gate_assessment_state=assessment.state,
        gate_review_id=review.id,
        organization_context_id=review.organization_context_id,
        subject_person_id=review.subject_person_id,
        opened_by=review.opened_by,
        opened_at=review.opened_at,
        definition=definition,
        pinned_profile=GatePinnedProfileRead(
            profile_snapshot_id=snapshot.id,
            snapshot_version=snapshot.snapshot_version,
            source_flag_profile_id=snapshot.source_flag_profile_id,
            source_flag_profile_version=snapshot.source_flag_profile_version,
            source_track_code=snapshot.source_track_code,
            source_profile_updated_at=snapshot.source_profile_updated_at,
            captured_at=snapshot.captured_at,
            claims=tuple(claims),
            evidence_gaps=tuple(evidence_gaps),
            risk_patterns=tuple(risk_patterns),
        ),
    )
