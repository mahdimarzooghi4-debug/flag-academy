from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import nats
from nats.js.errors import NotFoundError
from sqlalchemy import select

from app.ai_control_plane.dataset_builder import (
    ApprovedLearningInput,
    ingest_approved_learning_input,
)
from app.db import SessionFactory
from app.platform.events import EventEnvelope
from app.platform.models import InboxEvent

STREAM_NAME = "PARCHAM_EVENTS"
CONSUMER_NAME = "ai-dataset-builder-v1"
APPROVED_INPUT_EVENT = "ai.learning_input_approved.v1"


async def _ensure_stream(js) -> None:
    try:
        await js.stream_info(STREAM_NAME)
    except NotFoundError:
        await js.add_stream(name=STREAM_NAME, subjects=["parcham.events.>"])


def _required_payload(payload: dict, key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"{APPROVED_INPUT_EVENT} payload is missing {key}"
        )
    return value.strip()


async def apply_event(envelope: EventEnvelope, db) -> None:
    if envelope.event_type != APPROVED_INPUT_EVENT:
        return

    if envelope.organization_context_id is None:
        raise ValueError(
            f"{APPROVED_INPUT_EVENT} requires organization_context_id"
        )

    actor_type = envelope.actor.get("type")
    actor_id = envelope.actor.get("id")
    if actor_type not in {"PERSON", "SYSTEM"}:
        raise ValueError(
            f"{APPROVED_INPUT_EVENT} actor must be PERSON or SYSTEM"
        )
    if not isinstance(actor_id, str) or not actor_id.strip():
        raise ValueError(
            f"{APPROVED_INPUT_EVENT} actor id is required"
        )

    payload = envelope.payload
    source_version_value = payload.get("source_version")
    source_version = (
        str(source_version_value).strip()
        if source_version_value is not None
        and str(source_version_value).strip()
        else None
    )

    await ingest_approved_learning_input(
        db,
        command=ApprovedLearningInput(
            organization_context_id=envelope.organization_context_id,
            dataset_name=_required_payload(payload, "dataset_name"),
            purpose=_required_payload(payload, "purpose"),
            source_policy_key=_required_payload(
                payload,
                "source_policy_key",
            ),
            source_policy_version=_required_payload(
                payload,
                "source_policy_version",
            ),
            source_type=_required_payload(payload, "source_type"),
            source_reference=_required_payload(
                payload,
                "source_reference",
            ),
            source_version=source_version,
            source_payload_digest=_required_payload(
                payload,
                "source_payload_digest",
            ),
            approval_reference=_required_payload(
                payload,
                "approval_reference",
            ),
            approval_event_id=envelope.event_id,
            data_classification=envelope.data_classification,
            approved_by_type=str(actor_type),
            approved_by_reference=actor_id.strip(),
            approved_at=envelope.occurred_at,
            trace_id=envelope.trace_id,
        ),
    )


async def run_forever() -> None:
    from app.config import get_settings

    nc = await nats.connect(get_settings().nats_url)
    js = nc.jetstream()
    await _ensure_stream(js)

    async def handler(message) -> None:
        envelope = EventEnvelope.model_validate_json(message.data)
        async with SessionFactory() as db:
            already_processed = (
                await db.execute(
                    select(InboxEvent.id).where(
                        InboxEvent.consumer_name == CONSUMER_NAME,
                        InboxEvent.event_id == envelope.event_id,
                    )
                )
            ).scalar_one_or_none()
            if already_processed is not None:
                await message.ack()
                return

            try:
                await apply_event(envelope, db)
                db.add(
                    InboxEvent(
                        consumer_name=CONSUMER_NAME,
                        event_id=envelope.event_id,
                        processed_at=datetime.now(UTC),
                    )
                )
                await db.commit()
                await message.ack()
            except Exception:
                await db.rollback()
                await message.nak()

    await js.subscribe(
        "parcham.events.ai.learning_input_approved.v1",
        durable=CONSUMER_NAME,
        cb=handler,
        manual_ack=True,
    )
    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        await nc.close()


if __name__ == "__main__":
    asyncio.run(run_forever())
