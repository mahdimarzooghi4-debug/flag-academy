from datetime import UTC, datetime, timedelta
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.errors import AppError
from app.identity.auth import ActorContext, require_role
from app.identity.models import OrganizationMembership, Person
from app.journey.models import CandidateJourney
from app.mission_design.models import MissionTemplate, MissionVersion
from app.mission_runtime.domain import (
    MissionActionType,
    MissionAssignmentStatus,
    MissionInstanceStatus,
    ScheduledEffectStatus,
    apply_actor_effect,
    apply_world_effect,
    assignment_transition_allowed,
    candidate_event_payload,
    candidate_event_visible,
    candidate_observation_payload,
    candidate_observation_visible,
    delegation_preserves_candidate_accountability,
    preserves_candidate_accountability,
    project_candidate_visible_state,
    runtime_transition_allowed,
)
from app.mission_runtime.models import (
    ActorInstance,
    CandidateAction,
    DecisionRecord,
    MissionAssignment,
    MissionInstance,
    Observation,
    RuntimeEvent,
    ScheduledEffect,
)
from app.platform.events import new_event, record_event

router = APIRouter(prefix="/api/v1", tags=["mission-runtime"])


class MissionStartRequest(BaseModel):
    assignment_id: UUID
    idempotency_key: str = Field(min_length=1, max_length=160)


class MissionAssignmentCreateRequest(BaseModel):
    candidate_id: UUID
    mission_version_id: UUID
    assignment_reason: str = Field(min_length=1, max_length=2000)
    idempotency_key: str = Field(min_length=1, max_length=160)


class MissionAssignmentCandidateResponse(BaseModel):
    id: UUID
    display_name: str


class MissionAssignmentResponse(BaseModel):
    id: UUID
    version: int
    candidate_id: UUID
    candidate_name: str
    mission_version_id: UUID
    mission_code: str
    mission_title: str
    status: str
    assignment_reason: str
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class AdvanceSimulationRequest(BaseModel):
    expected_world_version: int = Field(ge=1)
    idempotency_key: str = Field(min_length=1, max_length=160)


class MissionActionRequest(BaseModel):
    action_type: MissionActionType
    target: str | None = Field(default=None, max_length=255)
    payload: dict[str, Any] = Field(default_factory=dict)
    reasoning: str = Field(min_length=1, max_length=5000)
    confidence: int = Field(ge=0, le=100)
    expected_world_version: int = Field(ge=1)
    expected_actor_version: int | None = Field(default=None, ge=1)
    idempotency_key: str = Field(min_length=1, max_length=160)
    resource_cost: dict[str, Any] = Field(default_factory=dict)
    mode: str = Field(default="CANDIDATE", min_length=1, max_length=32)
    provenance: dict[str, Any] = Field(default_factory=dict)


class MissionCatalogItem(BaseModel):
    assignment_id: UUID
    assignment_status: str
    version_id: UUID
    template_id: UUID
    code: str
    title: str
    purpose: str
    difficulty: str
    decision_points: list[dict[str, Any]]
    information_options: list[dict[str, Any]]
    decision_options: list[dict[str, Any]]


class RuntimeEventResponse(BaseModel):
    id: UUID
    sequence_number: int
    event_type: str
    source: str
    visibility: str
    payload: dict[str, Any]
    world_version_before: int
    world_version_after: int
    occurred_at: datetime


class ObservationResponse(BaseModel):
    id: UUID
    source_event_id: UUID
    sequence_number: int
    observation_type: str
    factual_statement: str
    payload: dict[str, Any]
    occurred_at: datetime


class ScheduledEffectResponse(BaseModel):
    id: UUID
    effect_code: str
    label: str
    due_at: datetime | None
    trigger_mode: str
    status: str


class ActorInstanceResponse(BaseModel):
    id: UUID
    actor_key: str
    display_name: str
    state: dict[str, Any]
    state_version: int
    communication_options: list[dict[str, str]]


class MissionInstanceResponse(BaseModel):
    id: UUID
    version: int
    assignment_id: UUID | None
    mission_version_id: UUID
    template_id: UUID
    mission_code: str
    title: str
    status: str
    world_state: dict[str, Any]
    world_state_version: int
    simulation_time: datetime
    scheduled_effects: list[ScheduledEffectResponse]
    decision_points: list[dict[str, Any]]
    information_options: list[dict[str, Any]]
    decision_options: list[dict[str, Any]]
    escalation_options: list[dict[str, str]]
    delegation_options: list[dict[str, str]]
    scope_change_options: list[dict[str, str]]
    no_action_options: list[dict[str, str]]
    actors: list[ActorInstanceResponse]
    disclosed_information: list[dict[str, Any]]
    audit_events: list[RuntimeEventResponse]
    observations: list[ObservationResponse]
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


def _runtime_config(version: MissionVersion) -> dict[str, Any]:
    value = version.world_context.get("runtime_v1", {})
    return value if isinstance(value, dict) else {}


def _information_options(version: MissionVersion) -> list[dict[str, Any]]:
    return [
        {"label": item.get("label", ""), "access": item.get("access", "")}
        for item in version.information_items
        if item.get("access") in {"DEFAULT", "DISCOVERABLE"}
    ]


def _decision_options(version: MissionVersion) -> list[dict[str, Any]]:
    value = _runtime_config(version).get("decision_options", [])
    return value if isinstance(value, list) else []


def _escalation_options(version: MissionVersion) -> list[dict[str, str]]:
    value = _runtime_config(version).get("escalation_options", [])
    if not isinstance(value, list):
        return []

    options: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        code = item.get("code")
        label = item.get("label")
        actor_key = item.get("actor_key")
        if (
            isinstance(code, str)
            and code
            and isinstance(label, str)
            and label
            and isinstance(actor_key, str)
            and actor_key
        ):
            options.append(
                {
                    "code": code,
                    "label": label,
                    "actor_key": actor_key,
                }
            )
    return options


def _delegation_options(version: MissionVersion) -> list[dict[str, str]]:
    value = _runtime_config(version).get("delegation_options", [])
    if not isinstance(value, list):
        return []

    options: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        code = item.get("code")
        label = item.get("label")
        actor_key = item.get("actor_key")
        if (
            isinstance(code, str)
            and code
            and isinstance(label, str)
            and label
            and isinstance(actor_key, str)
            and actor_key
        ):
            options.append(
                {
                    "code": code,
                    "label": label,
                    "actor_key": actor_key,
                }
            )
    return options


def _scope_change_options(version: MissionVersion) -> list[dict[str, str]]:
    value = _runtime_config(version).get("scope_change_options", [])
    if not isinstance(value, list):
        return []

    options: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        code = item.get("code")
        label = item.get("label")
        from_scope = item.get("from_scope")
        to_scope = item.get("to_scope")
        if (
            isinstance(code, str)
            and code
            and isinstance(label, str)
            and label
            and isinstance(from_scope, str)
            and from_scope
            and isinstance(to_scope, str)
            and to_scope
            and from_scope != to_scope
        ):
            options.append(
                {
                    "code": code,
                    "label": label,
                    "from_scope": from_scope,
                    "to_scope": to_scope,
                }
            )
    return options


def _no_action_options(version: MissionVersion) -> list[dict[str, str]]:
    value = _runtime_config(version).get("no_action_options", [])
    if not isinstance(value, list):
        return []
    options: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        code = item.get("code")
        label = item.get("label")
        if isinstance(code, str) and code and isinstance(label, str) and label:
            options.append({"code": code, "label": label})
    return options


def _candidate_visible_paths(version: MissionVersion) -> list[str]:
    value = _runtime_config(version).get("candidate_visible_paths", [])
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item.strip()]


def _actor_runtime_configs(version: MissionVersion) -> dict[str, Any]:
    value = _runtime_config(version).get("actor_runtime", {})
    return value if isinstance(value, dict) else {}


def _actor_runtime_config(
    version: MissionVersion,
    actor_key: str,
) -> dict[str, Any] | None:
    value = _actor_runtime_configs(version).get(actor_key)
    return value if isinstance(value, dict) else None


def _actor_candidate_visible_paths(config: dict[str, Any]) -> list[str]:
    value = config.get("candidate_visible_paths", [])
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item.strip()]


def _actor_communication_options(config: dict[str, Any]) -> list[dict[str, str]]:
    value = config.get("communication_options", [])
    if not isinstance(value, list):
        return []

    options: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        code = item.get("code")
        label = item.get("label")
        if isinstance(code, str) and code and isinstance(label, str) and label:
            options.append({"code": code, "label": label})
    return options


async def _load_version_and_template(
    db: AsyncSession,
    actor: ActorContext,
    version_id: UUID,
    *,
    require_active: bool,
) -> tuple[MissionVersion, MissionTemplate]:
    row = (
        await db.execute(
            select(MissionVersion, MissionTemplate)
            .join(MissionTemplate, MissionVersion.template_id == MissionTemplate.id)
            .where(
                MissionVersion.id == version_id,
                MissionTemplate.organization_context_id
                == actor.organization_context_id,
            )
        )
    ).first()
    if row is None:
        raise AppError(
            "MISSION_VERSION_NOT_FOUND",
            "Mission version not found.",
            status_code=404,
        )
    version, template = row
    if require_active and version.status != "ACTIVE":
        raise AppError(
            "MISSION_VERSION_NOT_ACTIVE",
            "Only an active mission version can be started.",
            status_code=409,
        )
    return version, template


async def _candidate_eligibility_checks(
    db: AsyncSession,
    *,
    organization_context_id: UUID,
    candidate_id: UUID,
) -> dict[str, bool]:
    membership = (
        await db.execute(
            select(OrganizationMembership.id).where(
                OrganizationMembership.person_id == candidate_id,
                OrganizationMembership.organization_id == organization_context_id,
                OrganizationMembership.membership_role == "CANDIDATE",
            )
        )
    ).scalar_one_or_none()
    active_journey = (
        await db.execute(
            select(CandidateJourney.id).where(
                CandidateJourney.person_id == candidate_id,
                CandidateJourney.organization_context_id == organization_context_id,
                CandidateJourney.state == "ACTIVE",
            )
        )
    ).scalar_one_or_none()
    return {
        "candidate_membership": membership is not None,
        "active_candidate_journey": active_journey is not None,
    }


async def _assert_candidate_eligible(
    db: AsyncSession,
    *,
    organization_context_id: UUID,
    candidate_id: UUID,
) -> dict[str, bool]:
    checks = await _candidate_eligibility_checks(
        db,
        organization_context_id=organization_context_id,
        candidate_id=candidate_id,
    )
    if not all(checks.values()):
        raise AppError(
            "MISSION_ELIGIBILITY_FAILED",
            "Candidate is not eligible to run this mission assignment.",
            status_code=409,
            details={"checks": checks},
        )
    return checks


async def _load_candidate_instance(
    db: AsyncSession,
    actor: ActorContext,
    instance_id: UUID,
    *,
    for_update: bool = False,
) -> MissionInstance:
    stmt = select(MissionInstance).where(
        MissionInstance.id == instance_id,
        MissionInstance.organization_context_id == actor.organization_context_id,
        MissionInstance.candidate_id == actor.person_id,
    )
    if for_update:
        stmt = stmt.with_for_update()
    instance = (await db.execute(stmt)).scalar_one_or_none()
    if instance is None:
        raise AppError(
            "MISSION_INSTANCE_NOT_FOUND",
            "Mission instance not found.",
            status_code=404,
        )
    return instance


async def _next_event_sequence(db: AsyncSession, instance_id: UUID) -> int:
    value = (
        await db.execute(
            select(func.max(RuntimeEvent.sequence_number)).where(
                RuntimeEvent.mission_instance_id == instance_id
            )
        )
    ).scalar_one_or_none()
    return int(value or 0) + 1


async def _next_observation_sequence(db: AsyncSession, instance_id: UUID) -> int:
    value = (
        await db.execute(
            select(func.max(Observation.sequence_number)).where(
                Observation.mission_instance_id == instance_id
            )
        )
    ).scalar_one_or_none()
    return int(value or 0) + 1


