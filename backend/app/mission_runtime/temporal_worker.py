import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from app.config import get_settings
from app.mission_runtime.temporal_activities import apply_scheduled_effect
from app.mission_runtime.temporal_workflows import ScheduledEffectWorkflow


async def _run_once() -> None:
    settings = get_settings()
    client = await Client.connect(
        settings.temporal_address,
        namespace=settings.temporal_namespace,
    )
    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[ScheduledEffectWorkflow],
        activities=[apply_scheduled_effect],
    )
    await worker.run()


async def run_forever() -> None:
    while True:
        try:
            await _run_once()
        except Exception:
            await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(run_forever())
