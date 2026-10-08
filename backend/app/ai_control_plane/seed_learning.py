from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import AppError
from app.platform.events import new_event, record_event
from app.platform.models import DomainEvent

SEED_KEY = "decision-making-v1"
SEED_SOURCE_REFERENCE = "docs/ai/seed/decision-making-v1.jsonl"
SEED_SOURCE_VERSION = "1"
SEED_DATASET_NAME = "parcham-decision-making"
SEED_DATASET_PURPOSE = "MODEL_TRAINING"
SEED_SOURCE_POLICY_KEY = "parcham-curated-synthetic-seed"
SEED_SOURCE_POLICY_VERSION = "v1"
SEED_SOURCE_TYPE = "CURATED_SYNTHETIC_SEED"
SEED_DATA_CLASSIFICATION = "INTERNAL"
APPROVED_INPUT_EVENT = "ai.learning_input_approved.v1"
APPROVAL_AGGREGATE_TYPE = "AISeedLearningApproval"

_SEED_PATH = Path(__file__).with_name("seeds") / "decision-making-v1.jsonl"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class DecisionSeedArtifact:
    key: str
    source_reference: str
    source_version: str
    source_payload_digest: str
    record_count: int
    dataset_name: str
    purpose: str
    source_policy_key: str
    source_policy_version: str
    source_type: str
    data_classification: str


@dataclass(frozen=True)
class ApproveDecisionSeedLearning:
    organization_context_id: UUID
    reviewer_id: UUID
    expected_source_payload_digest: str
    approval_reference: str
    trace_id: str


@dataclass(frozen=True)
class SeedLearningApprovalResult:
    approval_event_id: UUID
    source_payload_digest: str
    record_count: int
    dataset_name: str
    purpose: str
    source_reference: str
    source_version: str
    approval_reference: str
    reviewer_id: UUID
    created: bool


