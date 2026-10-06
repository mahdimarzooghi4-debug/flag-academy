from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import AppError
from app.patterns.models import (
    BehaviourPattern,
    EvidenceSet,
    EvidenceSetMember,
    PatternCandidate,
    PatternCandidateEvidence,
    PatternReview,
)


@dataclass(frozen=True)
class ReviewedPatternSourceContract:
    source_observation_id: UUID
    source_context: str
    source_reference: str
    observation_type: str


@dataclass(frozen=True)
class ReviewedPatternEvidenceContract:
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
    source: ReviewedPatternSourceContract


@dataclass(frozen=True)
class ReviewedPatternSnapshotContract:
    pattern_id: UUID
    pattern_version: int
    organization_context_id: UUID
    subject_person_id: UUID
    behaviour_code: str
    behaviour_description: str
    pattern_status: str
    scope: str
    reviewed_at: datetime
    evidence: tuple[ReviewedPatternEvidenceContract, ...]


def _source_contract(value: dict) -> ReviewedPatternSourceContract:
    try:
        return ReviewedPatternSourceContract(
            source_observation_id=UUID(str(value["source_observation_id"])),
            source_context=str(value["source_context"]),
            source_reference=str(value["source_reference"]),
            observation_type=str(value["observation_type"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise AppError(
            "PATTERN_LINEAGE_INCOMPLETE",
            "Reviewed Pattern source lineage is incomplete.",
            status_code=409,
        ) from exc


async def load_reviewed_pattern_snapshots(
    db: AsyncSession,
    *,
    organization_context_id: UUID,
    subject_person_id: UUID,
    pattern_ids: tuple[UUID, ...],
) -> list[ReviewedPatternSnapshotContract]:
    if not pattern_ids:
        return []

    patterns = (
        await db.execute(
            select(BehaviourPattern)
            .where(
                BehaviourPattern.id.in_(pattern_ids),
                BehaviourPattern.organization_context_id == organization_context_id,
                BehaviourPattern.subject_person_id == subject_person_id,
            )
            .order_by(BehaviourPattern.reviewed_at, BehaviourPattern.id)
        )
    ).scalars().all()

    snapshots: list[ReviewedPatternSnapshotContract] = []
    for pattern in patterns:
        candidate = (
            await db.execute(
                select(PatternCandidate).where(
                    PatternCandidate.id == pattern.source_pattern_candidate_id,
                    PatternCandidate.organization_context_id
                    == organization_context_id,
                    PatternCandidate.subject_person_id == subject_person_id,
                )
            )
        ).scalar_one_or_none()
        evidence_set = (
            await db.execute(
                select(EvidenceSet).where(
                    EvidenceSet.id == pattern.evidence_set_id,
                    EvidenceSet.organization_context_id == organization_context_id,
                    EvidenceSet.subject_person_id == subject_person_id,
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

        if (
            candidate is None
            or evidence_set is None
            or review is None
            or review.resulting_pattern_status != pattern.pattern_status
        ):
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

        evidence = tuple(
            ReviewedPatternEvidenceContract(
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
                source=_source_contract(member.source_lineage),
            )
            for relation, member in rows
        )

        snapshots.append(
            ReviewedPatternSnapshotContract(
                pattern_id=pattern.id,
                pattern_version=pattern.version,
                organization_context_id=pattern.organization_context_id,
                subject_person_id=pattern.subject_person_id,
                behaviour_code=pattern.behaviour_code,
                behaviour_description=pattern.behaviour_description,
                pattern_status=pattern.pattern_status,
                scope=pattern.scope,
                reviewed_at=pattern.reviewed_at,
                evidence=evidence,
            )
        )

    return snapshots
