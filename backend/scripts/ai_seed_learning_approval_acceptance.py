from __future__ import annotations

import asyncio
from uuid import UUID

from sqlalchemy import func, select

from app.ai_control_plane.models import (
    AIDataset,
    AIDatasetItem,
    AIDatasetVersion,
    AILearningSourceApproval,
)
from app.ai_control_plane.seed_learning import (
    ApproveDecisionSeedLearning,
    approve_decision_seed_learning,
    load_decision_seed_artifact,
)
from app.db import SessionFactory
from app.platform.models import DomainEvent

ORGANIZATION_CONTEXT_ID = UUID(
    "31000000-0000-0000-0000-000000000001"
)
REVIEWER_ID = UUID(
    "31000000-0000-0000-0000-000000000002"
)
APPROVAL_REFERENCE = "ci-decision-seed-human-approval-v1"


async def _approve() -> tuple[str, str]:
    artifact = load_decision_seed_artifact()

    async with SessionFactory() as db:
        first = await approve_decision_seed_learning(
            db,
            command=ApproveDecisionSeedLearning(
                organization_context_id=ORGANIZATION_CONTEXT_ID,
                reviewer_id=REVIEWER_ID,
                expected_source_payload_digest=(
                    artifact.source_payload_digest
                ),
                approval_reference=APPROVAL_REFERENCE,
                trace_id="ci-decision-seed-approval",
            ),
        )
        await db.commit()

    async with SessionFactory() as db:
        replay = await approve_decision_seed_learning(
            db,
            command=ApproveDecisionSeedLearning(
                organization_context_id=ORGANIZATION_CONTEXT_ID,
                reviewer_id=REVIEWER_ID,
                expected_source_payload_digest=(
                    artifact.source_payload_digest
                ),
                approval_reference=APPROVAL_REFERENCE,
                trace_id="ci-decision-seed-approval-retry",
            ),
        )
        await db.rollback()

    if not first.created:
        raise RuntimeError("Initial Seed learning approval was not created.")
    if replay.created:
        raise RuntimeError("Seed learning approval retry created a duplicate.")
    if replay.approval_event_id != first.approval_event_id:
        raise RuntimeError("Seed learning approval retry changed event identity.")

    return str(first.approval_event_id), artifact.source_payload_digest


async def _snapshot() -> dict[str, object]:
    async with SessionFactory() as db:
        dataset = (
            await db.execute(
                select(AIDataset).where(
                    AIDataset.organization_context_id
                    == ORGANIZATION_CONTEXT_ID,
                    AIDataset.name == "parcham-decision-making",
                    AIDataset.purpose == "MODEL_TRAINING",
                )
            )
        ).scalar_one_or_none()
        if dataset is None:
            return {"dataset": 0}

        versions = list(
            (
                await db.execute(
                    select(AIDatasetVersion)
                    .where(AIDatasetVersion.dataset_id == dataset.id)
                    .order_by(AIDatasetVersion.version_number)
                )
            ).scalars().all()
        )
        approvals = list(
            (
                await db.execute(
                    select(AILearningSourceApproval).where(
                        AILearningSourceApproval.dataset_id == dataset.id
                    )
                )
            ).scalars().all()
        )
        items = list(
            (
                await db.execute(
                    select(AIDatasetItem)
                    .join(
                        AIDatasetVersion,
                        AIDatasetVersion.id
                        == AIDatasetItem.dataset_version_id,
                    )
                    .where(AIDatasetVersion.dataset_id == dataset.id)
                )
            ).scalars().all()
        )
        approval_events = (
            await db.execute(
                select(func.count())
                .select_from(DomainEvent)
                .where(
                    DomainEvent.organization_context_id
                    == ORGANIZATION_CONTEXT_ID,
                    DomainEvent.event_type
                    == "ai.learning_input_approved.v1",
                    DomainEvent.aggregate_type
                    == "AISeedLearningApproval",
                )
            )
        ).scalar_one()

        approval = approvals[0] if approvals else None
        item = items[0] if items else None
        return {
            "dataset": 1,
            "versions": len(versions),
            "approvals": len(approvals),
            "items": len(items),
            "approval_events": approval_events,
            "version_number": (
                None if not versions else versions[0].version_number
            ),
            "source_type": (
                None if approval is None else approval.source_type
            ),
            "approved_by_type": (
                None if approval is None else approval.approved_by_type
            ),
            "approved_by_reference": (
                None
                if approval is None
                else approval.approved_by_reference
            ),
            "source_payload_digest": (
                None
                if item is None
                else item.source_payload_digest
            ),
        }


async def main() -> None:
    event_id, expected_digest = await _approve()

    snapshot: dict[str, object] = {}
    for _ in range(80):
        snapshot = await _snapshot()
        if snapshot.get("items") == 1:
            break
        await asyncio.sleep(0.25)

    expected = {
        "dataset": 1,
        "versions": 1,
        "approvals": 1,
        "items": 1,
        "approval_events": 1,
        "version_number": 1,
        "source_type": "CURATED_SYNTHETIC_SEED",
        "approved_by_type": "PERSON",
        "approved_by_reference": str(REVIEWER_ID),
        "source_payload_digest": expected_digest,
    }
    if snapshot != expected:
        raise RuntimeError(
            "Seed learning approval acceptance failed: "
            f"{snapshot!r}"
        )

    print(f"approval_event_id={event_id}")
    print("seed_artifact_sha256=PASS")
    print("human_approval=PASS")
    print("approval_retry_idempotency=PASS")
    print("outbox_to_dataset_builder=PASS")
    print("dataset_version=1")
    print("training_started=NO")
    print("runtime_activation=NO")


if __name__ == "__main__":
    asyncio.run(main())
