from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import AppError
from app.patterns.domain import evidence_set_contract_valid
from app.patterns.models import EvidenceSet, EvidenceSetMember
from app.platform.events import new_event, record_event


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
