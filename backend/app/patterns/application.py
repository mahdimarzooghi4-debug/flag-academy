from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import AppError
from app.patterns.domain import (
    PatternStatus,
    evidence_set_contract_valid,
    pattern_candidate_contract_valid,
)
from app.patterns.models import (
    BehaviourPattern,
    EvidenceSet,
    EvidenceSetMember,
    PatternCandidate,
    PatternCandidateEvidence,
    PatternReview,
)
from app.platform.events import EventEnvelope, new_event, record_event


@dataclass(frozen=True)
class AcceptedEvidenceSnapshot:
    evidence_case_id: UUID
    interpretation_id: UUID
    interpretation_version: int
    organization_context_id: UUID
    subject_person_id: UUID
    status: str
    interpretation_status: str
    behaviour_code: str
    signal: str
    scope: str
    confidence: str
    context_difficulty: str
    prompt_contamination: str
    source_independence_group: str
    accepted_at: datetime
    target_links: list[dict]
    source_lineage: dict


class AcceptedEvidenceReader(Protocol):
    async def load(
        self,
        *,
        organization_context_id: UUID,
        subject_person_id: UUID,
        evidence_case_ids: tuple[UUID, ...],
    ) -> list[AcceptedEvidenceSnapshot]: ...


@dataclass(frozen=True)
class CreateEvidenceSetCommand:
    organization_context_id: UUID
    subject_person_id: UUID
    created_by: UUID
    evidence_case_ids: tuple[UUID, ...]
    expected_version: int
    idempotency_key: str
    trace_id: str


def _require_create_expected_version(expected_version: int) -> None:
    if expected_version != 0:
        raise AppError(
            "VERSION_CONFLICT",
            "Evidence set changed. Refresh and retry.",
            status_code=409,
            details={
                "expected_version": expected_version,
                "current_version": 0,
            },
        )


def _accepted_snapshot_matches_context(
    snapshot: AcceptedEvidenceSnapshot,
    *,
    organization_context_id: UUID,
    subject_person_id: UUID,
) -> bool:
    return (
        snapshot.status == "ACCEPTED"
        and snapshot.interpretation_status == "ACTIVE"
        and snapshot.organization_context_id == organization_context_id
        and snapshot.subject_person_id == subject_person_id
    )


