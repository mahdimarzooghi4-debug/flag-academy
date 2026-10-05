from datetime import datetime, timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from app.mission_runtime.temporal_activities import apply_scheduled_effect


@workflow.defn
class ScheduledEffectWorkflow:
    @workflow.run
    async def run(self, payload: dict[str, str]) -> str:
        due_at = datetime.fromisoformat(payload["due_at"])
        delay_seconds = max(0.0, (due_at - workflow.now()).total_seconds())
        if delay_seconds > 0:
            await workflow.sleep(timedelta(seconds=delay_seconds))
        return await workflow.execute_activity(
            apply_scheduled_effect,
            payload["effect_id"],
            start_to_close_timeout=timedelta(seconds=30),
        )
