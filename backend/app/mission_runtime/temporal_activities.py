from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import func, select
from temporalio import activity

from app.db import SessionFactory
from app.mission_runtime.domain import (
    MissionInstanceStatus,
    ScheduledEffectStatus,
    apply_world_effect,
)
from app.mission_runtime.models import (
    MissionInstance,
    Observation,
    RuntimeEvent,
    ScheduledEffect,
)
from app.platform.events import new_event, record_event


async def _next_event_sequence(db, instance_id: UUID) -> int:
    value = (
        await db.execute(
            select(func.max(RuntimeEvent.sequence_number)).where(
                RuntimeEvent.mission_instance_id == instance_id
            )
        )
    ).scalar_one_or_none()
    return int(value or 0) + 1


async def _next_observation_sequence(db, instance_id: UUID) -> int:
    value = (
        await db.execute(
            select(func.max(Observation.sequence_number)).where(
                Observation.mission_instance_id == instance_id
            )
        )
    ).scalar_one_or_none()
    return int(value or 0) + 1


@activity.defn
async def apply_scheduled_effect(effect_id: str) -> str:
    now = datetime.now(UTC)
    async with SessionFactory() as db:
        effect = (
            await db.execute(
                select(ScheduledEffect)
                .where(ScheduledEffect.id == UUID(effect_id))
                .with_for_update()
            )
        ).scalar_one_or_none()
        if effect is None:
            return "NOT_FOUND"
        if effect.status == ScheduledEffectStatus.APPLIED.value:
            return ScheduledEffectStatus.APPLIED.value
        if effect.status == ScheduledEffectStatus.CANCELLED.value:
            return ScheduledEffectStatus.CANCELLED.value

        instance = (
            await db.execute(
                select(MissionInstance)
                .where(MissionInstance.id == effect.mission_instance_id)
                .with_for_update()
            )
        ).scalar_one_or_none()
        if instance is None:
            effect.status = ScheduledEffectStatus.CANCELLED.value
            effect.cancelled_at = now
            await db.commit()
            return ScheduledEffectStatus.CANCELLED.value

        if (
            effect.cancellable
            and effect.cancel_condition.get("mission_must_be_running") is True
            and instance.status != MissionInstanceStatus.RUNNING.value
        ):
            effect.status = ScheduledEffectStatus.CANCELLED.value
            effect.cancelled_at = now
            await db.commit()
            return ScheduledEffectStatus.CANCELLED.value

        before = instance.world_state_version
        instance.world_state = apply_world_effect(instance.world_state, effect.world_effect)
        instance.world_state_version += 1
        instance.version += 1

        event = RuntimeEvent(
            id=uuid4(),
            mission_instance_id=instance.id,
            sequence_number=await _next_event_sequence(db, instance.id),
            event_type="scheduled_effect.applied",
            source="ENGINE",
            trigger_type="SCHEDULED",
            trigger_reference=str(effect.id),
            occurred_at=now,
            effective_at=now,
            visibility="CANDIDATE",
            payload={
                "effect_code": effect.effect_code,
                "message": effect.candidate_message,
                "effect_applied": effect.world_effect,
                "world_version_before": before,
                "world_version_after": instance.world_state_version,
            },
            world_version_before=before,
            world_version_after=instance.world_state_version,
            causal_parent_ids=[str(effect.origin_event_id)],
            idempotency_key=f"scheduled-effect:{effect.id}:applied",
        )
        db.add(event)
        await db.flush()

        db.add(
            Observation(
                id=uuid4(),
                mission_instance_id=instance.id,
                source_event_id=event.id,
                sequence_number=await _next_observation_sequence(db, instance.id),
                observation_type="SCHEDULED_EFFECT_OBSERVED",
                factual_statement=(
                    f"Scheduled effect '{effect.effect_code}' applied; world state advanced "
                    f"from version {before} to {instance.world_state_version}."
                ),
                payload={
                    "effect_code": effect.effect_code,
                    "world_version_before": before,
                    "world_version_after": instance.world_state_version,
                },
                occurred_at=now,
            )
        )

        effect.status = ScheduledEffectStatus.APPLIED.value
        effect.applied_at = now

        record_event(
            db,
            new_event(
                event_type="mission.scheduled_effect_applied.v1",
                aggregate_type="MissionInstance",
                aggregate_id=instance.id,
                aggregate_version=instance.version,
                actor={"type": "SYSTEM", "id": "TEMPORAL"},
                organization_context_id=instance.organization_context_id,
                data_classification="INTERNAL",
                payload={
                    "mission_instance_id": str(instance.id),
                    "scheduled_effect_id": str(effect.id),
                    "effect_code": effect.effect_code,
                    "world_version_before": before,
                    "world_version_after": instance.world_state_version,
                },
                trace_id=f"temporal:{effect.id}",
            ),
        )
        await db.commit()
        return ScheduledEffectStatus.APPLIED.value