async def _append_runtime_event(
    db: AsyncSession,
    *,
    instance: MissionInstance,
    event_type: str,
    source: str,
    trigger_type: str,
    trigger_reference: str | None,
    payload: dict[str, Any],
    world_version_before: int,
    world_version_after: int,
    idempotency_key: str,
    now: datetime,
    causal_parent_ids: list[str] | None = None,
    visibility: str = "CANDIDATE",
    effective_at: datetime | None = None,
) -> RuntimeEvent:
    event = RuntimeEvent(
        id=uuid4(),
        mission_instance_id=instance.id,
        sequence_number=await _next_event_sequence(db, instance.id),
        event_type=event_type,
        source=source,
        trigger_type=trigger_type,
        trigger_reference=trigger_reference,
        occurred_at=now,
        effective_at=effective_at or now,
        visibility=visibility,
        payload=payload,
        world_version_before=world_version_before,
        world_version_after=world_version_after,
        causal_parent_ids=causal_parent_ids or [],
        idempotency_key=idempotency_key,
    )
    db.add(event)
    await db.flush()
    return event


async def _append_observation(
    db: AsyncSession,
    *,
    instance: MissionInstance,
    source_event: RuntimeEvent,
    observation_type: str,
    factual_statement: str,
    payload: dict[str, Any],
    now: datetime,
) -> Observation:
    observation = Observation(
        id=uuid4(),
        mission_instance_id=instance.id,
        source_event_id=source_event.id,
        sequence_number=await _next_observation_sequence(db, instance.id),
        observation_type=observation_type,
        factual_statement=factual_statement,
        payload=payload,
        occurred_at=now,
    )
    db.add(observation)
    await db.flush()
    return observation


def _world_state_path_value(
    world_state: dict[str, Any],
    path: str,
) -> Any:
    current: Any = world_state
    for part in [segment for segment in path.split(".") if segment]:
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _scheduled_trigger_condition_valid(
    condition: dict[str, Any],
) -> bool:
    return (
        condition.get("type") == "WORLD_STATE_EQUALS"
        and isinstance(condition.get("path"), str)
        and bool(condition.get("path"))
        and "equals" in condition
    )


def _scheduled_trigger_condition_matches(
    world_state: dict[str, Any],
    condition: dict[str, Any],
) -> bool:
    if not _scheduled_trigger_condition_valid(condition):
        return False
    return _world_state_path_value(
        world_state,
        str(condition["path"]),
    ) == condition["equals"]


def _scheduled_effect_trigger_mode(effect: ScheduledEffect) -> str:
    return "DUE_AT" if effect.due_at is not None else "STATE_TRIGGERED"


def _scheduled_effect_due_at_text(effect: ScheduledEffect) -> str | None:
    return effect.due_at.isoformat() if effect.due_at is not None else None


def _scheduled_cancel_condition_valid(
    condition: dict[str, Any],
) -> bool:
    return (
        condition.get("type") == "WORLD_STATE_EQUALS"
        and isinstance(condition.get("path"), str)
        and bool(condition.get("path"))
        and "equals" in condition
        and isinstance(condition.get("reason_code"), str)
        and bool(condition.get("reason_code"))
    )


def _scheduled_cancel_condition_matches(
    world_state: dict[str, Any],
    condition: dict[str, Any],
) -> bool:
    if not _scheduled_cancel_condition_valid(condition):
        return False
    return _world_state_path_value(
        world_state,
        str(condition["path"]),
    ) == condition["equals"]


async def _cancel_matching_scheduled_effects(
    db: AsyncSession,
    *,
    instance: MissionInstance,
    actor: ActorContext,
    source_event: RuntimeEvent,
    command_key: str,
    now: datetime,
) -> None:
    pending = (
        await db.execute(
            select(ScheduledEffect)
            .where(
                ScheduledEffect.mission_instance_id == instance.id,
                ScheduledEffect.status == ScheduledEffectStatus.PENDING.value,
                ScheduledEffect.cancellable.is_(True),
            )
            .order_by(ScheduledEffect.created_at, ScheduledEffect.id)
            .with_for_update()
        )
    ).scalars().all()

    for effect in pending:
        if not _scheduled_cancel_condition_matches(
            instance.world_state,
            effect.cancel_condition,
        ):
            continue

        reason_code = str(effect.cancel_condition["reason_code"])
        effect.status = ScheduledEffectStatus.CANCELLED.value
        effect.cancelled_at = instance.simulation_time
        instance.version += 1

        cancelled_event = await _append_runtime_event(
            db,
            instance=instance,
            event_type="scheduled_effect.cancelled",
            source="ENGINE",
            trigger_type="STATE_TRIGGERED",
            trigger_reference=str(source_event.id),
            payload={
                "effect_code": effect.effect_code,
                "label": effect.label,
                "due_at": _scheduled_effect_due_at_text(effect),
                "cancelled_at": instance.simulation_time.isoformat(),
                "reason_code": reason_code,
                "cancel_condition_matched": effect.cancel_condition,
            },
            world_version_before=instance.world_state_version,
            world_version_after=instance.world_state_version,
            idempotency_key=f"{command_key}:cancelled:{effect.id}",
            now=now,
            effective_at=instance.simulation_time,
            causal_parent_ids=[
                str(effect.origin_event_id),
                str(source_event.id),
            ],
            visibility=effect.visibility,
        )

        if effect.visibility == "CANDIDATE":
            await _append_observation(
                db,
                instance=instance,
                source_event=cancelled_event,
                observation_type="SCHEDULED_EFFECT_CANCELLED_OBSERVED",
                factual_statement=(
                    f"Scheduled effect '{effect.effect_code}' was cancelled after "
                    f"world-state condition '{reason_code}' became true."
                ),
                payload={
                    "effect_code": effect.effect_code,
                    "due_at": _scheduled_effect_due_at_text(effect),
                    "cancelled_at": instance.simulation_time.isoformat(),
                    "reason_code": reason_code,
                    "world_version": instance.world_state_version,
                },
                now=now,
            )

        record_event(
            db,
            new_event(
                event_type="mission.scheduled_effect_cancelled.v1",
                aggregate_type="MissionInstance",
                aggregate_id=instance.id,
                aggregate_version=instance.version,
                actor={"type": "SYSTEM", "id": "MISSION_ENGINE"},
                organization_context_id=actor.organization_context_id,
                data_classification="INTERNAL",
                payload={
                    "mission_instance_id": str(instance.id),
                    "scheduled_effect_id": str(effect.id),
                    "effect_code": effect.effect_code,
                    "reason_code": reason_code,
                    "world_state_version": instance.world_state_version,
                },
                trace_id=actor.trace_id,
            ),
        )


async def _apply_matching_state_triggered_effects(
    db: AsyncSession,
    *,
    instance: MissionInstance,
    actor: ActorContext,
    source_event: RuntimeEvent,
    command_key: str,
    now: datetime,
) -> None:
    causal_source = source_event
    while instance.status == MissionInstanceStatus.RUNNING.value:
        pending = (
            await db.execute(
                select(ScheduledEffect)
                .where(
                    ScheduledEffect.mission_instance_id == instance.id,
                    ScheduledEffect.status == ScheduledEffectStatus.PENDING.value,
                    ScheduledEffect.due_at.is_(None),
                    ScheduledEffect.trigger_condition.is_not(None),
                )
                .order_by(ScheduledEffect.created_at, ScheduledEffect.id)
                .with_for_update()
            )
        ).scalars().all()

        effect = next(
            (
                item
                for item in pending
                if isinstance(item.trigger_condition, dict)
                and _scheduled_trigger_condition_matches(
                    instance.world_state,
                    item.trigger_condition,
                )
            ),
            None,
        )
        if effect is None:
            break

        world_before = instance.world_state_version
        try:
            instance.world_state = apply_world_effect(
                instance.world_state,
                effect.effect_payload,
            )
        except ValueError as exc:
            raise AppError(
                "SCHEDULED_EFFECT_INVALID",
                str(exc),
                status_code=422,
            ) from exc

        instance.world_state_version += 1
        instance.version += 1
        effect.status = ScheduledEffectStatus.APPLIED.value
        effect.applied_at = instance.simulation_time

        effect_event = await _append_runtime_event(
            db,
            instance=instance,
            event_type="scheduled_effect.applied",
            source="ENGINE",
            trigger_type="STATE_TRIGGERED",
            trigger_reference=str(causal_source.id),
            payload={
                "effect_code": effect.effect_code,
                "label": effect.label,
                "due_at": None,
                "trigger_mode": "STATE_TRIGGERED",
                "effect_applied": effect.effect_payload,
                "trigger_condition_matched": effect.trigger_condition,
                "world_version_before": world_before,
                "world_version_after": instance.world_state_version,
            },
            world_version_before=world_before,
            world_version_after=instance.world_state_version,
            idempotency_key=f"{command_key}:state-applied:{effect.id}",
            now=now,
            effective_at=instance.simulation_time,
            causal_parent_ids=list(
                dict.fromkeys(
                    [str(effect.origin_event_id), str(causal_source.id)]
                )
            ),
            visibility=effect.visibility,
        )

        if effect.visibility == "CANDIDATE":
            await _append_observation(
                db,
                instance=instance,
                source_event=effect_event,
                observation_type="SCHEDULED_EFFECT_OBSERVED",
                factual_statement=(
                    f"State-triggered effect '{effect.effect_code}' became applicable; "
                    f"world state advanced from version {world_before} to "
                    f"{instance.world_state_version}."
                ),
                payload={
                    "effect_code": effect.effect_code,
                    "due_at": None,
                    "trigger_mode": "STATE_TRIGGERED",
                    "world_version_before": world_before,
                    "world_version_after": instance.world_state_version,
                },
                now=now,
            )

        record_event(
            db,
            new_event(
                event_type="mission.scheduled_effect_applied.v1",
                aggregate_type="MissionInstance",
                aggregate_id=instance.id,
                aggregate_version=instance.version,
                actor={"type": "SYSTEM", "id": "MISSION_ENGINE"},
                organization_context_id=actor.organization_context_id,
                data_classification="INTERNAL",
                payload={
                    "mission_instance_id": str(instance.id),
                    "scheduled_effect_id": str(effect.id),
                    "effect_code": effect.effect_code,
                    "trigger_mode": "STATE_TRIGGERED",
                    "world_version_before": world_before,
                    "world_version_after": instance.world_state_version,
                },
                trace_id=actor.trace_id,
            ),
        )

        await _cancel_matching_scheduled_effects(
            db,
            instance=instance,
            actor=actor,
            source_event=effect_event,
            command_key=f"{command_key}:after-state-applied:{effect.id}",
            now=now,
        )
        causal_source = effect_event


async def _complete_assignment_after_terminal(
    db: AsyncSession,
    *,
    instance: MissionInstance,
    now: datetime,
) -> None:
    if instance.assignment_id is None:
        return
    assignment = (
        await db.execute(
            select(MissionAssignment)
            .where(MissionAssignment.id == instance.assignment_id)
            .with_for_update()
        )
    ).scalar_one_or_none()
    if assignment is None:
        raise AppError(
            "MISSION_ASSIGNMENT_NOT_FOUND",
            "Mission assignment was not found.",
            status_code=500,
        )
    if assignment.status == MissionAssignmentStatus.COMPLETED.value:
        return
    if not assignment_transition_allowed(
        assignment.status,
        MissionAssignmentStatus.COMPLETED.value,
    ):
        raise AppError(
            "MISSION_ASSIGNMENT_TRANSITION_INVALID",
            "Mission assignment cannot transition to COMPLETED.",
            status_code=500,
        )
    assignment.status = MissionAssignmentStatus.COMPLETED.value
    assignment.version += 1
    assignment.completed_at = now