async def create_evidence_set(
    db: AsyncSession,
    *,
    reader: AcceptedEvidenceReader,
    command: CreateEvidenceSetCommand,
) -> EvidenceSet:
    evidence_case_ids = tuple(command.evidence_case_ids)
    if not evidence_case_ids:
        raise AppError(
            "PATTERN_EVIDENCE_SET_EMPTY",
            "Evidence set must contain at least one accepted Evidence case.",
            status_code=422,
        )
    if len(set(evidence_case_ids)) != len(evidence_case_ids):
        raise AppError(
            "PATTERN_EVIDENCE_DUPLICATE",
            "Evidence set cannot contain duplicate Evidence cases.",
            status_code=422,
        )

    idempotency_key = command.idempotency_key.strip()
    if not idempotency_key:
        raise AppError(
            "PATTERN_IDEMPOTENCY_KEY_REQUIRED",
            "Idempotency key is required.",
            status_code=422,
        )

    existing = (
        await db.execute(
            select(EvidenceSet).where(
                EvidenceSet.organization_context_id == command.organization_context_id,
                EvidenceSet.created_by == command.created_by,
                EvidenceSet.idempotency_key == idempotency_key,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        existing_ids = tuple(
            (
                await db.execute(
                    select(EvidenceSetMember.evidence_case_id).where(
                        EvidenceSetMember.evidence_set_id == existing.id
                    )
                )
            )
            .scalars()
            .all()
        )
        if (
            existing.subject_person_id != command.subject_person_id
            or set(existing_ids) != set(evidence_case_ids)
            or len(existing_ids) != len(evidence_case_ids)
        ):
            raise AppError(
                "PATTERN_IDEMPOTENCY_KEY_REUSED",
                "Idempotency key was already used for a different Evidence set.",
                status_code=409,
            )
        return existing

    _require_create_expected_version(command.expected_version)

    snapshots = await reader.load(
        organization_context_id=command.organization_context_id,
        subject_person_id=command.subject_person_id,
        evidence_case_ids=evidence_case_ids,
    )
    by_id = {item.evidence_case_id: item for item in snapshots}
    missing = [str(item) for item in evidence_case_ids if item not in by_id]
    if missing:
        raise AppError(
            "PATTERN_EVIDENCE_NOT_ACCEPTED",
            "Every Evidence set member must reference accepted Evidence.",
            status_code=422,
            details={"evidence_case_ids": missing},
        )

    ordered = [by_id[item] for item in evidence_case_ids]
    for snapshot in ordered:
        if not _accepted_snapshot_matches_context(
            snapshot,
            organization_context_id=command.organization_context_id,
            subject_person_id=command.subject_person_id,
        ):
            raise AppError(
                "PATTERN_EVIDENCE_NOT_ACCEPTED",
                (
                    "Every Evidence set member must reference accepted Evidence "
                    "with its active accepted Interpretation for the same subject."
                ),
                status_code=422,
            )

    contract = {
        "organization_context_id": str(command.organization_context_id),
        "subject_person_id": str(command.subject_person_id),
        "members": [
            {
                "evidence_case_id": str(item.evidence_case_id),
                "interpretation_id": str(item.interpretation_id),
                "interpretation_version": item.interpretation_version,
                "behaviour_code": item.behaviour_code,
                "signal": item.signal,
                "scope": item.scope,
                "confidence": item.confidence,
                "context_difficulty": item.context_difficulty,
                "prompt_contamination": item.prompt_contamination,
                "source_independence_group": item.source_independence_group,
                "accepted_at": item.accepted_at.isoformat(),
                "target_links": item.target_links,
                "source_lineage": item.source_lineage,
            }
            for item in ordered
        ],
    }
    if not evidence_set_contract_valid(contract):
        raise AppError(
            "PATTERN_EVIDENCE_SET_INVALID",
            "Accepted Evidence snapshot does not satisfy the Pattern lineage contract.",
            status_code=422,
        )

    now = datetime.now(UTC)
    evidence_set = EvidenceSet(
        id=uuid4(),
        evidence_set_key=uuid4(),
        version_number=1,
        organization_context_id=command.organization_context_id,
        subject_person_id=command.subject_person_id,
        created_by=command.created_by,
        idempotency_key=idempotency_key,
        created_at=now,
    )
    db.add(evidence_set)
    await db.flush()

    for item in ordered:
        db.add(
            EvidenceSetMember(
                id=uuid4(),
                evidence_set_id=evidence_set.id,
                evidence_case_id=item.evidence_case_id,
                interpretation_id=item.interpretation_id,
                interpretation_version=item.interpretation_version,
                behaviour_code=item.behaviour_code.strip(),
                signal=item.signal,
                scope=item.scope.strip(),
                confidence=item.confidence,
                context_difficulty=item.context_difficulty.strip(),
                prompt_contamination=item.prompt_contamination.strip(),
                source_independence_group=item.source_independence_group.strip(),
                accepted_at=item.accepted_at,
                target_links=item.target_links,
                source_lineage=item.source_lineage,
                created_at=now,
            )
        )

    record_event(
        db,
        new_event(
            event_type="pattern.evidence_set_created.v1",
            aggregate_type="EvidenceSet",
            aggregate_id=evidence_set.id,
            aggregate_version=evidence_set.version_number,
            actor={"type": "PERSON", "id": str(command.created_by)},
            organization_context_id=command.organization_context_id,
            data_classification="CONFIDENTIAL",
            payload={
                "evidence_set_id": str(evidence_set.id),
                "evidence_set_key": str(evidence_set.evidence_set_key),
                "subject_person_id": str(evidence_set.subject_person_id),
                "evidence_case_ids": [str(item) for item in evidence_case_ids],
            },
            trace_id=command.trace_id,
        ),
    )
    await db.commit()
    return evidence_set

@dataclass(frozen=True)
class PatternCandidateEvidenceInput:
    evidence_set_member_id: UUID
    relationship: str


@dataclass(frozen=True)
class CreatePatternCandidateCommand:
    organization_context_id: UUID
    subject_person_id: UUID
    evidence_set_id: UUID
    behaviour_code: str
    behaviour_description: str
    proposed_pattern_status: str
    scope: str
    rationale: str
    evidence: tuple[PatternCandidateEvidenceInput, ...]
    created_by: UUID
    expected_version: int
    idempotency_key: str
    trace_id: str


def _require_pattern_candidate_create_expected_version(expected_version: int) -> None:
    if expected_version != 0:
        raise AppError(
            "VERSION_CONFLICT",
            "Pattern candidate changed. Refresh and retry.",
            status_code=409,
            details={
                "expected_version": expected_version,
                "current_version": 0,
            },
        )


async def create_pattern_candidate(
    db: AsyncSession,
    *,
    command: CreatePatternCandidateCommand,
) -> PatternCandidate:
    idempotency_key = command.idempotency_key.strip()
    if not idempotency_key:
        raise AppError(
            "PATTERN_IDEMPOTENCY_KEY_REQUIRED",
            "Idempotency key is required.",
            status_code=422,
        )

    existing = (
        await db.execute(
            select(PatternCandidate).where(
                PatternCandidate.organization_context_id
                == command.organization_context_id,
                PatternCandidate.created_by == command.created_by,
                PatternCandidate.idempotency_key == idempotency_key,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        existing_evidence = (
            await db.execute(
                select(
                    PatternCandidateEvidence.evidence_set_member_id,
                    PatternCandidateEvidence.relationship,
                ).where(
                    PatternCandidateEvidence.pattern_candidate_id == existing.id
                )
            )
        ).all()
        existing_relationships = {
            (row.evidence_set_member_id, row.relationship) for row in existing_evidence
        }
        requested_relationships = {
            (item.evidence_set_member_id, item.relationship) for item in command.evidence
        }
        if (
            existing.subject_person_id != command.subject_person_id
            or existing.evidence_set_id != command.evidence_set_id
            or existing.behaviour_code != command.behaviour_code.strip()
            or existing.behaviour_description != command.behaviour_description.strip()
            or existing.proposed_pattern_status != command.proposed_pattern_status
            or existing.scope != command.scope.strip()
            or existing.rationale != command.rationale.strip()
            or existing_relationships != requested_relationships
            or len(existing_evidence) != len(command.evidence)
        ):
            raise AppError(
                "PATTERN_IDEMPOTENCY_KEY_REUSED",
                "Idempotency key was already used for a different Pattern candidate.",
                status_code=409,
            )
        return existing

    _require_pattern_candidate_create_expected_version(command.expected_version)

    contract = {
        "behaviour_code": command.behaviour_code,
        "behaviour_description": command.behaviour_description,
        "proposed_pattern_status": command.proposed_pattern_status,
        "scope": command.scope,
        "rationale": command.rationale,
        "evidence": [
            {
                "evidence_set_member_id": str(item.evidence_set_member_id),
                "relationship": item.relationship,
            }
            for item in command.evidence
        ],
    }
    if not pattern_candidate_contract_valid(contract):
        raise AppError(
            "PATTERN_CANDIDATE_INVALID",
            "Pattern candidate contract is invalid.",
            status_code=422,
        )

    evidence_set = (
        await db.execute(
            select(EvidenceSet)
            .where(
                EvidenceSet.id == command.evidence_set_id,
                EvidenceSet.organization_context_id
                == command.organization_context_id,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if evidence_set is None:
        raise AppError(
            "PATTERN_EVIDENCE_SET_NOT_FOUND",
            "Evidence set not found.",
            status_code=404,
        )
    if evidence_set.subject_person_id != command.subject_person_id:
        raise AppError(
            "PATTERN_EVIDENCE_SET_CONTEXT_MISMATCH",
            "Pattern candidate and Evidence set must have the same organization and subject.",
            status_code=422,
        )

    requested_member_ids = tuple(
        item.evidence_set_member_id for item in command.evidence
    )
    stored_member_ids = set(
        (
            await db.execute(
                select(EvidenceSetMember.id).where(
                    EvidenceSetMember.evidence_set_id == evidence_set.id,
                    EvidenceSetMember.id.in_(requested_member_ids),
                )
            )
        )
        .scalars()
        .all()
    )
    if stored_member_ids != set(requested_member_ids):
        raise AppError(
            "PATTERN_EVIDENCE_SET_MEMBER_INVALID",
            "Pattern candidate evidence must belong to the selected Evidence set.",
            status_code=422,
        )

    now = datetime.now(UTC)
    candidate = PatternCandidate(
        id=uuid4(),
        version=1,
        organization_context_id=command.organization_context_id,
        subject_person_id=command.subject_person_id,
        evidence_set_id=evidence_set.id,
        behaviour_code=command.behaviour_code.strip(),
        behaviour_description=command.behaviour_description.strip(),
        proposed_pattern_status=command.proposed_pattern_status,
        scope=command.scope.strip(),
        rationale=command.rationale.strip(),
        created_by=command.created_by,
        idempotency_key=idempotency_key,
        created_at=now,
        updated_at=now,
    )
    db.add(candidate)
    await db.flush()

    for item in command.evidence:
        db.add(
            PatternCandidateEvidence(
                id=uuid4(),
                pattern_candidate_id=candidate.id,
                evidence_set_member_id=item.evidence_set_member_id,
                relationship=item.relationship,
            )
        )

    record_event(
        db,
        new_event(
            event_type="pattern.pattern_candidate_created.v1",
            aggregate_type="PatternCandidate",
            aggregate_id=candidate.id,
            aggregate_version=candidate.version,
            actor={"type": "PERSON", "id": str(command.created_by)},
            organization_context_id=command.organization_context_id,
            data_classification="CONFIDENTIAL",
            payload={
                "pattern_candidate_id": str(candidate.id),
                "subject_person_id": str(candidate.subject_person_id),
                "evidence_set_id": str(candidate.evidence_set_id),
                "proposed_pattern_status": candidate.proposed_pattern_status,
                "evidence": [
                    {
                        "evidence_set_member_id": str(item.evidence_set_member_id),
                        "relationship": item.relationship,
                    }
                    for item in command.evidence
                ],
            },
            trace_id=command.trace_id,
        ),
    )
    await db.commit()
    return candidate

@dataclass(frozen=True)
class ReviewPatternCandidateCommand:
    organization_context_id: UUID
    pattern_candidate_id: UUID
    reviewer_id: UUID
    resulting_pattern_status: str
    rationale: str
    expected_version: int
    idempotency_key: str
    trace_id: str


def _reviewed_pattern_status_valid(value: str) -> bool:
    return value in {item.value for item in PatternStatus}


def _require_pattern_review_expected_version(
    *,
    current_version: int,
    expected_version: int,
) -> None:
    if current_version != expected_version:
        raise AppError(
            "VERSION_CONFLICT",
            "Pattern candidate changed. Refresh and retry.",
            status_code=409,
            details={
                "expected_version": expected_version,
                "current_version": current_version,
            },
        )


def _new_pattern_updated_event(
    *,
    pattern: BehaviourPattern,
    reviewer_id: UUID,
    trace_id: str,
) -> EventEnvelope:
    return new_event(
        event_type="pattern.updated.v1",
        aggregate_type="BehaviourPattern",
        aggregate_id=pattern.id,
        aggregate_version=pattern.version,
        actor={"type": "PERSON", "id": str(reviewer_id)},
        organization_context_id=pattern.organization_context_id,
        data_classification="CONFIDENTIAL",
        payload={
            "pattern_id": str(pattern.id),
            "source_pattern_candidate_id": str(pattern.source_pattern_candidate_id),
            "subject_person_id": str(pattern.subject_person_id),
            "evidence_set_id": str(pattern.evidence_set_id),
            "pattern_status": pattern.pattern_status,
            "behaviour_code": pattern.behaviour_code,
            "scope": pattern.scope,
        },
        trace_id=trace_id,
    )


async def review_pattern_candidate(
    db: AsyncSession,
    *,
    command: ReviewPatternCandidateCommand,
) -> BehaviourPattern:
    idempotency_key = command.idempotency_key.strip()
    if not idempotency_key:
        raise AppError(
            "PATTERN_IDEMPOTENCY_KEY_REQUIRED",
            "Idempotency key is required.",
            status_code=422,
        )

    rationale = command.rationale.strip()
    if not rationale:
        raise AppError(
            "PATTERN_REVIEW_RATIONALE_REQUIRED",
            "Human review rationale is required.",
            status_code=422,
        )
    if not _reviewed_pattern_status_valid(command.resulting_pattern_status):
        raise AppError(
            "PATTERN_STATUS_INVALID",
            "Reviewed Pattern status is not part of the DEC-401 vocabulary.",
            status_code=422,
        )

    existing_review = (
        await db.execute(
            select(PatternReview).where(
                PatternReview.pattern_candidate_id == command.pattern_candidate_id,
                PatternReview.reviewer_id == command.reviewer_id,
                PatternReview.idempotency_key == idempotency_key,
            )
        )
    ).scalar_one_or_none()
    if existing_review is not None:
        resulting_pattern = (
            await db.execute(
                select(BehaviourPattern).where(
                    BehaviourPattern.id == existing_review.resulting_pattern_id
                )
            )
        ).scalar_one_or_none()
        if (
            resulting_pattern is None
            or resulting_pattern.organization_context_id
            != command.organization_context_id
            or existing_review.resulting_pattern_status
            != command.resulting_pattern_status
            or existing_review.rationale != rationale
        ):
            raise AppError(
                "PATTERN_IDEMPOTENCY_KEY_REUSED",
                "Idempotency key was already used for a different Pattern review.",
                status_code=409,
            )
        return resulting_pattern

    candidate = (
        await db.execute(
            select(PatternCandidate)
            .where(
                PatternCandidate.id == command.pattern_candidate_id,
                PatternCandidate.organization_context_id
                == command.organization_context_id,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if candidate is None:
        raise AppError(
            "PATTERN_CANDIDATE_NOT_FOUND",
            "Pattern candidate not found.",
            status_code=404,
        )

    _require_pattern_review_expected_version(
        current_version=candidate.version,
        expected_version=command.expected_version,
    )

    existing_pattern = (
        await db.execute(
            select(BehaviourPattern).where(
                BehaviourPattern.source_pattern_candidate_id == candidate.id
            )
        )
    ).scalar_one_or_none()
    if existing_pattern is not None:
        raise AppError(
            "PATTERN_CANDIDATE_ALREADY_REVIEWED",
            "Pattern candidate already has a reviewed Behaviour Pattern.",
            status_code=409,
        )

    now = datetime.now(UTC)
    pattern = BehaviourPattern(
        id=uuid4(),
        version=1,
        organization_context_id=candidate.organization_context_id,
        subject_person_id=candidate.subject_person_id,
        source_pattern_candidate_id=candidate.id,
        evidence_set_id=candidate.evidence_set_id,
        behaviour_code=candidate.behaviour_code,
        behaviour_description=candidate.behaviour_description,
        pattern_status=command.resulting_pattern_status,
        scope=candidate.scope,
        rationale=rationale,
        reviewed_by=command.reviewer_id,
        reviewed_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(pattern)

    db.add(
        PatternReview(
            id=uuid4(),
            pattern_candidate_id=candidate.id,
            reviewer_id=command.reviewer_id,
            resulting_pattern_status=command.resulting_pattern_status,
            rationale=rationale,
            resulting_pattern_id=pattern.id,
            idempotency_key=idempotency_key,
            created_at=now,
        )
    )

    candidate.version += 1
    candidate.updated_at = now

    record_event(
        db,
        _new_pattern_updated_event(
            pattern=pattern,
            reviewer_id=command.reviewer_id,
            trace_id=command.trace_id,
        ),
    )

    await db.commit()
    return pattern

