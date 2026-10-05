from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID

import nats
from nats.js.errors import NotFoundError
from sqlalchemy import select
from temporalio.client import Client

from app import models as all_models  # noqa: F401
from app.config import get_settings
from app.db import SessionFactory
from app.mission_runtime.domain import ScheduledEffectStatus
from app.mission_runtime.models import ScheduledEffect
from app.mission_runtime.temporal_workflows import ScheduledEffectWorkflow
from app.platform.events import EventEnvelope
from app.platform.models import InboxEvent

STREAM_NAME = "PARCHAM_EVENTS"
CONSUMER_NAME = "mission-scheduled-effect-starter-v1"
SUBJECT = "parcham.events.mission.scheduled_effect_created.v1"


async def _ensure_stream(js) -> None:
    try:
        await js.stream_info(STREAM_NAME)
    except NotFoundError:
        await js.add_stream(name=STREAM_NAME, subjects=["parcham.events.>"])


async def _run_once() -> None:
    settings = get_settings()
    temporal_client = await Client.connect(
        settings.temporal_address,
        namespace=settings.temporal_namespace,
    )
    nc = await nats.connect(settings.nats_url)
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

            effect_id = envelope.payload.get("scheduled_effect_id")
            due_at = envelope.payload.get("due_at")
            if not effect_id or not due_at:
                await message.ack()
                return

            workflow_id = f"scheduled-effect-{effect_id}"
            try:
                await temporal_client.start_workflow(
                    ScheduledEffectWorkflow.run,
                    {"effect_id": str(effect_id), "due_at": str(due_at)},
                    id=workflow_id,
                    task_queue=settings.temporal_task_queue,
                )
            except Exception:
                handle = temporal_client.get_workflow_handle(workflow_id)
                try:
                    await handle.describe()
                except Exception:
                    await db.rollback()
                    await message.nak()
                    return

            effect = (
                await db.execute(
                    select(ScheduledEffect)
                    .where(ScheduledEffect.id == UUID(str(effect_id)))
                    .with_for_update()
                )
            ).scalar_one_or_none()
            if (
                effect is not None
                and effect.status == ScheduledEffectStatus.PENDING.value
            ):
                effect.status = ScheduledEffectStatus.SCHEDULED.value
                effect.workflow_id = workflow_id
                effect.scheduled_at = datetime.now(UTC)

            db.add(
                InboxEvent(
                    consumer_name=CONSUMER_NAME,
                    event_id=envelope.event_id,
                    processed_at=datetime.now(UTC),
                )
            )
            await db.commit()
            await message.ack()

    await js.subscribe(
        SUBJECT,
        durable=CONSUMER_NAME,
        cb=handler,
        manual_ack=True,
    )
    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        await nc.close()


async def run_forever() -> None:
    while True:
        try:
            await _run_once()
        except Exception:
            await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(run_forever())