async def _advance_simulation_through(
    db: AsyncSession,
    *,
    instance: MissionInstance,
    actor: ActorContext,
    target_time: datetime,
    command_key: str,
    now: datetime,
    trigger_reference: str,
    causal_parent_ids: list[str] | None = None,
) -> RuntimeEvent:
    from_time = instance.simulation_time
    if target_time < from_time:
        raise AppError(
            "SIMULATION_TIME_REGRESSION",
            "Simulation time cannot move backward.",
            status_code=409,
        )

    instance.simulation_time = target_time
    instance.version += 1
    time_event = await _append_runtime_event(
        db,
        instance=instance,
        event_type="simulation.time_advanced",
        source="ENGINE",
        trigger_type="BEHAVIOUR_TRIGGERED",
        trigger_reference=trigger_reference,
        payload={
            "from_time": from_time.isoformat(),
            "to_time": target_time.isoformat(),
        },
        world_version_before=instance.world_state_version,
        world_version_after=instance.world_state_version,
        idempotency_key=f"{command_key}:time-advanced",
        now=now,
        effective_at=target_time,
        causal_parent_ids=causal_parent_ids,
    )

    due_effects = (
        await db.execute(
            select(ScheduledEffect)
            .where(
                ScheduledEffect.mission_instance_id == instance.id,
                ScheduledEffect.status == ScheduledEffectStatus.PENDING.value,
                ScheduledEffect.due_at.is_not(None),
                ScheduledEffect.due_at <= target_time,
            )
            .order_by(ScheduledEffect.due_at, ScheduledEffect.id)
            .with_for_update()
        )
    ).scalars().all()

    for effect in due_effects:
        if instance.status != MissionInstanceStatus.RUNNING.value:
            break
        if effect.status != ScheduledEffectStatus.PENDING.value:
            continue
        due_at = effect.due_at
        if due_at is None:
            continue

        world_before = instance.world_state_version
        try:
            instance.world_state = apply_world_effect(
                instance.world_state,
                effect.effect_payload,
            )
        except ValueError as exc:
            raise AppError(
                "SCHEDULED_EFFECT_INVALID",
                str(exc),
                status_code=422,
            ) from exc

        instance.world_state_version += 1
        instance.version += 1
        effect.status = ScheduledEffectStatus.APPLIED.value
        effect.applied_at = due_at

        effect_event = await _append_runtime_event(
            db,
            instance=instance,
            event_type="scheduled_effect.applied",
            source="ENGINE",
            trigger_type="SCHEDULED",
            trigger_reference=str(effect.id),
            payload={
                "effect_code": effect.effect_code,
                "label": effect.label,
                "due_at": due_at.isoformat(),
                "trigger_mode": "DUE_AT",
                "effect_applied": effect.effect_payload,
                "world_version_before": world_before,
                "world_version_after": instance.world_state_version,
            },
            world_version_before=world_before,
            world_version_after=instance.world_state_version,
            idempotency_key=f"{command_key}:applied:{effect.id}",
            now=now,
            effective_at=due_at,
            causal_parent_ids=[
                str(effect.origin_event_id),
                str(time_event.id),
            ],
            visibility=effect.visibility,
        )

        if effect.visibility == "CANDIDATE":
            await _append_observation(
                db,
                instance=instance,
                source_event=effect_event,
                observation_type="SCHEDULED_EFFECT_OBSERVED",
                factual_statement=(
                    f"Scheduled effect '{effect.effect_code}' became due at "
                    f"{due_at.isoformat()}; world state advanced from version "
                    f"{world_before} to {instance.world_state_version}."
                ),
                payload={
                    "effect_code": effect.effect_code,
                    "due_at": due_at.isoformat(),
                    "trigger_mode": "DUE_AT",
                    "world_version_before": world_before,
                    "world_version_after": instance.world_state_version,
                },
                now=now,
            )

        record_event(
            db,
            new_event(
                event_type="mission.scheduled_effect_applied.v1",
                aggregate_type="MissionInstance",
                aggregate_id=instance.id,
                aggregate_version=instance.version,
                actor={"type": "SYSTEM", "id": "MISSION_ENGINE"},
                organization_context_id=actor.organization_context_id,
                data_classification="INTERNAL",
                payload={
                    "mission_instance_id": str(instance.id),
                    "scheduled_effect_id": str(effect.id),
                    "effect_code": effect.effect_code,
                    "due_at": due_at.isoformat(),
                    "trigger_mode": "DUE_AT",
                    "world_version_before": world_before,
                    "world_version_after": instance.world_state_version,
                },
                trace_id=actor.trace_id,
            ),
        )

        await _cancel_matching_scheduled_effects(
            db,
            instance=instance,
            actor=actor,
            source_event=effect_event,
            command_key=f"{command_key}:after-applied:{effect.id}",
            now=now,
        )
        await _apply_matching_state_triggered_effects(
            db,
            instance=instance,
            actor=actor,
            source_event=effect_event,
            command_key=f"{command_key}:after-applied:{effect.id}",
            now=now,
        )

        if effect.terminal_status is not None:
            if effect.terminal_status != MissionInstanceStatus.TIME_EXPIRED.value:
                raise AppError(
                    "SCHEDULED_TERMINAL_STATUS_INVALID",
                    "Scheduled terminal status is not supported.",
                    status_code=422,
                )
            if not runtime_transition_allowed(
                instance.status,
                effect.terminal_status,
            ):
                raise AppError(
                    "MISSION_RUNTIME_TRANSITION_INVALID",
                    "Mission cannot enter the scheduled terminal state.",
                    status_code=500,
                )

            previous_status = instance.status
            instance.status = effect.terminal_status
            instance.completed_at = now
            instance.version += 1
            expired_event = await _append_runtime_event(
                db,
                instance=instance,
                event_type="mission.time_expired",
                source="ENGINE",
                trigger_type="SCHEDULED",
                trigger_reference=str(effect.id),
                payload={
                    "from_status": previous_status,
                    "to_status": instance.status,
                    "effect_code": effect.effect_code,
                    "expired_at": due_at.isoformat(),
                },
                world_version_before=instance.world_state_version,
                world_version_after=instance.world_state_version,
                idempotency_key=f"{command_key}:terminal:{effect.id}",
                now=now,
                effective_at=due_at,
                causal_parent_ids=[str(effect_event.id)],
                visibility=effect.visibility,
            )
            if effect.visibility == "CANDIDATE":
                await _append_observation(
                    db,
                    instance=instance,
                    source_event=expired_event,
                    observation_type="MISSION_TIME_EXPIRED",
                    factual_statement=(
                        f"Mission time expired at {due_at.isoformat()} after "
                        f"scheduled effect '{effect.effect_code}'."
                    ),
                    payload={
                        "effect_code": effect.effect_code,
                        "expired_at": due_at.isoformat(),
                        "world_version_before": world_before,
                        "world_version_after": instance.world_state_version,
                    },
                    now=now,
                )
            await _complete_assignment_after_terminal(
                db,
                instance=instance,
                now=now,
            )
            record_event(
                db,
                new_event(
                    event_type="mission.time_expired.v1",
                    aggregate_type="MissionInstance",
                    aggregate_id=instance.id,
                    aggregate_version=instance.version,
                    actor={"type": "SYSTEM", "id": "MISSION_ENGINE"},
                    organization_context_id=actor.organization_context_id,
                    data_classification="INTERNAL",
                    payload={
                        "mission_instance_id": str(instance.id),
                        "scheduled_effect_id": str(effect.id),
                        "effect_code": effect.effect_code,
                        "expired_at": due_at.isoformat(),
                        "world_state_version": instance.world_state_version,
                    },
                    trace_id=actor.trace_id,
                ),
            )

    return time_event


async def _instance_response(
    db: AsyncSession,
    instance: MissionInstance,
) -> MissionInstanceResponse:
    version = await db.get(MissionVersion, instance.mission_version_id)
    if version is None:
        raise AppError(
            "MISSION_VERSION_NOT_FOUND",
            "Mission version not found.",
            status_code=500,
        )
    template = await db.get(MissionTemplate, version.template_id)
    if template is None:
        raise AppError(
            "MISSION_TEMPLATE_NOT_FOUND",
            "Mission template not found.",
            status_code=500,
        )

    events = (
        await db.execute(
            select(RuntimeEvent)
            .where(RuntimeEvent.mission_instance_id == instance.id)
            .order_by(RuntimeEvent.sequence_number)
        )
    ).scalars().all()
    observations = (
        await db.execute(
            select(Observation)
            .where(Observation.mission_instance_id == instance.id)
            .order_by(Observation.sequence_number)
        )
    ).scalars().all()

    actor_instances = (
        await db.execute(
            select(ActorInstance)
            .where(ActorInstance.mission_instance_id == instance.id)
            .order_by(ActorInstance.actor_key)
        )
    ).scalars().all()

    scheduled_effects = (
        await db.execute(
            select(ScheduledEffect)
            .where(
                ScheduledEffect.mission_instance_id == instance.id,
                ScheduledEffect.visibility == "CANDIDATE",
            )
            .order_by(
                ScheduledEffect.created_at,
                ScheduledEffect.effect_code,
            )
        )
    ).scalars().all()

    candidate_events = [
        item
        for item in events
        if item.visibility == "CANDIDATE"
        and candidate_event_visible(item.event_type)
    ]
    candidate_observations = [
        item
        for item in observations
        if candidate_observation_visible(item.observation_type)
    ]
    disclosed_information = [
        {
            "label": event.payload.get("label"),
            "content": event.payload.get("content"),
            "access": event.payload.get("access"),
        }
        for event in candidate_events
        if event.event_type == "information.disclosed"
    ]

    return MissionInstanceResponse(
        id=instance.id,
        version=instance.version,
        assignment_id=instance.assignment_id,
        mission_version_id=instance.mission_version_id,
        template_id=template.id,
        mission_code=template.code,
        title=version.title,
        status=instance.status,
        world_state=project_candidate_visible_state(
            instance.world_state,
            _candidate_visible_paths(version),
        ),
        world_state_version=instance.world_state_version,
        simulation_time=instance.simulation_time,
        scheduled_effects=[
            ScheduledEffectResponse(
                id=item.id,
                effect_code=item.effect_code,
                label=item.label,
                due_at=item.due_at,
                trigger_mode=_scheduled_effect_trigger_mode(item),
                status=item.status,
            )
            for item in scheduled_effects
        ],
        decision_points=version.decision_points,
        information_options=_information_options(version),
        decision_options=_decision_options(version),
        escalation_options=_escalation_options(version),
        delegation_options=_delegation_options(version),
        scope_change_options=_scope_change_options(version),
        no_action_options=_no_action_options(version),
        actors=[
            ActorInstanceResponse(
                id=item.id,
                actor_key=item.actor_key,
                display_name=item.definition_name,
                state=project_candidate_visible_state(
                    item.state,
                    _actor_candidate_visible_paths(
                        _actor_runtime_config(version, item.actor_key) or {}
                    ),
                ),
                state_version=item.state_version,
                communication_options=_actor_communication_options(
                    _actor_runtime_config(version, item.actor_key) or {}
                ),
            )
            for item in actor_instances
        ],
        disclosed_information=disclosed_information,
        audit_events=[
            RuntimeEventResponse(
                id=item.id,
                sequence_number=item.sequence_number,
                event_type=item.event_type,
                source=item.source,
                visibility=item.visibility,
                payload=candidate_event_payload(item.event_type, item.payload),
                world_version_before=item.world_version_before,
                world_version_after=item.world_version_after,
                occurred_at=item.occurred_at,
            )
            for item in candidate_events
        ],
        observations=[
            ObservationResponse(
                id=item.id,
                source_event_id=item.source_event_id,
                sequence_number=item.sequence_number,
                observation_type=item.observation_type,
                factual_statement=item.factual_statement,
                payload=candidate_observation_payload(
                    item.observation_type,
                    item.payload,
                ),
                occurred_at=item.occurred_at,
            )
            for item in candidate_observations
        ],
        created_at=instance.created_at,
        started_at=instance.started_at,
        completed_at=instance.completed_at,
    )


