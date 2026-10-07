from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_control_plane.domain import GovernanceActorType
from app.ai_control_plane.models import (
    AIDataset,
    AIDatasetItem,
    AIDatasetVersion,
    AILearningSourceApproval,
)
from app.errors import AppError
from app.platform.events import new_event, record_event

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class ApprovedLearningInput:
    organization_context_id: UUID
    dataset_name: str
    purpose: str
    source_policy_key: str
    source_policy_version: str
    source_type: str
    source_reference: str
    source_version: str | None
    source_payload_digest: str
    approval_reference: str
    data_classification: str
    approved_by_type: str
    approved_by_reference: str
    approved_at: datetime
    trace_id: str


@dataclass(frozen=True)
class DatasetBuildResult:
    dataset_id: UUID
    dataset_version_id: UUID
    version_number: int
    dataset_digest: str
    learning_source_approval_id: UUID
    created: bool


def _required_text(value: str, field: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise AppError(
            "AI_DATASET_INPUT_INVALID",
            f"{field} is required.",
            status_code=422,
            details={"field": field},
        )
    return normalized


def _sha256(value: str, field: str) -> str:
    normalized = value.strip().lower()
    if not _SHA256_RE.fullmatch(normalized):
        raise AppError(
            "AI_DATASET_INPUT_INVALID",
            f"{field} must be a lowercase SHA-256 digest.",
            status_code=422,
            details={"field": field},
        )
    return normalized


def _approved_at(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise AppError(
            "AI_DATASET_INPUT_INVALID",
            "approved_at must be timezone-aware.",
            status_code=422,
            details={"field": "approved_at"},
        )
    return value.astimezone(UTC)


def _normalize(command: ApprovedLearningInput) -> ApprovedLearningInput:
    actor_type = _required_text(command.approved_by_type, "approved_by_type")
    if actor_type not in {item.value for item in GovernanceActorType}:
        raise AppError(
            "AI_DATASET_INPUT_INVALID",
            "approved_by_type must be PERSON or SYSTEM.",
            status_code=422,
            details={"field": "approved_by_type"},
        )

    source_version = (
        command.source_version.strip()
        if command.source_version is not None and command.source_version.strip()
        else None
    )
    return ApprovedLearningInput(
        organization_context_id=command.organization_context_id,
        dataset_name=_required_text(command.dataset_name, "dataset_name"),
        purpose=_required_text(command.purpose, "purpose"),
        source_policy_key=_required_text(
            command.source_policy_key,
            "source_policy_key",
        ),
        source_policy_version=_required_text(
            command.source_policy_version,
            "source_policy_version",
        ),
        source_type=_required_text(command.source_type, "source_type"),
        source_reference=_required_text(
            command.source_reference,
            "source_reference",
        ),
        source_version=source_version,
        source_payload_digest=_sha256(
            command.source_payload_digest,
            "source_payload_digest",
        ),
        approval_reference=_required_text(
            command.approval_reference,
            "approval_reference",
        ),
        data_classification=_required_text(
            command.data_classification,
            "data_classification",
        ),
        approved_by_type=actor_type,
        approved_by_reference=_required_text(
            command.approved_by_reference,
            "approved_by_reference",
        ),
        approved_at=_approved_at(command.approved_at),
        trace_id=_required_text(command.trace_id, "trace_id"),
    )


def _canonical_digest(payload: dict) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def approval_provenance_digest(command: ApprovedLearningInput) -> str:
    normalized = _normalize(command)
    return _canonical_digest(
        {
            "organization_context_id": str(normalized.organization_context_id),
            "dataset_name": normalized.dataset_name,
            "purpose": normalized.purpose,
            "source_policy_key": normalized.source_policy_key,
            "source_policy_version": normalized.source_policy_version,
            "source_type": normalized.source_type,
            "source_reference": normalized.source_reference,
            "source_version": normalized.source_version,
            "source_payload_digest": normalized.source_payload_digest,
            "data_classification": normalized.data_classification,
        }
    )


def dataset_version_digest(
    *,
    organization_context_id: UUID,
    dataset_name: str,
    purpose: str,
    parent_dataset_digest: str | None,
    provenance_digest: str,
) -> str:
    return _canonical_digest(
        {
            "organization_context_id": str(organization_context_id),
            "dataset_name": dataset_name,
            "purpose": purpose,
            "parent_dataset_digest": parent_dataset_digest,
            "delta_provenance_digests": [provenance_digest],
        }
    )


def _dataset_lock_key(
    *,
    organization_context_id: UUID,
    dataset_name: str,
    purpose: str,
) -> int:
    identity = (
        f"{organization_context_id}:{dataset_name}:{purpose}".encode("utf-8")
    )
    raw = hashlib.sha256(identity).digest()[:8]
    return int.from_bytes(raw, byteorder="big", signed=True)


async def _result_for_approval(
    db: AsyncSession,
    *,
    approval: AILearningSourceApproval,
    created: bool,
) -> DatasetBuildResult:
    item = (
        await db.execute(
            select(AIDatasetItem).where(
                AIDatasetItem.learning_source_approval_id == approval.id
            )
        )
    ).scalar_one_or_none()
    if item is None:
        raise AppError(
            "AI_DATASET_LINEAGE_INCOMPLETE",
            "Approved learning input has no Dataset Version lineage.",
            status_code=409,
            details={"learning_source_approval_id": str(approval.id)},
        )

    version = (
        await db.execute(
            select(AIDatasetVersion).where(
                AIDatasetVersion.id == item.dataset_version_id,
                AIDatasetVersion.dataset_id == approval.dataset_id,
            )
        )
    ).scalar_one_or_none()
    if version is None:
        raise AppError(
            "AI_DATASET_LINEAGE_INCOMPLETE",
            "Dataset item has no immutable Dataset Version.",
            status_code=409,
            details={"dataset_item_id": str(item.id)},
        )

    return DatasetBuildResult(
        dataset_id=approval.dataset_id,
        dataset_version_id=version.id,
        version_number=version.version_number,
        dataset_digest=version.dataset_digest,
        learning_source_approval_id=approval.id,
        created=created,
    )


async def ingest_approved_learning_input(
    db: AsyncSession,
    *,
    command: ApprovedLearningInput,
) -> DatasetBuildResult:
    normalized = _normalize(command)
    provenance_digest = approval_provenance_digest(normalized)

    await db.execute(
        text("SELECT pg_advisory_xact_lock(:lock_key)"),
        {
            "lock_key": _dataset_lock_key(
                organization_context_id=normalized.organization_context_id,
                dataset_name=normalized.dataset_name,
                purpose=normalized.purpose,
            )
        },
    )

    dataset = (
        await db.execute(
            select(AIDataset).where(
                AIDataset.organization_context_id
                == normalized.organization_context_id,
                AIDataset.name == normalized.dataset_name,
                AIDataset.purpose == normalized.purpose,
            )
        )
    ).scalar_one_or_none()

    now = datetime.now(UTC)
    if dataset is None:
        dataset = AIDataset(
            id=uuid4(),
            organization_context_id=normalized.organization_context_id,
            name=normalized.dataset_name,
            purpose=normalized.purpose,
            created_at=now,
        )
        db.add(dataset)
        await db.flush()

    existing_by_reference = (
        await db.execute(
            select(AILearningSourceApproval).where(
                AILearningSourceApproval.dataset_id == dataset.id,
                AILearningSourceApproval.approval_reference
                == normalized.approval_reference,
            )
        )
    ).scalar_one_or_none()
    if existing_by_reference is not None:
        if existing_by_reference.provenance_digest != provenance_digest:
            raise AppError(
                "AI_LEARNING_APPROVAL_REFERENCE_REUSED",
                (
                    "Approval reference was already used for a different "
                    "governed learning input."
                ),
                status_code=409,
                details={
                    "approval_reference": normalized.approval_reference,
                },
            )
        result = await _result_for_approval(
            db,
            approval=existing_by_reference,
            created=False,
        )
        await db.commit()
        return result

    existing_by_provenance = (
        await db.execute(
            select(AILearningSourceApproval).where(
                AILearningSourceApproval.dataset_id == dataset.id,
                AILearningSourceApproval.provenance_digest
                == provenance_digest,
            )
        )
    ).scalar_one_or_none()
    if existing_by_provenance is not None:
        result = await _result_for_approval(
            db,
            approval=existing_by_provenance,
            created=False,
        )
        await db.commit()
        return result

    approval = AILearningSourceApproval(
        id=uuid4(),
        dataset_id=dataset.id,
        source_policy_key=normalized.source_policy_key,
        source_policy_version=normalized.source_policy_version,
        source_type=normalized.source_type,
        source_reference=normalized.source_reference,
        source_version=normalized.source_version,
        source_payload_digest=normalized.source_payload_digest,
        approval_reference=normalized.approval_reference,
        data_classification=normalized.data_classification,
        provenance_digest=provenance_digest,
        approved_by_type=normalized.approved_by_type,
        approved_by_reference=normalized.approved_by_reference,
        approved_at=normalized.approved_at,
        created_at=now,
    )
    db.add(approval)
    await db.flush()

    parent = (
        await db.execute(
            select(AIDatasetVersion)
            .where(AIDatasetVersion.dataset_id == dataset.id)
            .order_by(AIDatasetVersion.version_number.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    version_number = 1 if parent is None else parent.version_number + 1
    digest = dataset_version_digest(
        organization_context_id=normalized.organization_context_id,
        dataset_name=normalized.dataset_name,
        purpose=normalized.purpose,
        parent_dataset_digest=(
            None if parent is None else parent.dataset_digest
        ),
        provenance_digest=provenance_digest,
    )

    version = AIDatasetVersion(
        id=uuid4(),
        dataset_id=dataset.id,
        parent_dataset_version_id=None if parent is None else parent.id,
        version_number=version_number,
        source_policy_key=normalized.source_policy_key,
        source_policy_version=normalized.source_policy_version,
        dataset_digest=digest,
        created_at=now,
    )
    db.add(version)
    await db.flush()

    db.add(
        AIDatasetItem(
            id=uuid4(),
            dataset_version_id=version.id,
            learning_source_approval_id=approval.id,
            position=1,
            source_type=normalized.source_type,
            source_reference=normalized.source_reference,
            source_version=normalized.source_version,
            approval_reference=normalized.approval_reference,
            data_classification=normalized.data_classification,
            source_payload_digest=normalized.source_payload_digest,
            provenance_digest=provenance_digest,
        )
    )

    record_event(
        db,
        new_event(
            event_type="ai.dataset_version_created.v1",
            aggregate_type="AIDatasetVersion",
            aggregate_id=version.id,
            aggregate_version=version.version_number,
            actor={
                "type": normalized.approved_by_type,
                "id": normalized.approved_by_reference,
            },
            organization_context_id=normalized.organization_context_id,
            data_classification=normalized.data_classification,
            payload={
                "dataset_id": str(dataset.id),
                "dataset_version_id": str(version.id),
                "version_number": version.version_number,
                "parent_dataset_version_id": (
                    None if parent is None else str(parent.id)
                ),
                "dataset_digest": version.dataset_digest,
                "source_policy_key": normalized.source_policy_key,
                "source_policy_version": normalized.source_policy_version,
                "source_type": normalized.source_type,
                "source_reference": normalized.source_reference,
                "source_version": normalized.source_version,
                "source_payload_digest": normalized.source_payload_digest,
                "approval_reference": normalized.approval_reference,
                "provenance_digest": provenance_digest,
            },
            trace_id=normalized.trace_id,
        ),
    )
    await db.commit()

    return DatasetBuildResult(
        dataset_id=dataset.id,
        dataset_version_id=version.id,
        version_number=version.version_number,
        dataset_digest=version.dataset_digest,
        learning_source_approval_id=approval.id,
        created=True,
    )
