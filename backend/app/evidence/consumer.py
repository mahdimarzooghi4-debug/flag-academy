from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

import nats
from nats.js.errors import NotFoundError
from sqlalchemy import select

from app.db import SessionFactory
from app.evidence.domain import EvidenceCaseStatus
from app.evidence.models import EvidenceCase
from app.platform.events import EventEnvelope, new_event, record_event
from app.platform.models import InboxEvent

STREAM_NAME = "PARCHAM_EVENTS"
CONSUMER_NAME = "evidence-observation-ingestor-v1"


async def _ensure_stream(js) -> None:
    try:
        await js.stream_info(STREAM_NAME)
    except NotFoundError:
        await js.add_stream(name=STREAM_NAME, subjects=["parcham.events.>"])


async def apply_event(envelope: EventEnvelope, db) -> None:
    if envelope.event_type != "observation.sealed.v1":
        return

    payload = envelope.payload
    required = {
        "observation_id",
        "subject_person_id",
        "source_context",
        "source_reference",
        "source_runtime_event_id",
        "observation_type",
        "observed_fact",
        "observed_payload",
        "occurred_at",
        "source_independence_group",
        "provenance",
    }
    if envelope.organization_context_id is None or any(key not in payload for key in required):
        raise ValueError("observation.sealed.v1 payload is incomplete")

    source_observation_id = UUID(str(payload["observation_id"]))
    existing = (
        await db.execute(
            select(EvidenceCase.id).where(
                EvidenceCase.source_observation_id == source_observation_id
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return

    now = datetime.now(UTC)
    evidence_case = EvidenceCase(
        id=uuid4(),
        version=1,
        organization_context_id=envelope.organization_context_id,
        subject_person_id=UUID(str(payload["subject_person_id"])),
        source_observation_id=source_observation_id,
        source_context=str(payload["source_context"]),
        source_reference=str(payload["source_reference"]),
        source_runtime_event_id=UUID(str(payload["source_runtime_event_id"])),
        observation_type=str(payload["observation_type"]),
        observed_fact=str(payload["observed_fact"]),
        observed_payload=dict(payload["observed_payload"]),
        occurred_at=datetime.fromisoformat(str(payload["occurred_at"])),
        source_independence_group=str(payload["source_independence_group"]),
        provenance=dict(payload["provenance"]),
        integrity_state="SEALED",
        status=EvidenceCaseStatus.DRAFT.value,
        context_request=None,
        created_at=now,
        updated_at=now,
        accepted_at=None,
        rejected_at=None,
    )
    db.add(evidence_case)
    await db.flush()

    record_event(
        db,
        new_event(
            event_type="evidence.case_created.v1",
            aggregate_type="EvidenceCase",
            aggregate_id=evidence_case.id,
            aggregate_version=evidence_case.version,
            actor={"type": "SYSTEM", "id": CONSUMER_NAME},
            organization_context_id=evidence_case.organization_context_id,
            data_classification="INTERNAL",
            payload={
                "evidence_case_id": str(evidence_case.id),
                "subject_person_id": str(evidence_case.subject_person_id),
                "source_observation_id": str(evidence_case.source_observation_id),
                "observation_type": evidence_case.observation_type,
            },
            trace_id=envelope.trace_id,
            causation_id=envelope.event_id,
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
        "parcham.events.observation.sealed.v1",
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