@router.get(
    "/studio/mission-assignment-candidates",
    response_model=list[MissionAssignmentCandidateResponse],
)
async def list_mission_assignment_candidates(
    actor: Annotated[ActorContext, Depends(require_role("ACADEMY_ADMIN"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> list[MissionAssignmentCandidateResponse]:
    rows = (
        await db.execute(
            select(Person)
            .join(
                OrganizationMembership,
                OrganizationMembership.person_id == Person.id,
            )
            .join(
                CandidateJourney,
                CandidateJourney.person_id == Person.id,
            )
            .where(
                OrganizationMembership.organization_id
                == actor.organization_context_id,
                OrganizationMembership.membership_role == "CANDIDATE",
                CandidateJourney.organization_context_id
                == actor.organization_context_id,
                CandidateJourney.state == "ACTIVE",
            )
            .order_by(Person.display_name)
        )
    ).scalars().all()
    return [
        MissionAssignmentCandidateResponse(id=item.id, display_name=item.display_name)
        for item in rows
    ]


@router.get(
    "/studio/mission-assignments",
    response_model=list[MissionAssignmentResponse],
)
async def list_mission_assignments(
    actor: Annotated[ActorContext, Depends(require_role("ACADEMY_ADMIN"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> list[MissionAssignmentResponse]:
    rows = (
        await db.execute(
            select(MissionAssignment, Person, MissionVersion, MissionTemplate)
            .join(Person, MissionAssignment.candidate_id == Person.id)
            .join(
                MissionVersion,
                MissionAssignment.mission_version_id == MissionVersion.id,
            )
            .join(
                MissionTemplate,
                MissionVersion.template_id == MissionTemplate.id,
            )
            .where(
                MissionAssignment.organization_context_id
                == actor.organization_context_id,
                MissionTemplate.organization_context_id
                == actor.organization_context_id,
            )
            .order_by(MissionAssignment.created_at.desc())
        )
    ).all()
    return [
        MissionAssignmentResponse(
            id=assignment.id,
            version=assignment.version,
            candidate_id=assignment.candidate_id,
            candidate_name=person.display_name,
            mission_version_id=assignment.mission_version_id,
            mission_code=template.code,
            mission_title=version.title,
            status=assignment.status,
            assignment_reason=assignment.assignment_reason,
            created_at=assignment.created_at,
            started_at=assignment.started_at,
            completed_at=assignment.completed_at,
        )
        for assignment, person, version, template in rows
    ]


@router.post(
    "/mission-assignments",
    response_model=MissionAssignmentResponse,
    status_code=201,
)
async def create_mission_assignment(
    body: MissionAssignmentCreateRequest,
    actor: Annotated[ActorContext, Depends(require_role("ACADEMY_ADMIN"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> MissionAssignmentResponse:
    version, template = await _load_version_and_template(
        db,
        actor,
        body.mission_version_id,
        require_active=True,
    )
    existing = (
        await db.execute(
            select(MissionAssignment).where(
                MissionAssignment.organization_context_id
                == actor.organization_context_id,
                MissionAssignment.idempotency_key == body.idempotency_key,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        if (
            existing.candidate_id != body.candidate_id
            or existing.mission_version_id != body.mission_version_id
        ):
            raise AppError(
                "IDEMPOTENCY_KEY_REUSED",
                "Idempotency key was already used for a different mission assignment.",
                status_code=409,
            )
        person = await db.get(Person, existing.candidate_id)
        if person is None:
            raise AppError("PERSON_NOT_FOUND", "Candidate was not found.", status_code=404)
        return MissionAssignmentResponse(
            id=existing.id,
            version=existing.version,
            candidate_id=existing.candidate_id,
            candidate_name=person.display_name,
            mission_version_id=existing.mission_version_id,
            mission_code=template.code,
            mission_title=version.title,
            status=existing.status,
            assignment_reason=existing.assignment_reason,
            created_at=existing.created_at,
            started_at=existing.started_at,
            completed_at=existing.completed_at,
        )

    person = await db.get(Person, body.candidate_id)
    if person is None:
        raise AppError("PERSON_NOT_FOUND", "Candidate was not found.", status_code=404)
    await _assert_candidate_eligible(
        db,
        organization_context_id=actor.organization_context_id,
        candidate_id=body.candidate_id,
    )

    now = datetime.now(UTC)
    assignment = MissionAssignment(
        id=uuid4(),
        organization_context_id=actor.organization_context_id,
        candidate_id=body.candidate_id,
        mission_version_id=version.id,
        status=MissionAssignmentStatus.ASSIGNED.value,
        assignment_reason=body.assignment_reason,
        idempotency_key=body.idempotency_key,
        assigned_by=actor.person_id,
        created_at=now,
        started_at=None,
        completed_at=None,
        cancelled_at=None,
    )
    db.add(assignment)
    await db.flush()
    record_event(
        db,
        new_event(
            event_type="mission.assigned.v1",
            aggregate_type="MissionAssignment",
            aggregate_id=assignment.id,
            aggregate_version=assignment.version,
            actor={"type": "PERSON", "id": str(actor.person_id)},
            organization_context_id=actor.organization_context_id,
            data_classification="INTERNAL",
            payload={
                "assignment_id": str(assignment.id),
                "candidate_id": str(assignment.candidate_id),
                "mission_version_id": str(assignment.mission_version_id),
            },
            trace_id=actor.trace_id,
        ),
    )
    await db.commit()
    return MissionAssignmentResponse(
        id=assignment.id,
        version=assignment.version,
        candidate_id=assignment.candidate_id,
        candidate_name=person.display_name,
        mission_version_id=assignment.mission_version_id,
        mission_code=template.code,
        mission_title=version.title,
        status=assignment.status,
        assignment_reason=assignment.assignment_reason,
        created_at=assignment.created_at,
        started_at=assignment.started_at,
        completed_at=assignment.completed_at,
    )


@router.get("/missions/active", response_model=list[MissionCatalogItem])
async def list_active_missions(
    actor: Annotated[ActorContext, Depends(require_role("CANDIDATE"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> list[MissionCatalogItem]:
    rows = (
        await db.execute(
            select(MissionAssignment, MissionVersion, MissionTemplate)
            .join(
                MissionVersion,
                MissionAssignment.mission_version_id == MissionVersion.id,
            )
            .join(
                MissionTemplate,
                MissionVersion.template_id == MissionTemplate.id,
            )
            .where(
                MissionAssignment.organization_context_id
                == actor.organization_context_id,
                MissionAssignment.candidate_id == actor.person_id,
                MissionAssignment.status.in_(
                    [
                        MissionAssignmentStatus.ASSIGNED.value,
                        MissionAssignmentStatus.STARTED.value,
                        MissionAssignmentStatus.COMPLETED.value,
                    ]
                ),
                MissionTemplate.organization_context_id
                == actor.organization_context_id,
            )
            .order_by(MissionAssignment.created_at.desc())
        )
    ).all()
    return [
        MissionCatalogItem(
            assignment_id=assignment.id,
            assignment_status=assignment.status,
            version_id=version.id,
            template_id=template.id,
            code=template.code,
            title=version.title,
            purpose=version.purpose,
            difficulty=version.difficulty,
            decision_points=version.decision_points,
            information_options=_information_options(version),
            decision_options=_decision_options(version),
        )
        for assignment, version, template in rows
    ]


@router.get("/me/mission-instances", response_model=list[MissionInstanceResponse])
async def list_my_mission_instances(
    actor: Annotated[ActorContext, Depends(require_role("CANDIDATE"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> list[MissionInstanceResponse]:
    instances = (
        await db.execute(
            select(MissionInstance)
            .where(
                MissionInstance.organization_context_id
                == actor.organization_context_id,
                MissionInstance.candidate_id == actor.person_id,
            )
            .order_by(MissionInstance.created_at.desc())
        )
    ).scalars().all()
    return [await _instance_response(db, item) for item in instances]


@router.get(
    "/mission-instances/{instance_id}",
    response_model=MissionInstanceResponse,
)
async def get_mission_instance(
    instance_id: UUID,
    actor: Annotated[ActorContext, Depends(require_role("CANDIDATE"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> MissionInstanceResponse:
    instance = await _load_candidate_instance(db, actor, instance_id)
    return await _instance_response(db, instance)


@router.post(
    "/missions/{version_id}/instances",
    response_model=MissionInstanceResponse,
    status_code=201,
)
async def start_mission_instance(
    version_id: UUID,
    body: MissionStartRequest,
    actor: Annotated[ActorContext, Depends(require_role("CANDIDATE"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> MissionInstanceResponse:
    version, template = await _load_version_and_template(
        db,
        actor,
        version_id,
        require_active=False,
    )
    assignment = (
        await db.execute(
            select(MissionAssignment)
            .where(
                MissionAssignment.id == body.assignment_id,
                MissionAssignment.organization_context_id
                == actor.organization_context_id,
                MissionAssignment.candidate_id == actor.person_id,
                MissionAssignment.mission_version_id == version.id,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if assignment is None:
        raise AppError(
            "MISSION_ASSIGNMENT_REQUIRED",
            "A valid mission assignment is required before the mission can start.",
            status_code=403,
        )

    existing_by_assignment = (
        await db.execute(
            select(MissionInstance).where(
                MissionInstance.assignment_id == assignment.id
            )
        )
    ).scalar_one_or_none()
    if existing_by_assignment is not None:
        return await _instance_response(db, existing_by_assignment)

    if version.status != "ACTIVE":
        raise AppError(
            "MISSION_VERSION_NOT_ACTIVE",
            "Only an active mission version can be started.",
            status_code=409,
        )

    if assignment.status != MissionAssignmentStatus.ASSIGNED.value:
        raise AppError(
            "MISSION_ASSIGNMENT_NOT_STARTABLE",
            "Mission assignment is not in ASSIGNED state.",
            status_code=409,
            details={"assignment_status": assignment.status},
        )

    checks = await _assert_candidate_eligible(
        db,
        organization_context_id=actor.organization_context_id,
        candidate_id=actor.person_id,
    )

    runtime = _runtime_config(version)
    initial_state = runtime.get("initial_state")
    if not isinstance(initial_state, dict):
        raise AppError(
            "MISSION_RUNTIME_DEFINITION_INVALID",
            "Mission runtime initial_state is required.",
            status_code=422,
        )
    decision_effects = runtime.get("decision_effects")
    if not isinstance(decision_effects, dict) or not decision_effects:
        raise AppError(
            "MISSION_RUNTIME_DEFINITION_INVALID",
            "Mission runtime decision_effects are required.",
            status_code=422,
        )
    delegation_options = runtime.get("delegation_options", [])
    if (
        isinstance(delegation_options, list)
        and delegation_options
        and not delegation_preserves_candidate_accountability(
            initial_state,
            initial_state,
        )
    ):
        raise AppError(
            "MISSION_DELEGATION_DEFINITION_INVALID",
            "Missions with delegation must declare mission.accountability_owner=CANDIDATE.",
            status_code=422,
        )
    scope_change_options = runtime.get("scope_change_options", [])
    if (
        isinstance(scope_change_options, list)
        and scope_change_options
        and not preserves_candidate_accountability(
            initial_state,
            initial_state,
        )
    ):
        raise AppError(
            "MISSION_SCOPE_CHANGE_DEFINITION_INVALID",
            "Missions with scope changes must declare mission.accountability_owner=CANDIDATE.",
            status_code=422,
        )

    now = datetime.now(UTC)
    instance_id = uuid4()
    instance = MissionInstance(
        id=instance_id,
        organization_context_id=actor.organization_context_id,
        mission_version_id=version.id,
        assignment_id=assignment.id,
        candidate_id=actor.person_id,
        status=MissionInstanceStatus.CREATED.value,
        world_state=initial_state,
        world_state_version=1,
        simulation_seed=instance_id.int % 2_147_483_647,
        simulation_time=now,
        start_idempotency_key=body.idempotency_key,
        created_at=now,
        started_at=None,
        completed_at=None,
    )
    db.add(instance)
    await db.flush()

    defined_actor_names = {
        item.get("name")
        for item in version.actors
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }
    for actor_key, actor_config_value in _actor_runtime_configs(version).items():
        if not isinstance(actor_key, str) or not actor_key:
            raise AppError(
                "MISSION_ACTOR_RUNTIME_DEFINITION_INVALID",
                "Actor runtime keys must be non-empty strings.",
                status_code=422,
            )
        if not isinstance(actor_config_value, dict):
            raise AppError(
                "MISSION_ACTOR_RUNTIME_DEFINITION_INVALID",
                "Actor runtime configuration must be an object.",
                status_code=422,
            )
        definition_name = actor_config_value.get("definition_name")
        initial_actor_state = actor_config_value.get("initial_state")
        if (
            not isinstance(definition_name, str)
            or definition_name not in defined_actor_names
            or not isinstance(initial_actor_state, dict)
        ):
            raise AppError(
                "MISSION_ACTOR_RUNTIME_DEFINITION_INVALID",
                "Actor runtime must reference a Mission actor and define initial_state.",
                status_code=422,
            )
        try:
            validated_actor_state = apply_actor_effect({}, initial_actor_state)
        except ValueError as exc:
            raise AppError(
                "MISSION_ACTOR_RUNTIME_DEFINITION_INVALID",
                str(exc),
                status_code=422,
            ) from exc
        db.add(
            ActorInstance(
                id=uuid4(),
                mission_instance_id=instance.id,
                actor_key=actor_key,
                definition_name=definition_name,
                state=validated_actor_state,
                state_version=1,
                created_at=now,
                updated_at=now,
            )
        )
    await db.flush()

    previous = instance.status
    if not runtime_transition_allowed(
        previous,
        MissionInstanceStatus.ELIGIBILITY_CHECK.value,
    ):
        raise AppError(
            "MISSION_RUNTIME_TRANSITION_INVALID",
            "Mission runtime transition is invalid.",
            status_code=500,
        )
    instance.status = MissionInstanceStatus.ELIGIBILITY_CHECK.value
    instance.version += 1
    eligibility_state_event = await _append_runtime_event(
        db,
        instance=instance,
        event_type="mission.status_changed",
        source="ENGINE",
        trigger_type="BEHAVIOUR_TRIGGERED",
        trigger_reference=str(actor.person_id),
        payload={
            "from_status": previous,
            "to_status": instance.status,
            "assignment_id": str(assignment.id),
            "mission_version_id": str(version.id),
        },
        world_version_before=1,
        world_version_after=1,
        idempotency_key=f"{body.idempotency_key}:status:eligibility",
        now=now,
    )
    eligibility_event = await _append_runtime_event(
        db,
        instance=instance,
        event_type="mission.eligibility_passed",
        source="ENGINE",
        trigger_type="STATE_TRIGGERED",
        trigger_reference=str(assignment.id),
        payload={
            "assignment_id": str(assignment.id),
            "checks": checks,
        },
        world_version_before=1,
        world_version_after=1,
        idempotency_key=f"{body.idempotency_key}:eligibility",
        now=now,
        causal_parent_ids=[str(eligibility_state_event.id)],
    )

    previous_event_id = eligibility_event.id
    for index, target in enumerate(
        (
            MissionInstanceStatus.READY,
            MissionInstanceStatus.RUNNING,
        ),
        start=1,
    ):
        previous = instance.status
        if not runtime_transition_allowed(previous, target.value):
            raise AppError(
                "MISSION_RUNTIME_TRANSITION_INVALID",
                "Mission runtime transition is invalid.",
                status_code=500,
            )
        instance.status = target.value
        instance.version += 1
        if target == MissionInstanceStatus.RUNNING:
            instance.started_at = now
        event = await _append_runtime_event(
            db,
            instance=instance,
            event_type="mission.status_changed",
            source="ENGINE",
            trigger_type="STATE_TRIGGERED",
            trigger_reference=str(assignment.id),
            payload={
                "from_status": previous,
                "to_status": target.value,
                "assignment_id": str(assignment.id),
                "mission_version_id": str(version.id),
            },
            world_version_before=instance.world_state_version,
            world_version_after=instance.world_state_version,
            idempotency_key=f"{body.idempotency_key}:status:{index}",
            now=now,
            causal_parent_ids=[str(previous_event_id)],
        )
        previous_event_id = event.id

    if not assignment_transition_allowed(
        assignment.status,
        MissionAssignmentStatus.STARTED.value,
    ):
        raise AppError(
            "MISSION_ASSIGNMENT_TRANSITION_INVALID",
            "Mission assignment cannot transition to STARTED.",
            status_code=500,
        )
    assignment.status = MissionAssignmentStatus.STARTED.value
    assignment.version += 1
    assignment.started_at = now

    start_event = await _append_runtime_event(
        db,
        instance=instance,
        event_type="mission.started",
        source="ENGINE",
        trigger_type="BEHAVIOUR_TRIGGERED",
        trigger_reference=str(actor.person_id),
        payload={
            "assignment_id": str(assignment.id),
            "mission_version_id": str(version.id),
            "mission_code": template.code,
            "simulation_seed": instance.simulation_seed,
        },
        world_version_before=1,
        world_version_after=1,
        idempotency_key=f"{body.idempotency_key}:started",
        now=now,
        causal_parent_ids=[str(previous_event_id)],
    )
    await _append_observation(
        db,
        instance=instance,
        source_event=start_event,
        observation_type="MISSION_STARTED",
        factual_statement=(
            f"Assigned mission {template.code} started for the candidate at world state version 1."
        ),
        payload={
            "assignment_id": str(assignment.id),
            "mission_version_id": str(version.id),
        },
        now=now,
    )

    record_event(
        db,
        new_event(
            event_type="mission.started.v1",
            aggregate_type="MissionInstance",
            aggregate_id=instance.id,
            aggregate_version=instance.version,
            actor={"type": "PERSON", "id": str(actor.person_id)},
            organization_context_id=actor.organization_context_id,
            data_classification="INTERNAL",
            payload={
                "assignment_id": str(assignment.id),
                "mission_instance_id": str(instance.id),
                "mission_version_id": str(version.id),
                "status": instance.status,
                "world_state_version": instance.world_state_version,
            },
            trace_id=actor.trace_id,
        ),
    )
    await db.commit()
    return await _instance_response(db, instance)


@router.post(
    "/mission-instances/{instance_id}/advance-to-next-event",
    response_model=MissionInstanceResponse,
)
async def advance_to_next_world_event(
    instance_id: UUID,
    body: AdvanceSimulationRequest,
    actor: Annotated[ActorContext, Depends(require_role("CANDIDATE"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> MissionInstanceResponse:
    instance = await _load_candidate_instance(
        db,
        actor,
        instance_id,
        for_update=True,
    )
    event_idempotency_key = f"{body.idempotency_key}:time-advanced"
    existing = (
        await db.execute(
            select(RuntimeEvent.id).where(
                RuntimeEvent.mission_instance_id == instance.id,
                RuntimeEvent.idempotency_key == event_idempotency_key,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return await _instance_response(db, instance)

    if instance.status != MissionInstanceStatus.RUNNING.value:
        raise AppError(
            "MISSION_INSTANCE_NOT_RUNNING",
            "Mission instance is not running.",
            status_code=409,
        )
    if instance.world_state_version != body.expected_world_version:
        raise AppError(
            "WORLD_STATE_VERSION_CONFLICT",
            "Mission world state changed. Refresh and retry.",
            status_code=409,
            details={
                "expected_version": body.expected_world_version,
                "current_version": instance.world_state_version,
            },
        )

    next_effect = (
        await db.execute(
            select(ScheduledEffect)
            .where(
                ScheduledEffect.mission_instance_id == instance.id,
                ScheduledEffect.status == ScheduledEffectStatus.PENDING.value,
                ScheduledEffect.due_at.is_not(None),
            )
            .order_by(ScheduledEffect.due_at, ScheduledEffect.id)
            .limit(1)
            .with_for_update()
        )
    ).scalar_one_or_none()
    if next_effect is None:
        raise AppError(
            "NO_PENDING_SCHEDULED_EFFECT",
            "There is no pending world event to advance to.",
            status_code=409,
        )

    next_due_at = next_effect.due_at
    if next_due_at is None:
        raise AppError(
            "SCHEDULED_EFFECT_TRIGGER_INVALID",
            "Next timed effect is missing due_at.",
            status_code=500,
        )

    now = datetime.now(UTC)
    target_time = max(instance.simulation_time, next_due_at)
    await _advance_simulation_through(
        db,
        instance=instance,
        actor=actor,
        target_time=target_time,
        command_key=body.idempotency_key,
        now=now,
        trigger_reference=str(actor.person_id),
    )

    await db.commit()
    return await _instance_response(db, instance)


@router.post(
    "/mission-instances/{instance_id}/actions",
    response_model=MissionInstanceResponse,
)
async def submit_mission_action(
    instance_id: UUID,
    body: MissionActionRequest,
    actor: Annotated[ActorContext, Depends(require_role("CANDIDATE"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> MissionInstanceResponse:
    instance = await _load_candidate_instance(
        db,
        actor,
        instance_id,
        for_update=True,
    )
    existing_action = (
        await db.execute(
            select(CandidateAction.id).where(
                CandidateAction.mission_instance_id == instance.id,
                CandidateAction.idempotency_key == body.idempotency_key,
            )
        )
    ).scalar_one_or_none()
    if existing_action is not None:
        return await _instance_response(db, instance)

    if instance.status != MissionInstanceStatus.RUNNING.value:
        raise AppError(
            "MISSION_INSTANCE_NOT_RUNNING",
            "Mission instance is not running.",
            status_code=409,
        )
    if instance.world_state_version != body.expected_world_version:
        raise AppError(
            "WORLD_STATE_VERSION_CONFLICT",
            "Mission world state changed. Refresh and retry.",
            status_code=409,
            details={
                "expected_version": body.expected_world_version,
                "current_version": instance.world_state_version,
            },
        )

    version, _ = await _load_version_and_template(
        db,
        actor,
        instance.mission_version_id,
        require_active=False,
    )
    now = datetime.now(UTC)
    action = CandidateAction(
        id=uuid4(),
        mission_instance_id=instance.id,
        candidate_id=actor.person_id,
        action_type=body.action_type.value,
        target=body.target,
        payload=body.payload,
        reasoning=body.reasoning,
        confidence=body.confidence,
        requested_at=now,
        effective_at=now,
        resource_cost=body.resource_cost,
        mode=body.mode,
        provenance=body.provenance,
        idempotency_key=body.idempotency_key,
    )
    db.add(action)
    await db.flush()

    before = instance.world_state_version
    event: RuntimeEvent

    if body.action_type == MissionActionType.REQUEST_INFORMATION:
        label = body.payload.get("label")
        if not isinstance(label, str) or not label:
            raise AppError(
                "INFORMATION_LABEL_REQUIRED",
                "Information label is required.",
                status_code=422,
            )
        information = next(
            (item for item in version.information_items if item.get("label") == label),
            None,
        )
        if information is None or information.get("access") not in {
            "DEFAULT",
            "DISCOVERABLE",
        }:
            raise AppError(
                "INFORMATION_NOT_AVAILABLE",
                "Requested information is not available through this action.",
                status_code=422,
            )
        instance.version += 1
        event = await _append_runtime_event(
            db,
            instance=instance,
            event_type="information.disclosed",
            source="ENGINE",
            trigger_type="BEHAVIOUR_TRIGGERED",
            trigger_reference=str(action.id),
            payload={
                "label": label,
                "content": information.get("content"),
                "access": information.get("access"),
            },
            world_version_before=before,
            world_version_after=before,
            idempotency_key=f"{body.idempotency_key}:event",
            now=now,
        )
        await _append_observation(
            db,
            instance=instance,
            source_event=event,
            observation_type="INFORMATION_REQUESTED",
            factual_statement=(
                f"Candidate requested information '{label}' at world state version {before}."
            ),
            payload={"label": label, "access": information.get("access")},
            now=now,
        )

    elif body.action_type == MissionActionType.COMMUNICATE:
        actor_key = body.target
        if not isinstance(actor_key, str) or not actor_key:
            raise AppError(
                "ACTOR_TARGET_REQUIRED",
                "COMMUNICATE requires an Actor target.",
                status_code=422,
            )
        if body.expected_actor_version is None:
            raise AppError(
                "ACTOR_STATE_VERSION_REQUIRED",
                "COMMUNICATE requires expected_actor_version.",
                status_code=422,
            )

        actor_instance = (
            await db.execute(
                select(ActorInstance)
                .where(
                    ActorInstance.mission_instance_id == instance.id,
                    ActorInstance.actor_key == actor_key,
                )
                .with_for_update()
            )
        ).scalar_one_or_none()
        if actor_instance is None:
            raise AppError(
                "MISSION_ACTOR_NOT_FOUND",
                "Mission actor was not found.",
                status_code=404,
            )
        if actor_instance.state_version != body.expected_actor_version:
            raise AppError(
                "ACTOR_STATE_VERSION_CONFLICT",
                "Actor state changed. Refresh and retry.",
                status_code=409,
                details={
                    "expected_version": body.expected_actor_version,
                    "current_version": actor_instance.state_version,
                },
            )

        communication_code = body.payload.get("communication_code")
        utterance = body.payload.get("utterance")
        if not isinstance(communication_code, str) or not communication_code:
            raise AppError(
                "COMMUNICATION_CODE_REQUIRED",
                "communication_code is required.",
                status_code=422,
            )
        if not isinstance(utterance, str) or not utterance.strip():
            raise AppError(
                "COMMUNICATION_UTTERANCE_REQUIRED",
                "Candidate utterance is required.",
                status_code=422,
            )

        actor_config = _actor_runtime_config(version, actor_key)
        if actor_config is None:
            raise AppError(
                "MISSION_ACTOR_RUNTIME_DEFINITION_INVALID",
                "Actor runtime configuration is missing.",
                status_code=422,
            )
        raw_options = actor_config.get("communication_options", [])
        option = next(
            (
                item
                for item in raw_options
                if isinstance(item, dict)
                and item.get("code") == communication_code
            ),
            None,
        ) if isinstance(raw_options, list) else None
        if option is None:
            raise AppError(
                "COMMUNICATION_NOT_ALLOWED",
                "Communication strategy is not defined for this actor.",
                status_code=422,
            )

        reply = option.get("reply")
        actor_effect = option.get("effect")
        if not isinstance(reply, str) or not reply or not isinstance(actor_effect, dict):
            raise AppError(
                "MISSION_ACTOR_RUNTIME_DEFINITION_INVALID",
                "Communication rule must define reply and effect.",
                status_code=422,
            )

        actor_before = actor_instance.state_version
        try:
            actor_instance.state = apply_actor_effect(
                actor_instance.state,
                actor_effect,
            )
        except ValueError as exc:
            raise AppError(
                "MISSION_ACTOR_EFFECT_INVALID",
                str(exc),
                status_code=422,
            ) from exc
        actor_instance.state_version += 1
        actor_instance.updated_at = now
        instance.version += 1

        communication_event = await _append_runtime_event(
            db,
            instance=instance,
            event_type="communication.sent",
            source="CANDIDATE",
            trigger_type="BEHAVIOUR_TRIGGERED",
            trigger_reference=str(action.id),
            payload={
                "actor_key": actor_key,
                "communication_code": communication_code,
                "utterance": utterance.strip(),
            },
            world_version_before=before,
            world_version_after=before,
            idempotency_key=f"{body.idempotency_key}:communication",
            now=now,
        )
        event = await _append_runtime_event(
            db,
            instance=instance,
            event_type="actor.responded",
            source="ENGINE",
            trigger_type="STATE_TRIGGERED",
            trigger_reference=str(communication_event.id),
            payload={
                "actor_key": actor_key,
                "communication_code": communication_code,
                "reply": reply,
                "actor_effect_applied": actor_effect,
                "actor_state_version_before": actor_before,
                "actor_state_version_after": actor_instance.state_version,
            },
            world_version_before=before,
            world_version_after=before,
            idempotency_key=f"{body.idempotency_key}:actor-response",
            now=now,
            causal_parent_ids=[str(communication_event.id)],
        )
        await _append_observation(
            db,
            instance=instance,
            source_event=event,
            observation_type="ACTOR_RESPONSE_OBSERVED",
            factual_statement=(
                f"Candidate communicated with actor '{actor_key}' using "
                f"'{communication_code}'; actor state advanced from version "
                f"{actor_before} to {actor_instance.state_version}."
            ),
            payload={
                "actor_key": actor_key,
                "communication_code": communication_code,
                "actor_state_version_before": actor_before,
                "actor_state_version_after": actor_instance.state_version,
            },
            now=now,
        )
        record_event(
            db,
            new_event(
                event_type="mission.actor_state_changed.v1",
                aggregate_type="ActorInstance",
                aggregate_id=actor_instance.id,
                aggregate_version=actor_instance.state_version,
                actor={"type": "PERSON", "id": str(actor.person_id)},
                organization_context_id=actor.organization_context_id,
                data_classification="INTERNAL",
                payload={
                    "mission_instance_id": str(instance.id),
                    "actor_instance_id": str(actor_instance.id),
                    "actor_key": actor_key,
                    "communication_code": communication_code,
                    "actor_state_version_before": actor_before,
                    "actor_state_version_after": actor_instance.state_version,
                },
                trace_id=actor.trace_id,
            ),
        )

    elif body.action_type == MissionActionType.ESCALATE:
        actor_key = body.target
        if not isinstance(actor_key, str) or not actor_key:
            raise AppError(
                "ACTOR_TARGET_REQUIRED",
                "ESCALATE requires an Actor target.",
                status_code=422,
            )
        if body.expected_actor_version is None:
            raise AppError(
                "ACTOR_STATE_VERSION_REQUIRED",
                "ESCALATE requires expected_actor_version.",
                status_code=422,
            )

        actor_instance = (
            await db.execute(
                select(ActorInstance)
                .where(
                    ActorInstance.mission_instance_id == instance.id,
                    ActorInstance.actor_key == actor_key,
                )
                .with_for_update()
            )
        ).scalar_one_or_none()
        if actor_instance is None:
            raise AppError(
                "MISSION_ACTOR_NOT_FOUND",
                "Mission actor was not found.",
                status_code=404,
            )
        if actor_instance.state_version != body.expected_actor_version:
            raise AppError(
                "ACTOR_STATE_VERSION_CONFLICT",
                "Actor state changed. Refresh and retry.",
                status_code=409,
                details={
                    "expected_version": body.expected_actor_version,
                    "current_version": actor_instance.state_version,
                },
            )

        escalation_code = body.payload.get("escalation_code")
        rationale = body.payload.get("rationale")
        if not isinstance(escalation_code, str) or not escalation_code:
            raise AppError(
                "ESCALATION_CODE_REQUIRED",
                "escalation_code is required.",
                status_code=422,
            )
        if not isinstance(rationale, str) or not rationale.strip():
            raise AppError(
                "ESCALATION_RATIONALE_REQUIRED",
                "Candidate escalation rationale is required.",
                status_code=422,
            )

        raw_options = _runtime_config(version).get("escalation_options", [])
        option = next(
            (
                item
                for item in raw_options
                if isinstance(item, dict)
                and item.get("code") == escalation_code
                and item.get("actor_key") == actor_key
            ),
            None,
        ) if isinstance(raw_options, list) else None
        if option is None:
            raise AppError(
                "ESCALATION_NOT_ALLOWED",
                "Escalation is not defined for this actor.",
                status_code=422,
            )

        response = option.get("response")
        world_effect = option.get("world_effect")
        actor_effect = option.get("actor_effect")
        if (
            not isinstance(response, str)
            or not response
            or not isinstance(world_effect, dict)
            or not isinstance(actor_effect, dict)
        ):
            raise AppError(
                "MISSION_ESCALATION_DEFINITION_INVALID",
                "Escalation rule must define response, world_effect and actor_effect.",
                status_code=422,
            )

        actor_before = actor_instance.state_version
        try:
            next_world = apply_world_effect(instance.world_state, world_effect)
            next_actor = apply_actor_effect(actor_instance.state, actor_effect)
        except ValueError as exc:
            raise AppError(
                "MISSION_ESCALATION_EFFECT_INVALID",
                str(exc),
                status_code=422,
            ) from exc

        instance.world_state = next_world
        instance.world_state_version += 1
        instance.version += 1
        actor_instance.state = next_actor
        actor_instance.state_version += 1
        actor_instance.updated_at = now

        requested_event = await _append_runtime_event(
            db,
            instance=instance,
            event_type="escalation.requested",
            source="CANDIDATE",
            trigger_type="BEHAVIOUR_TRIGGERED",
            trigger_reference=str(action.id),
            payload={
                "actor_key": actor_key,
                "escalation_code": escalation_code,
                "rationale": rationale.strip(),
            },
            world_version_before=before,
            world_version_after=before,
            idempotency_key=f"{body.idempotency_key}:requested",
            now=now,
        )
        event = await _append_runtime_event(
            db,
            instance=instance,
            event_type="escalation.accepted",
            source="ENGINE",
            trigger_type="STATE_TRIGGERED",
            trigger_reference=str(requested_event.id),
            payload={
                "actor_key": actor_key,
                "escalation_code": escalation_code,
                "response": response,
                "world_effect_applied": world_effect,
                "actor_effect_applied": actor_effect,
                "world_version_before": before,
                "world_version_after": instance.world_state_version,
                "actor_state_version_before": actor_before,
                "actor_state_version_after": actor_instance.state_version,
            },
            world_version_before=before,
            world_version_after=instance.world_state_version,
            idempotency_key=f"{body.idempotency_key}:accepted",
            now=now,
            causal_parent_ids=[str(requested_event.id)],
        )
        await _append_observation(
            db,
            instance=instance,
            source_event=event,
            observation_type="ESCALATION_OBSERVED",
            factual_statement=(
                f"Candidate escalated '{escalation_code}' to actor '{actor_key}'; "
                f"world state advanced from version {before} to "
                f"{instance.world_state_version} and actor state advanced from "
                f"version {actor_before} to {actor_instance.state_version}."
            ),
            payload={
                "actor_key": actor_key,
                "escalation_code": escalation_code,
                "world_version_before": before,
                "world_version_after": instance.world_state_version,
                "actor_state_version_before": actor_before,
                "actor_state_version_after": actor_instance.state_version,
            },
            now=now,
        )
        raw_scheduled_effects = option.get("scheduled_effects", [])
        if not isinstance(raw_scheduled_effects, list):
            raise AppError(
                "MISSION_SCHEDULED_EFFECT_DEFINITION_INVALID",
                "scheduled_effects must be a list.",
                status_code=422,
            )
        for index, scheduled_definition in enumerate(raw_scheduled_effects):
            if not isinstance(scheduled_definition, dict):
                raise AppError(
                    "MISSION_SCHEDULED_EFFECT_DEFINITION_INVALID",
                    "Scheduled effect definition must be an object.",
                    status_code=422,
                )
            effect_code = scheduled_definition.get("code")
            label = scheduled_definition.get("label")
            delay_seconds = scheduled_definition.get("due_after_seconds")
            trigger_condition = scheduled_definition.get("trigger_condition")
            effect_payload = scheduled_definition.get("effect")
            terminal_status = scheduled_definition.get("terminal_status")
            visibility = scheduled_definition.get("visibility", "CANDIDATE")
            cancellable = scheduled_definition.get("cancellable", False)
            cancel_condition = scheduled_definition.get("cancel_condition", {})
            has_due_definition = delay_seconds is not None
            has_trigger_definition = trigger_condition is not None
            due_definition_valid = (
                isinstance(delay_seconds, int)
                and not isinstance(delay_seconds, bool)
                and delay_seconds > 0
            )
            trigger_definition_valid = (
                isinstance(trigger_condition, dict)
                and _scheduled_trigger_condition_valid(trigger_condition)
            )
            if (
                not isinstance(effect_code, str)
                or not effect_code
                or not isinstance(label, str)
                or not label
                or has_due_definition == has_trigger_definition
                or (has_due_definition and not due_definition_valid)
                or (has_trigger_definition and not trigger_definition_valid)
                or not isinstance(effect_payload, dict)
                or (
                    terminal_status is not None
                    and terminal_status != MissionInstanceStatus.TIME_EXPIRED.value
                )
                or (
                    has_trigger_definition
                    and terminal_status is not None
                )
                or visibility not in {"CANDIDATE", "INTERNAL"}
                or not isinstance(cancellable, bool)
                or not isinstance(cancel_condition, dict)
                or (
                    cancellable
                    and not _scheduled_cancel_condition_valid(cancel_condition)
                )
                or (
                    not cancellable
                    and bool(cancel_condition)
                )
            ):
                raise AppError(
                    "MISSION_SCHEDULED_EFFECT_DEFINITION_INVALID",
                    "Scheduled effect must define exactly one deterministic trigger and a valid cancellation policy.",
                    status_code=422,
                )
            try:
                apply_world_effect(instance.world_state, effect_payload)
            except ValueError as exc:
                raise AppError(
                    "MISSION_SCHEDULED_EFFECT_DEFINITION_INVALID",
                    str(exc),
                    status_code=422,
                ) from exc

            due_at = (
                instance.simulation_time + timedelta(seconds=delay_seconds)
                if due_definition_valid and isinstance(delay_seconds, int)
                else None
            )
            stored_trigger_condition = (
                trigger_condition
                if trigger_definition_valid and isinstance(trigger_condition, dict)
                else None
            )
            trigger_mode = "DUE_AT" if due_at is not None else "STATE_TRIGGERED"
            scheduled_effect = ScheduledEffect(
                id=uuid4(),
                mission_instance_id=instance.id,
                origin_event_id=event.id,
                effect_code=effect_code,
                label=label,
                due_at=due_at,
                trigger_condition=stored_trigger_condition,
                effect_payload=effect_payload,
                terminal_status=terminal_status,
                cancellable=cancellable,
                cancel_condition=cancel_condition,
                visibility=visibility,
                status=ScheduledEffectStatus.PENDING.value,
                created_at=now,
                applied_at=None,
                cancelled_at=None,
                idempotency_key=f"{body.idempotency_key}:scheduled:{index}:{effect_code}",
            )
            db.add(scheduled_effect)
            await db.flush()
            await _append_runtime_event(
                db,
                instance=instance,
                event_type="scheduled_effect.created",
                source="ENGINE",
                trigger_type="STATE_TRIGGERED",
                trigger_reference=str(event.id),
                payload={
                    "effect_code": effect_code,
                    "label": label,
                    "due_at": due_at.isoformat() if due_at is not None else None,
                    "trigger_mode": trigger_mode,
                    "trigger_condition_defined": stored_trigger_condition,
                },
                world_version_before=instance.world_state_version,
                world_version_after=instance.world_state_version,
                idempotency_key=f"{body.idempotency_key}:scheduled-event:{index}:{effect_code}",
                now=now,
                effective_at=instance.simulation_time,
                causal_parent_ids=[str(event.id)],
                visibility=visibility,
            )

        record_event(
            db,
            new_event(
                event_type="mission.escalation_processed.v1",
                aggregate_type="MissionInstance",
                aggregate_id=instance.id,
                aggregate_version=instance.version,
                actor={"type": "PERSON", "id": str(actor.person_id)},
                organization_context_id=actor.organization_context_id,
                data_classification="INTERNAL",
                payload={
                    "mission_instance_id": str(instance.id),
                    "actor_instance_id": str(actor_instance.id),
                    "actor_key": actor_key,
                    "escalation_code": escalation_code,
                    "world_version_before": before,
                    "world_version_after": instance.world_state_version,
                    "actor_state_version_before": actor_before,
                    "actor_state_version_after": actor_instance.state_version,
                },
                trace_id=actor.trace_id,
            ),
        )

        await _cancel_matching_scheduled_effects(
            db,
            instance=instance,
            actor=actor,
            source_event=event,
            command_key=f"{body.idempotency_key}:after-escalation",
            now=now,
        )
        await _apply_matching_state_triggered_effects(
            db,
            instance=instance,
            actor=actor,
            source_event=event,
            command_key=f"{body.idempotency_key}:after-escalation",
            now=now,
        )

    elif body.action_type == MissionActionType.DELEGATE:
        actor_key = body.target
        if not isinstance(actor_key, str) or not actor_key:
            raise AppError(
                "ACTOR_TARGET_REQUIRED",
                "DELEGATE requires an Actor target.",
                status_code=422,
            )
        if body.expected_actor_version is None:
            raise AppError(
                "ACTOR_STATE_VERSION_REQUIRED",
                "DELEGATE requires expected_actor_version.",
                status_code=422,
            )

        actor_instance = (
            await db.execute(
                select(ActorInstance)
                .where(
                    ActorInstance.mission_instance_id == instance.id,
                    ActorInstance.actor_key == actor_key,
                )
                .with_for_update()
            )
        ).scalar_one_or_none()
        if actor_instance is None:
            raise AppError(
                "MISSION_ACTOR_NOT_FOUND",
                "Mission actor was not found.",
                status_code=404,
            )
        if actor_instance.state_version != body.expected_actor_version:
            raise AppError(
                "ACTOR_STATE_VERSION_CONFLICT",
                "Actor state changed. Refresh and retry.",
                status_code=409,
                details={
                    "expected_version": body.expected_actor_version,
                    "current_version": actor_instance.state_version,
                },
            )

        delegation_code = body.payload.get("delegation_code")
        rationale = body.payload.get("rationale")
        if not isinstance(delegation_code, str) or not delegation_code:
            raise AppError(
                "DELEGATION_CODE_REQUIRED",
                "delegation_code is required.",
                status_code=422,
            )
        if not isinstance(rationale, str) or not rationale.strip():
            raise AppError(
                "DELEGATION_RATIONALE_REQUIRED",
                "Candidate delegation rationale is required.",
                status_code=422,
            )

        raw_options = _runtime_config(version).get("delegation_options", [])
        option = next(
            (
                item
                for item in raw_options
                if isinstance(item, dict)
                and item.get("code") == delegation_code
                and item.get("actor_key") == actor_key
            ),
            None,
        ) if isinstance(raw_options, list) else None
        if option is None:
            raise AppError(
                "DELEGATION_NOT_ALLOWED",
                "Delegation is not defined for this actor.",
                status_code=422,
            )

        response = option.get("response")
        world_effect = option.get("world_effect")
        actor_effect = option.get("actor_effect")
        if (
            not isinstance(response, str)
            or not response
            or not isinstance(world_effect, dict)
            or not isinstance(actor_effect, dict)
        ):
            raise AppError(
                "MISSION_DELEGATION_DEFINITION_INVALID",
                "Delegation rule must define response, world_effect and actor_effect.",
                status_code=422,
            )

        actor_before = actor_instance.state_version
        try:
            next_world = apply_world_effect(instance.world_state, world_effect)
            next_actor = apply_actor_effect(actor_instance.state, actor_effect)
        except ValueError as exc:
            raise AppError(
                "MISSION_DELEGATION_EFFECT_INVALID",
                str(exc),
                status_code=422,
            ) from exc
        if not delegation_preserves_candidate_accountability(
            instance.world_state,
            next_world,
        ):
            raise AppError(
                "DELEGATION_ACCOUNTABILITY_TRANSFER_FORBIDDEN",
                "Delegation cannot transfer Candidate accountability for the Mission.",
                status_code=422,
            )

        instance.world_state = next_world
        instance.world_state_version += 1
        instance.version += 1
        actor_instance.state = next_actor
        actor_instance.state_version += 1
        actor_instance.updated_at = now

        requested_event = await _append_runtime_event(
            db,
            instance=instance,
            event_type="delegation.requested",
            source="CANDIDATE",
            trigger_type="BEHAVIOUR_TRIGGERED",
            trigger_reference=str(action.id),
            payload={
                "actor_key": actor_key,
                "delegation_code": delegation_code,
                "rationale": rationale.strip(),
            },
            world_version_before=before,
            world_version_after=before,
            idempotency_key=f"{body.idempotency_key}:requested",
            now=now,
        )
        event = await _append_runtime_event(
            db,
            instance=instance,
            event_type="delegation.accepted",
            source="ENGINE",
            trigger_type="STATE_TRIGGERED",
            trigger_reference=str(requested_event.id),
            payload={
                "actor_key": actor_key,
                "delegation_code": delegation_code,
                "response": response,
                "world_effect_applied": world_effect,
                "actor_effect_applied": actor_effect,
                "world_version_before": before,
                "world_version_after": instance.world_state_version,
                "actor_state_version_before": actor_before,
                "actor_state_version_after": actor_instance.state_version,
            },
            world_version_before=before,
            world_version_after=instance.world_state_version,
            idempotency_key=f"{body.idempotency_key}:accepted",
            now=now,
            causal_parent_ids=[str(requested_event.id)],
        )
        await _append_observation(
            db,
            instance=instance,
            source_event=event,
            observation_type="DELEGATION_OBSERVED",
            factual_statement=(
                f"Candidate delegated '{delegation_code}' to actor '{actor_key}'; "
                f"world state advanced from version {before} to "
                f"{instance.world_state_version} and actor state advanced from "
                f"version {actor_before} to {actor_instance.state_version}."
            ),
            payload={
                "actor_key": actor_key,
                "delegation_code": delegation_code,
                "world_version_before": before,
                "world_version_after": instance.world_state_version,
                "actor_state_version_before": actor_before,
                "actor_state_version_after": actor_instance.state_version,
            },
            now=now,
        )
        record_event(
            db,
            new_event(
                event_type="mission.delegation_processed.v1",
                aggregate_type="MissionInstance",
                aggregate_id=instance.id,
                aggregate_version=instance.version,
                actor={"type": "PERSON", "id": str(actor.person_id)},
                organization_context_id=actor.organization_context_id,
                data_classification="INTERNAL",
                payload={
                    "mission_instance_id": str(instance.id),
                    "actor_instance_id": str(actor_instance.id),
                    "actor_key": actor_key,
                    "delegation_code": delegation_code,
                    "world_version_before": before,
                    "world_version_after": instance.world_state_version,
                    "actor_state_version_before": actor_before,
                    "actor_state_version_after": actor_instance.state_version,
                },
                trace_id=actor.trace_id,
            ),
        )

        await _cancel_matching_scheduled_effects(
            db,
            instance=instance,
            actor=actor,
            source_event=event,
            command_key=f"{body.idempotency_key}:after-delegation",
            now=now,
        )
        await _apply_matching_state_triggered_effects(
            db,
            instance=instance,
            actor=actor,
            source_event=event,
            command_key=f"{body.idempotency_key}:after-delegation",
            now=now,
        )

    elif body.action_type == MissionActionType.CHANGE_SCOPE:
        scope_change_code = body.payload.get("scope_change_code")
        rationale = body.payload.get("rationale")
        if not isinstance(scope_change_code, str) or not scope_change_code:
            raise AppError(
                "SCOPE_CHANGE_CODE_REQUIRED",
                "scope_change_code is required.",
                status_code=422,
            )
        if not isinstance(rationale, str) or not rationale.strip():
            raise AppError(
                "SCOPE_CHANGE_RATIONALE_REQUIRED",
                "Candidate scope-change rationale is required.",
                status_code=422,
            )

        raw_options = _runtime_config(version).get("scope_change_options", [])
        option = next(
            (
                item
                for item in raw_options
                if isinstance(item, dict)
                and item.get("code") == scope_change_code
            ),
            None,
        ) if isinstance(raw_options, list) else None
        if option is None:
            raise AppError(
                "SCOPE_CHANGE_NOT_ALLOWED",
                "Scope change is not defined by the mission world model.",
                status_code=422,
            )

        response = option.get("response")
        world_effect = option.get("world_effect")
        scope_path = option.get("scope_path")
        from_scope = option.get("from_scope")
        to_scope = option.get("to_scope")
        if (
            not isinstance(response, str)
            or not response
            or not isinstance(world_effect, dict)
            or not isinstance(scope_path, str)
            or not scope_path
            or not isinstance(from_scope, str)
            or not from_scope
            or not isinstance(to_scope, str)
            or not to_scope
            or from_scope == to_scope
        ):
            raise AppError(
                "MISSION_SCOPE_CHANGE_DEFINITION_INVALID",
                "Scope-change rule must define response, scope_path, distinct from_scope/to_scope and world_effect.",
                status_code=422,
            )

        current_scope = _world_state_path_value(instance.world_state, scope_path)
        if current_scope != from_scope:
            raise AppError(
                "SCOPE_CHANGE_PRECONDITION_NOT_MET",
                "The canonical Mission scope no longer matches this scope-change option.",
                status_code=409,
            )

        try:
            next_world = apply_world_effect(instance.world_state, world_effect)
        except ValueError as exc:
            raise AppError(
                "MISSION_SCOPE_CHANGE_EFFECT_INVALID",
                str(exc),
                status_code=422,
            ) from exc
        if _world_state_path_value(next_world, scope_path) != to_scope:
            raise AppError(
                "MISSION_SCOPE_CHANGE_DEFINITION_INVALID",
                "Scope-change world_effect must produce the declared to_scope at scope_path.",
                status_code=422,
            )
        if not preserves_candidate_accountability(
            instance.world_state,
            next_world,
        ):
            raise AppError(
                "SCOPE_CHANGE_ACCOUNTABILITY_TRANSFER_FORBIDDEN",
                "Scope change cannot transfer Candidate accountability for the Mission.",
                status_code=422,
            )
        if next_world == instance.world_state:
            raise AppError(
                "SCOPE_CHANGE_NO_EFFECT",
                "Scope-change option must change canonical World State.",
                status_code=422,
            )
        instance.world_state = next_world
        instance.world_state_version += 1
        instance.version += 1

        requested_event = await _append_runtime_event(
            db,
            instance=instance,
            event_type="scope_change.requested",
            source="CANDIDATE",
            trigger_type="BEHAVIOUR_TRIGGERED",
            trigger_reference=str(action.id),
            payload={
                "scope_change_code": scope_change_code,
                "from_scope": from_scope,
                "to_scope": to_scope,
                "rationale": rationale.strip(),
            },
            world_version_before=before,
            world_version_after=before,
            idempotency_key=f"{body.idempotency_key}:requested",
            now=now,
        )
        event = await _append_runtime_event(
            db,
            instance=instance,
            event_type="scope_change.accepted",
            source="ENGINE",
            trigger_type="STATE_TRIGGERED",
            trigger_reference=str(requested_event.id),
            payload={
                "scope_change_code": scope_change_code,
                "response": response,
                "scope_path": scope_path,
                "from_scope": from_scope,
                "to_scope": to_scope,
                "world_effect_applied": world_effect,
                "world_version_before": before,
                "world_version_after": instance.world_state_version,
            },
            world_version_before=before,
            world_version_after=instance.world_state_version,
            idempotency_key=f"{body.idempotency_key}:accepted",
            now=now,
            causal_parent_ids=[str(requested_event.id)],
        )
        await _append_observation(
            db,
            instance=instance,
            source_event=event,
            observation_type="SCOPE_CHANGE_OBSERVED",
            factual_statement=(
                f"Candidate changed Mission scope using '{scope_change_code}'; "
                f"world state advanced from version {before} to "
                f"{instance.world_state_version}."
            ),
            payload={
                "scope_change_code": scope_change_code,
                "from_scope": from_scope,
                "to_scope": to_scope,
                "world_version_before": before,
                "world_version_after": instance.world_state_version,
            },
            now=now,
        )
        record_event(
            db,
            new_event(
                event_type="mission.scope_change_processed.v1",
                aggregate_type="MissionInstance",
                aggregate_id=instance.id,
                aggregate_version=instance.version,
                actor={"type": "PERSON", "id": str(actor.person_id)},
                organization_context_id=actor.organization_context_id,
                data_classification="INTERNAL",
                payload={
                    "mission_instance_id": str(instance.id),
                    "scope_change_code": scope_change_code,
                    "scope_path": scope_path,
                    "from_scope": from_scope,
                    "to_scope": to_scope,
                    "world_version_before": before,
                    "world_version_after": instance.world_state_version,
                },
                trace_id=actor.trace_id,
            ),
        )

        await _cancel_matching_scheduled_effects(
            db,
            instance=instance,
            actor=actor,
            source_event=event,
            command_key=f"{body.idempotency_key}:after-scope-change",
            now=now,
        )
        await _apply_matching_state_triggered_effects(
            db,
            instance=instance,
            actor=actor,
            source_event=event,
            command_key=f"{body.idempotency_key}:after-scope-change",
            now=now,
        )

    elif body.action_type == MissionActionType.NO_ACTION:
        no_action_code = body.payload.get("no_action_code")
        rationale = body.reasoning
        if not isinstance(no_action_code, str) or not no_action_code:
            raise AppError(
                "NO_ACTION_CODE_REQUIRED",
                "no_action_code is required.",
                status_code=422,
            )
        raw_options = _runtime_config(version).get("no_action_options", [])
        option = next(
            (
                item
                for item in raw_options
                if isinstance(item, dict)
                and item.get("code") == no_action_code
            ),
            None,
        ) if isinstance(raw_options, list) else None
        if option is None:
            raise AppError(
                "NO_ACTION_NOT_ALLOWED",
                "NO_ACTION option is not defined by the mission world model.",
                status_code=422,
            )
        wait_seconds = option.get("wait_seconds")
        if not isinstance(wait_seconds, int) or wait_seconds <= 0:
            raise AppError(
                "NO_ACTION_DEFINITION_INVALID",
                "NO_ACTION option requires a positive wait_seconds.",
                status_code=422,
            )

        target_time = instance.simulation_time + timedelta(seconds=wait_seconds)
        due_effect = (
            await db.execute(
                select(ScheduledEffect.id).where(
                    ScheduledEffect.mission_instance_id == instance.id,
                    ScheduledEffect.status == ScheduledEffectStatus.PENDING.value,
                    ScheduledEffect.due_at.is_not(None),
                    ScheduledEffect.due_at <= target_time,
                ).limit(1)
            )
        ).scalar_one_or_none()
        if due_effect is None:
            raise AppError(
                "NO_ACTION_HAS_NO_CANONICAL_CONSEQUENCE",
                "No canonical scheduled consequence exists within this wait window.",
                status_code=409,
            )

        simulation_before = instance.simulation_time
        no_action_event = await _append_runtime_event(
            db,
            instance=instance,
            event_type="no_action.committed",
            source="CANDIDATE",
            trigger_type="BEHAVIOUR_TRIGGERED",
            trigger_reference=str(action.id),
            payload={
                "no_action_code": no_action_code,
                "reasoning": rationale.strip(),
                "simulation_time_before": simulation_before.isoformat(),
                "simulation_time_after": target_time.isoformat(),
            },
            world_version_before=before,
            world_version_after=before,
            idempotency_key=f"{body.idempotency_key}:no-action",
            now=now,
        )
        await _advance_simulation_through(
            db,
            instance=instance,
            actor=actor,
            target_time=target_time,
            command_key=body.idempotency_key,
            now=now,
            trigger_reference=str(action.id),
            causal_parent_ids=[str(no_action_event.id)],
        )
        await _append_observation(
            db,
            instance=instance,
            source_event=no_action_event,
            observation_type="NO_ACTION_OBSERVED",
            factual_statement=(
                f"Candidate explicitly chose no action '{no_action_code}' and simulation "
                f"time advanced from {simulation_before.isoformat()} to "
                f"{target_time.isoformat()}."
            ),
            payload={
                "no_action_code": no_action_code,
                "simulation_time_before": simulation_before.isoformat(),
                "simulation_time_after": target_time.isoformat(),
                "world_version_before": before,
                "world_version_after": instance.world_state_version,
            },
            now=now,
        )

    elif body.action_type == MissionActionType.DECIDE:
        decision_code = body.payload.get("decision_code")
        if not isinstance(decision_code, str) or not decision_code:
            raise AppError(
                "DECISION_CODE_REQUIRED",
                "decision_code is required.",
                status_code=422,
            )
        runtime = _runtime_config(version)
        decision_effects = runtime.get("decision_effects", {})
        effect = (
            decision_effects.get(decision_code)
            if isinstance(decision_effects, dict)
            else None
        )
        if not isinstance(effect, dict):
            raise AppError(
                "DECISION_NOT_ALLOWED",
                "Decision is not defined by the mission world model.",
                status_code=422,
            )
        try:
            next_state = apply_world_effect(instance.world_state, effect)
        except ValueError as exc:
            raise AppError(
                "MISSION_RUNTIME_EFFECT_INVALID",
                str(exc),
                status_code=422,
            ) from exc

        instance.world_state = next_state
        instance.world_state_version += 1
        instance.version += 1

        decision_point = version.decision_points[0] if version.decision_points else {}
        db.add(
            DecisionRecord(
                id=uuid4(),
                mission_instance_id=instance.id,
                action_id=action.id,
                question=str(decision_point.get("prompt", body.target or "Mission decision")),
                options_considered=body.payload.get("options_considered", []),
                available_evidence=body.payload.get("available_evidence", []),
                assumptions=body.payload.get("assumptions", []),
                decision=decision_code,
                reasoning=body.reasoning,
                confidence=body.confidence,
                expected_outcome=str(body.payload.get("expected_outcome", "Not provided")),
                revisit_trigger=str(body.payload.get("revisit_trigger", "Not provided")),
                decision_owner=actor.person_id,
                reversibility=str(body.payload.get("reversibility", "DEFINED_BY_WORLD_MODEL")),
                frozen_at=now,
            )
        )
        await db.flush()

        event = await _append_runtime_event(
            db,
            instance=instance,
            event_type="decision.committed",
            source="ENGINE",
            trigger_type="BEHAVIOUR_TRIGGERED",
            trigger_reference=str(action.id),
            payload={
                "decision_code": decision_code,
                "effect_applied": effect,
            },
            world_version_before=before,
            world_version_after=instance.world_state_version,
            idempotency_key=f"{body.idempotency_key}:event",
            now=now,
        )
        await _append_observation(
            db,
            instance=instance,
            source_event=event,
            observation_type="DECISION_COMMITTED",
            factual_statement=(
                f"Candidate committed decision '{decision_code}'; world state advanced "
                f"from version {before} to {instance.world_state_version}."
            ),
            payload={
                "decision_code": decision_code,
                "world_version_before": before,
                "world_version_after": instance.world_state_version,
            },
            now=now,
        )

        await _cancel_matching_scheduled_effects(
            db,
            instance=instance,
            actor=actor,
            source_event=event,
            command_key=f"{body.idempotency_key}:after-decision",
            now=now,
        )
        await _apply_matching_state_triggered_effects(
            db,
            instance=instance,
            actor=actor,
            source_event=event,
            command_key=f"{body.idempotency_key}:after-decision",
            now=now,
        )

        if runtime.get("complete_after_decision", True):
            if not runtime_transition_allowed(
                instance.status,
                MissionInstanceStatus.COMPLETED.value,
            ):
                raise AppError(
                    "MISSION_RUNTIME_TRANSITION_INVALID",
                    "Mission cannot complete from its current state.",
                    status_code=500,
                )
            previous = instance.status
            instance.status = MissionInstanceStatus.COMPLETED.value
            instance.completed_at = now
            instance.version += 1
            await _append_runtime_event(
                db,
                instance=instance,
                event_type="mission.completed",
                source="ENGINE",
                trigger_type="STATE_TRIGGERED",
                trigger_reference=str(event.id),
                payload={
                    "from_status": previous,
                    "to_status": instance.status,
                },
                world_version_before=instance.world_state_version,
                world_version_after=instance.world_state_version,
                idempotency_key=f"{body.idempotency_key}:completed",
                now=now,
                causal_parent_ids=[str(event.id)],
            )

            if instance.assignment_id is not None:
                assignment = (
                    await db.execute(
                        select(MissionAssignment)
                        .where(MissionAssignment.id == instance.assignment_id)
                        .with_for_update()
                    )
                ).scalar_one_or_none()
                if assignment is None:
                    raise AppError(
                        "MISSION_ASSIGNMENT_NOT_FOUND",
                        "Mission assignment was not found.",
                        status_code=500,
                    )
                if not assignment_transition_allowed(
                    assignment.status,
                    MissionAssignmentStatus.COMPLETED.value,
                ):
                    raise AppError(
                        "MISSION_ASSIGNMENT_TRANSITION_INVALID",
                        "Mission assignment cannot transition to COMPLETED.",
                        status_code=500,
                    )
                assignment.status = MissionAssignmentStatus.COMPLETED.value
                assignment.version += 1
                assignment.completed_at = now

            record_event(
                db,
                new_event(
                    event_type="mission.completed.v1",
                    aggregate_type="MissionInstance",
                    aggregate_id=instance.id,
                    aggregate_version=instance.version,
                    actor={"type": "PERSON", "id": str(actor.person_id)},
                    organization_context_id=actor.organization_context_id,
                    data_classification="INTERNAL",
                    payload={
                        "assignment_id": (
                            str(instance.assignment_id)
                            if instance.assignment_id is not None
                            else None
                        ),
                        "mission_instance_id": str(instance.id),
                        "mission_version_id": str(instance.mission_version_id),
                        "world_state_version": instance.world_state_version,
                    },
                    trace_id=actor.trace_id,
                ),
            )

    else:
        raise AppError(
            "MISSION_ACTION_NOT_SUPPORTED_YET",
            "This action type is part of the runtime contract but is not executable in v1.",
            status_code=422,
        )

    record_event(
        db,
        new_event(
            event_type="mission.candidate_action_recorded.v1",
            aggregate_type="MissionInstance",
            aggregate_id=instance.id,
            aggregate_version=instance.version,
            actor={"type": "PERSON", "id": str(actor.person_id)},
            organization_context_id=actor.organization_context_id,
            data_classification="INTERNAL",
            payload={
                "mission_instance_id": str(instance.id),
                "action_id": str(action.id),
                "action_type": action.action_type,
                "world_version_before": before,
                "world_version_after": instance.world_state_version,
                "status": instance.status,
            },
            trace_id=actor.trace_id,
        ),
    )
    await db.commit()
    return await _instance_response(db, instance)
