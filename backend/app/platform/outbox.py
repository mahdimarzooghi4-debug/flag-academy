from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime

import nats
from nats.js.errors import NotFoundError
from sqlalchemy import select

from app.config import get_settings
from app.db import SessionFactory
from app.platform.models import OutboxEvent

STREAM_NAME = "PARCHAM_EVENTS"
STREAM_SUBJECTS = ["parcham.events.>"]


async def _ensure_stream(js) -> None:
    try:
        await js.stream_info(STREAM_NAME)
    except NotFoundError:
        await js.add_stream(name=STREAM_NAME, subjects=STREAM_SUBJECTS)


async def publish_pending_once() -> int:
    settings = get_settings()
    nc = await nats.connect(settings.nats_url)
    published = 0
    try:
        js = nc.jetstream()
        await _ensure_stream(js)
        async with SessionFactory() as db:
            rows = (
                await db.execute(
                    select(OutboxEvent)
                    .where(OutboxEvent.published_at.is_(None))
                    .order_by(OutboxEvent.created_at)
                    .limit(100)
                    .with_for_update(skip_locked=True)
                )
            ).scalars().all()
            for item in rows:
                subject = f"parcham.events.{item.event_type}"
                item.attempt_count += 1
                try:
                    await js.publish(subject, json.dumps(item.payload, default=str).encode())
                    item.published_at = datetime.now(UTC)
                    item.last_error = None
                    published += 1
                except Exception as exc:
                    item.last_error = str(exc)[:2000]
            await db.commit()
    finally:
        await nc.close()
    return published


async def run_forever() -> None:
    while True:
        try:
            count = await publish_pending_once()
            if count == 0:
                await asyncio.sleep(1)
        except Exception:
            await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(run_forever())
