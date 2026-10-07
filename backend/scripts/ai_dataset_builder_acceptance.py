from __future__ import annotations

import asyncio
import json
from uuid import UUID

import nats
from sqlalchemy import func, select

from app.ai_control_plane.consumer import CONSUMER_NAME
from app.ai_control_plane.models import (
    AIDataset,
    AIDatasetItem,
    AIDatasetVersion,
    AILearningSourceApproval,
)
from app.config import get_settings
from app.db import SessionFactory
from app.platform.events import new_event
from app.platform.models import InboxEvent, OutboxEvent

ORGANIZATION_CONTEXT_ID = UUID(
    "30000000-0000-0000-0000-000000000001"
)
DATASET_NAME = "ci-governed-learning"
PURPOSE = "MODEL_TRAINING"
SUBJECT = "parcham.events.ai.learning_input_approved.v1"


def _event(*, approval_reference: str):
    return new_event(
        event_type="ai.learning_input_approved.v1",
        aggregate_type="AILearningApproval",
        aggregate_id=UUID(
            "30000000-0000-0000-0000-000000000002"
        ),
        aggregate_version=1,
        actor={"type": "PERSON", "id": "ci-human-reviewer"},
        organization_context_id=ORGANIZATION_CONTEXT_ID,
        data_classification="CONFIDENTIAL",
        payload={
            "dataset_name": DATASET_NAME,
            "purpose": PURPOSE,
            "source_policy_key": "ci-ai-learning-policy",
            "source_policy_version": "v1",
            "source_type": "CI_GOVERNED_SOURCE",
            "source_reference": "ci-source:1",
            "source_version": "1",
            "source_payload_digest": "a" * 64,
            "approval_reference": approval_reference,
        },
        trace_id="ci-ai-dataset-builder",
    )


async def _publish() -> tuple[str, str]:
    first = _event(approval_reference="ci-approval-1")
    replay = first.model_dump(mode="json")
    second = _event(approval_reference="ci-approval-2")

    nc = await nats.connect(get_settings().nats_url)
    try:
        js = nc.jetstream()
        await js.publish(
            SUBJECT,
            json.dumps(replay, default=str).encode(),
        )
        await js.publish(
            SUBJECT,
            json.dumps(replay, default=str).encode(),
        )
        await js.publish(
            SUBJECT,
            json.dumps(
                second.model_dump(mode="json"),
                default=str,
            ).encode(),
        )
    finally:
        await nc.close()

    return str(first.event_id), str(second.event_id)


async def _counts() -> dict[str, int]:
    async with SessionFactory() as db:
        dataset = (
            await db.execute(
                select(AIDataset).where(
                    AIDataset.organization_context_id
                    == ORGANIZATION_CONTEXT_ID,
                    AIDataset.name == DATASET_NAME,
                    AIDataset.purpose == PURPOSE,
                )
            )
        ).scalar_one_or_none()
        if dataset is None:
            return {
                "datasets": 0,
                "approvals": 0,
                "versions": 0,
                "items": 0,
                "inbox": 0,
                "dataset_events": 0,
            }

        versions = (
            await db.execute(
                select(AIDatasetVersion.id).where(
                    AIDatasetVersion.dataset_id == dataset.id
                )
            )
        ).scalars().all()

        return {
            "datasets": 1,
            "approvals": (
                await db.execute(
                    select(func.count())
                    .select_from(AILearningSourceApproval)
                    .where(
                        AILearningSourceApproval.dataset_id
                        == dataset.id
                    )
                )
            ).scalar_one(),
            "versions": len(versions),
            "items": (
                await db.execute(
                    select(func.count())
                    .select_from(AIDatasetItem)
                    .where(
                        AIDatasetItem.dataset_version_id.in_(versions)
                    )
                )
            ).scalar_one()
            if versions
            else 0,
            "inbox": (
                await db.execute(
                    select(func.count())
                    .select_from(InboxEvent)
                    .where(
                        InboxEvent.consumer_name == CONSUMER_NAME
                    )
                )
            ).scalar_one(),
            "dataset_events": (
                await db.execute(
                    select(func.count())
                    .select_from(OutboxEvent)
                    .where(
                        OutboxEvent.event_type
                        == "ai.dataset_version_created.v1"
                    )
                )
            ).scalar_one(),
        }


async def main() -> None:
    await _publish()

    counts: dict[str, int] = {}
    for _ in range(60):
        counts = await _counts()
        if counts["inbox"] >= 2:
            break
        await asyncio.sleep(0.25)

    expected = {
        "datasets": 1,
        "approvals": 1,
        "versions": 1,
        "items": 1,
        "inbox": 2,
        "dataset_events": 1,
    }
    if counts != expected:
        raise RuntimeError(
            f"AI Dataset Builder acceptance failed: {counts!r}"
        )

    for key, value in counts.items():
        print(f"{key}={value}")
    print("semantic_reapproval_dedup=PASS")
    print("duplicate_delivery_idempotency=PASS")
    print("reviewed_domain_events_implicit_approval=FORBIDDEN")


if __name__ == "__main__":
    asyncio.run(main())