def _required_text(value: str, field: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise AppError(
            "AI_SEED_LEARNING_INPUT_INVALID",
            f"{field} is required.",
            status_code=422,
            details={"field": field},
        )
    return normalized


def _expected_digest(value: str) -> str:
    normalized = _required_text(
        value,
        "expected_source_payload_digest",
    ).lower()
    if not _SHA256_RE.fullmatch(normalized):
        raise AppError(
            "AI_SEED_LEARNING_INPUT_INVALID",
            "expected_source_payload_digest must be a lowercase SHA-256 digest.",
            status_code=422,
            details={"field": "expected_source_payload_digest"},
        )
    return normalized


def load_decision_seed_artifact() -> DecisionSeedArtifact:
    try:
        raw = _SEED_PATH.read_bytes()
    except OSError as exc:
        raise AppError(
            "AI_SEED_ARTIFACT_UNAVAILABLE",
            "Decision-Making Seed artifact is unavailable.",
            status_code=503,
        ) from exc

    try:
        decoded = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise AppError(
            "AI_SEED_ARTIFACT_INVALID",
            "Decision-Making Seed artifact must be valid UTF-8.",
            status_code=500,
        ) from exc

    records: list[dict] = []
    ids: set[str] = set()
    for line_number, line in enumerate(decoded.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise AppError(
                "AI_SEED_ARTIFACT_INVALID",
                "Decision-Making Seed artifact contains invalid JSONL.",
                status_code=500,
                details={"line": line_number},
            ) from exc

        if not isinstance(item, dict):
            raise AppError(
                "AI_SEED_ARTIFACT_INVALID",
                "Decision-Making Seed records must be JSON objects.",
                status_code=500,
                details={"line": line_number},
            )

        seed_id = item.get("id")
        if not isinstance(seed_id, str) or not seed_id.strip():
            raise AppError(
                "AI_SEED_ARTIFACT_INVALID",
                "Decision-Making Seed record id is required.",
                status_code=500,
                details={"line": line_number},
            )
        if seed_id in ids:
            raise AppError(
                "AI_SEED_ARTIFACT_INVALID",
                "Decision-Making Seed record ids must be unique.",
                status_code=500,
                details={"id": seed_id},
            )
        if item.get("synthetic") is not True:
            raise AppError(
                "AI_SEED_ARTIFACT_INVALID",
                "Decision-Making Seed records must be explicitly synthetic.",
                status_code=500,
                details={"id": seed_id},
            )
        if item.get("capability") != "Decision Making":
            raise AppError(
                "AI_SEED_ARTIFACT_INVALID",
                "Decision-Making Seed contains an unexpected Capability.",
                status_code=500,
                details={"id": seed_id},
            )
        source_refs = item.get("source_refs")
        if not isinstance(source_refs, list) or not source_refs:
            raise AppError(
                "AI_SEED_ARTIFACT_INVALID",
                "Decision-Making Seed record source_refs are required.",
                status_code=500,
                details={"id": seed_id},
            )

        ids.add(seed_id)
        records.append(item)

    if not records:
        raise AppError(
            "AI_SEED_ARTIFACT_INVALID",
            "Decision-Making Seed artifact must not be empty.",
            status_code=500,
        )

    return DecisionSeedArtifact(
        key=SEED_KEY,
        source_reference=SEED_SOURCE_REFERENCE,
        source_version=SEED_SOURCE_VERSION,
        source_payload_digest=hashlib.sha256(raw).hexdigest(),
        record_count=len(records),
        dataset_name=SEED_DATASET_NAME,
        purpose=SEED_DATASET_PURPOSE,
        source_policy_key=SEED_SOURCE_POLICY_KEY,
        source_policy_version=SEED_SOURCE_POLICY_VERSION,
        source_type=SEED_SOURCE_TYPE,
        data_classification=SEED_DATA_CLASSIFICATION,
    )


def seed_approval_aggregate_id(
    organization_context_id: UUID,
) -> UUID:
    return uuid5(
        NAMESPACE_URL,
        (
            "urn:parcham:ai:seed-learning-approval:"
            f"{organization_context_id}:{SEED_KEY}:{SEED_SOURCE_VERSION}"
        ),
    )


def _approval_lock_key(
    organization_context_id: UUID,
) -> int:
    identity = (
        f"{organization_context_id}:{SEED_KEY}:{SEED_SOURCE_VERSION}".encode()
    )
    raw = hashlib.sha256(identity).digest()[:8]
    return int.from_bytes(raw, byteorder="big", signed=True)


async def get_existing_seed_learning_approval(
    db: AsyncSession,
    *,
    organization_context_id: UUID,
) -> DomainEvent | None:
    return (
        await db.execute(
            select(DomainEvent).where(
                DomainEvent.event_type == APPROVED_INPUT_EVENT,
                DomainEvent.aggregate_type == APPROVAL_AGGREGATE_TYPE,
                DomainEvent.aggregate_id
                == seed_approval_aggregate_id(organization_context_id),
                DomainEvent.organization_context_id
                == organization_context_id,
            )
        )
    ).scalar_one_or_none()


def _result_from_event(
    event: DomainEvent,
    *,
    artifact: DecisionSeedArtifact,
    created: bool,
) -> SeedLearningApprovalResult:
    actor_id = event.actor.get("id")
    try:
        reviewer_id = UUID(str(actor_id))
    except (TypeError, ValueError) as exc:
        raise AppError(
            "AI_SEED_APPROVAL_LINEAGE_INVALID",
            "Seed approval has invalid Human reviewer lineage.",
            status_code=409,
        ) from exc

    return SeedLearningApprovalResult(
        approval_event_id=event.event_id,
        source_payload_digest=artifact.source_payload_digest,
        record_count=artifact.record_count,
        dataset_name=artifact.dataset_name,
        purpose=artifact.purpose,
        source_reference=artifact.source_reference,
        source_version=artifact.source_version,
        approval_reference=str(event.payload["approval_reference"]),
        reviewer_id=reviewer_id,
        created=created,
    )


async def approve_decision_seed_learning(
    db: AsyncSession,
    *,
    command: ApproveDecisionSeedLearning,
) -> SeedLearningApprovalResult:
    artifact = load_decision_seed_artifact()
    expected_digest = _expected_digest(
        command.expected_source_payload_digest
    )
    if expected_digest != artifact.source_payload_digest:
        raise AppError(
            "AI_SEED_DIGEST_MISMATCH",
            (
                "Decision-Making Seed changed since it was reviewed. "
                "Reload the Seed preview before approval."
            ),
            status_code=409,
            details={
                "current_source_payload_digest":
                    artifact.source_payload_digest,
            },
        )

    approval_reference = _required_text(
        command.approval_reference,
        "approval_reference",
    )
    if len(approval_reference) > 255:
        raise AppError(
            "AI_SEED_LEARNING_INPUT_INVALID",
            "approval_reference must be at most 255 characters.",
            status_code=422,
            details={"field": "approval_reference"},
        )
    trace_id = _required_text(command.trace_id, "trace_id")

    await db.execute(
        text("SELECT pg_advisory_xact_lock(:lock_key)"),
        {"lock_key": _approval_lock_key(command.organization_context_id)},
    )

    existing = await get_existing_seed_learning_approval(
        db,
        organization_context_id=command.organization_context_id,
    )
    if existing is not None:
        exact_retry = (
            existing.actor.get("type") == "PERSON"
            and existing.actor.get("id") == str(command.reviewer_id)
            and existing.payload.get("approval_reference")
            == approval_reference
            and existing.payload.get("source_payload_digest")
            == artifact.source_payload_digest
            and existing.payload.get("source_reference")
            == artifact.source_reference
            and existing.payload.get("source_version")
            == artifact.source_version
        )
        if not exact_retry:
            raise AppError(
                "AI_SEED_LEARNING_APPROVAL_CONFLICT",
                (
                    "This Seed version already has a different Human "
                    "AI-learning approval."
                ),
                status_code=409,
                details={
                    "approval_event_id": str(existing.event_id),
                },
            )
        return _result_from_event(
            existing,
            artifact=artifact,
            created=False,
        )

    envelope = new_event(
        event_type=APPROVED_INPUT_EVENT,
        aggregate_type=APPROVAL_AGGREGATE_TYPE,
        aggregate_id=seed_approval_aggregate_id(
            command.organization_context_id
        ),
        aggregate_version=1,
        actor={"type": "PERSON", "id": str(command.reviewer_id)},
        organization_context_id=command.organization_context_id,
        data_classification=artifact.data_classification,
        payload={
            "seed_key": artifact.key,
            "dataset_name": artifact.dataset_name,
            "purpose": artifact.purpose,
            "source_policy_key": artifact.source_policy_key,
            "source_policy_version": artifact.source_policy_version,
            "source_type": artifact.source_type,
            "source_reference": artifact.source_reference,
            "source_version": artifact.source_version,
            "source_payload_digest": artifact.source_payload_digest,
            "approval_reference": approval_reference,
            "record_count": artifact.record_count,
        },
        trace_id=trace_id,
    )
    record_event(db, envelope)

    return SeedLearningApprovalResult(
        approval_event_id=envelope.event_id,
        source_payload_digest=artifact.source_payload_digest,
        record_count=artifact.record_count,
        dataset_name=artifact.dataset_name,
        purpose=artifact.purpose,
        source_reference=artifact.source_reference,
        source_version=artifact.source_version,
        approval_reference=approval_reference,
        reviewer_id=command.reviewer_id,
        created=True,
    )
