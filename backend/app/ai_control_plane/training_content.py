"""Read-only, offline materialization of governed Training Dataset content.

Only the first-party, human-approved Decision-Making Seed has a resolver.
Unknown source types are deliberately not materialized. This is not a Trainer,
a public route, model activation, or permission to use unreviewed data.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Never
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_control_plane.dataset_builder import (
    ApprovedLearningInput,
    approval_provenance_digest,
    dataset_version_digest,
)
from app.ai_control_plane.domain import TrainingRunState
from app.ai_control_plane.models import (
    AIDataset,
    AIDatasetItem,
    AIDatasetVersion,
    AILearningSourceApproval,
    AITrainingRun,
    AITrainingRunState,
)
from app.ai_control_plane.seed_learning import (
    APPROVAL_AGGREGATE_TYPE,
    APPROVED_INPUT_EVENT,
    load_decision_seed_artifact,
    seed_approval_aggregate_id,
)
from app.errors import AppError
from app.platform.models import DomainEvent

_MODEL_FAMILY = "Gemma 4 12B Unified"
_SEED_BYTES = Path(__file__).with_name("seeds") / "decision-making-v1.jsonl"


@dataclass(frozen=True)
class ApprovedTrainingContent:
    dataset_item_id: UUID
    approval_event_id: UUID
    source_payload_digest: str
    provenance_digest: str
    content: bytes


@dataclass(frozen=True)
class AttestedTrainingDataset:
    training_run_id: UUID
    dataset_version_id: UUID
    dataset_digest: str
    items: tuple[ApprovedTrainingContent, ...]


def _deny(message: str) -> Never:
    raise AppError("AI_TRAINING_CONTENT_NOT_VERIFIED", message, status_code=409)


async def materialize_training_dataset(
    db: AsyncSession,
    *,
    organization_context_id: UUID,
    training_run_id: UUID,
) -> AttestedTrainingDataset:
    """Read a RUNNING run's approved source bytes, with exact tenant/lineage checks.

    Never accepts a caller-provided file path or an unregistered input.
    Source bytes are returned in-memory for a future, separately authorized Trainer.
    """
    run = (
        await db.execute(
            select(AITrainingRun).where(
                AITrainingRun.id == training_run_id,
                AITrainingRun.organization_context_id == organization_context_id,
            )
        )
    ).scalar_one_or_none()
    if run is None:
        _deny("Training Run is absent from this organization.")
    if run.model_family != _MODEL_FAMILY:
        _deny("This offline content adapter is only for the governed Gemma family.")

    state = (
        await db.execute(
            select(AITrainingRunState)
            .where(AITrainingRunState.training_run_id == run.id)
            .order_by(AITrainingRunState.sequence.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if state is None or state.state != TrainingRunState.RUNNING.value:
        _deny("Only RUNNING Training Runs may materialize training content.")

    dataset = (
        await db.execute(
            select(AIDataset)
            .join(AIDatasetVersion, AIDatasetVersion.dataset_id == AIDataset.id)
            .where(
                AIDatasetVersion.id == run.dataset_version_id,
                AIDataset.organization_context_id == organization_context_id,
            )
        )
    ).scalar_one_or_none()
    if dataset is None or dataset.purpose != "MODEL_TRAINING":
        _deny("Training Dataset is missing, cross-tenant or wrong-purpose.")

    versions: list[AIDatasetVersion] = []
    seen: set[UUID] = set()
    next_id: UUID | None = run.dataset_version_id
    while next_id is not None:
        if next_id in seen or len(versions) >= 256:
            _deny("Dataset Version ancestry is cyclic or unbounded.")
        seen.add(next_id)
        version = (
            await db.execute(
                select(AIDatasetVersion).where(
                    AIDatasetVersion.id == next_id,
                    AIDatasetVersion.dataset_id == dataset.id,
                )
            )
        ).scalar_one_or_none()
        if version is None:
            _deny("Dataset Version ancestry has missing or cross-dataset links.")
        versions.append(version)
        next_id = version.parent_dataset_version_id
    versions.reverse()

    previous_digest: str | None = None
    contents: list[ApprovedTrainingContent] = []
    for number, version in enumerate(versions, start=1):
        if version.version_number != number:
            _deny("Dataset Version sequence is inconsistent.")
        items = (
            await db.execute(
                select(AIDatasetItem).where(
                    AIDatasetItem.dataset_version_id == version.id
                )
            )
        ).scalars().all()
        # Existing Dataset Builder produces one append-only delta per version.
        if len(items) != 1 or items[0].position != 1:
            _deny("Dataset Version has an unsupported item layout.")
        item = items[0]
        approval = (
            await db.execute(
                select(AILearningSourceApproval).where(
                    AILearningSourceApproval.id == item.learning_source_approval_id,
                    AILearningSourceApproval.dataset_id == dataset.id,
                )
            )
        ).scalar_one_or_none()
        if approval is None:
            _deny("Dataset item has no governed approval.")
        event = (
            await db.execute(
                select(DomainEvent).where(
                    DomainEvent.event_id == approval.approval_event_id,
                    DomainEvent.organization_context_id == organization_context_id,
                    DomainEvent.event_type == APPROVED_INPUT_EVENT,
                )
            )
        ).scalar_one_or_none()
        if event is None or event.actor.get("type") != "PERSON":
            _deny("Original human approval event is missing.")
        if (
            approval.approved_by_type != "PERSON"
            or approval.approved_by_reference != event.actor.get("id")
            or approval.approved_at != event.occurred_at
            or approval.approval_reference != event.payload.get("approval_reference")
            or event.aggregate_type != APPROVAL_AGGREGATE_TYPE
            or event.aggregate_id != seed_approval_aggregate_id(organization_context_id)
            or event.data_classification != approval.data_classification
            or item.approval_reference != approval.approval_reference
            or item.source_type != approval.source_type
            or item.source_reference != approval.source_reference
            or item.source_version != approval.source_version
            or item.data_classification != approval.data_classification
            or item.source_payload_digest != approval.source_payload_digest
        ):
            _deny("Dataset approval and item lineage differ.")

        seed = load_decision_seed_artifact()
        approved_fields = {
            "dataset_name": dataset.name,
            "purpose": dataset.purpose,
            "source_policy_key": approval.source_policy_key,
            "source_policy_version": approval.source_policy_version,
            "source_type": approval.source_type,
            "source_reference": approval.source_reference,
            "source_version": approval.source_version,
            "source_payload_digest": approval.source_payload_digest,
        }
        canonical_fields = {
            "dataset_name": seed.dataset_name,
            "purpose": seed.purpose,
            "source_policy_key": seed.source_policy_key,
            "source_policy_version": seed.source_policy_version,
            "source_type": seed.source_type,
            "source_reference": seed.source_reference,
            "source_version": seed.source_version,
            "source_payload_digest": seed.source_payload_digest,
        }
        if (
            approved_fields != canonical_fields
            or any(event.payload.get(key) != value for key, value in approved_fields.items())
            or version.source_policy_key != approval.source_policy_key
            or version.source_policy_version != approval.source_policy_version
            or approval.data_classification != seed.data_classification
        ):
            _deny("Source is unsupported, unapproved or its canonical bytes changed.")
        provenance = approval_provenance_digest(
            ApprovedLearningInput(
                organization_context_id=organization_context_id,
                dataset_name=dataset.name,
                purpose=dataset.purpose,
                source_policy_key=approval.source_policy_key,
                source_policy_version=approval.source_policy_version,
                source_type=approval.source_type,
                source_reference=approval.source_reference,
                source_version=approval.source_version,
                source_payload_digest=approval.source_payload_digest,
                approval_reference=approval.approval_reference,
                approval_event_id=approval.approval_event_id,
                data_classification=approval.data_classification,
                approved_by_type=approval.approved_by_type,
                approved_by_reference=approval.approved_by_reference,
                approved_at=approval.approved_at,
                trace_id=event.trace_id,
            )
        )
        if provenance != approval.provenance_digest or provenance != item.provenance_digest:
            _deny("Dataset item provenance digest is invalid.")
        calculated = dataset_version_digest(
            organization_context_id=organization_context_id,
            dataset_name=dataset.name,
            purpose=dataset.purpose,
            parent_dataset_digest=previous_digest,
            provenance_digest=provenance,
        )
        if calculated != version.dataset_digest:
            _deny("Dataset Version digest does not match its approved ancestry.")
        try:
            raw = _SEED_BYTES.read_bytes()
        except OSError as exc:
            raise AppError(
                "AI_TRAINING_CONTENT_NOT_VERIFIED",
                "Approved source bytes are unavailable.",
                status_code=409,
            ) from exc
        if hashlib.sha256(raw).hexdigest() != approval.source_payload_digest:
            _deny("Approved source bytes differ from their immutable SHA-256.")
        contents.append(
            ApprovedTrainingContent(
                dataset_item_id=item.id,
                approval_event_id=event.event_id,
                source_payload_digest=approval.source_payload_digest,
                provenance_digest=provenance,
                content=raw,
            )
        )
        previous_digest = calculated
    if previous_digest is None:
        _deny("Training Dataset has no approved content.")
    return AttestedTrainingDataset(
        training_run_id=run.id,
        dataset_version_id=run.dataset_version_id,
        dataset_digest=previous_digest,
        items=tuple(contents),
    )
