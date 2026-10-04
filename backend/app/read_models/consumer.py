from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID

import nats
from nats.js.errors import NotFoundError
from sqlalchemy import select

from app.db import SessionFactory
from app.platform.events import EventEnvelope
from app.platform.models import InboxEvent
from app.read_models.projector import rebuild_candidate_home, rebuild_cohort_read_models

STREAM_NAME = "PARCHAM_EVENTS"
CONSUMER_NAME = "read-model-projector-v1"


async def _ensure_stream(js) -> None:
    try:
        await js.stream_info(STREAM_NAME)
    except NotFoundError:
        await js.add_stream(name=STREAM_NAME, subjects=["parcham.events.>"])


async def apply_event(envelope: EventEnvelope, db) -> None:
    if envelope.event_type == "candidate.journey_created.v1":
        candidate_id = envelope.payload.get("candidate_id")
        if candidate_id and envelope.organization_context_id:
            await rebuild_candidate_home(
                db,
                person_id=UUID(str(candidate_id)),
                organization_context_id=envelope.organization_context_id,
            )
        return

    if envelope.event_type == "academy.session_scheduled.v1":
        from app.academy.models import ClassOffering

        class_id = envelope.payload.get("class_offering_id")
        if not class_id or not envelope.organization_context_id:
            return
        class_offering = await db.get(ClassOffering, UUID(str(class_id)))
        if class_offering is not None:
            await rebuild_cohort_read_models(
                db,
                cohort_id=class_offering.cohort_id,
                organization_context_id=envelope.organization_context_id,
            )
        return

    if envelope.event_type in {
        "learning.unit_published.v1",
        "learning.unit_started.v1",
        "learning.unit_completed.v1",
        "learning.assignment_published.v1",
        "learning.submission_submitted.v1",
        "learning.instructor_feedback_recorded.v1",
    }:
        cohort_id = envelope.payload.get("cohort_id")
        if cohort_id and envelope.organization_context_id:
            await rebuild_cohort_read_models(
                db,
                cohort_id=UUID(str(cohort_id)),
                organization_context_id=envelope.organization_context_id,
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
        "parcham.events.>",
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
