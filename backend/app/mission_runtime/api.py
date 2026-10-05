from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.errors import AppError
from app.identity.auth import ActorContext, require_role
from app.mission_design.models import MissionTemplate, MissionVersion
from app.mission_runtime.domain import (
    MissionActionType,
    MissionInstanceStatus,
    apply_world_effect,
    runtime_transition_allowed,
)
from app.mission_runtime.models import (
    CandidateAction,
    DecisionRecord,
    MissionInstance,
    Observation,
    RuntimeEvent,
)
from app.platform.events import new_event, record_event

router = APIRouter(prefix="/api/v1", tags=["mission-runtime"])


class MissionStartRequest(BaseModel):
    idempotency_key: str = Field(min_length=1, max_length=160)


class MissionActionRequest(BaseModel):
    action_type: MissionActionType
    target: str | None = Field(default=None, max_length=255)
    payload: dict[str, Any] = Field(default_factory=dict)
    reasoning: str = Field(min_length=1, max_length=5000)
    confidence: int = Field(ge=0, le=100)
    expected_world_version: int = Field(ge=1)
    idempotency_key: str = Field(min_length=1, max_length=160)
    resource_cost: dict[str, Any] = Field(default_factory=dict)
    mode: str = Field(default="CANDIDATE", min_length=1, max_length=32)
    provenance: dict[str, Any] = Field(default_factory=dict)


class MissionCatalogItem(BaseModel):
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


class MissionInstanceResponse(BaseModel):
    id: UUID
    version: int
    mission_version_id: UUID
    template_id: UUID
    mission_code: str
    title: str
    status: str
    world_state: dict[str, Any]
    world_state_version: int
    simulation_seed: int
    decision_points: list[dict[str, Any]]
    information_options: list[dict[str, Any]]
    decision_options: list[dict[str, Any]]
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
        effective_at=now,
        visibility="CANDIDATE",
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

    disclosed_information = [
        {
            "label": event.payload.get("label"),
            "content": event.payload.get("content"),
            "access": event.payload.get("access"),
        }
        for event in events
        if event.event_type == "information.disclosed"
    ]

    return MissionInstanceResponse(
        id=instance.id,
        version=instance.version,
        mission_version_id=instance.mission_version_id,
        template_id=template.id,
        mission_code=template.code,
        title=version.title,
        status=instance.status,
        world_state=instance.world_state,
        world_state_version=instance.world_state_version,
        simulation_seed=instance.simulation_seed,
        decision_points=version.decision_points,
        information_options=_information_options(version),
        decision_options=_decision_options(version),
        disclosed_information=disclosed_information,
        audit_events=[
            RuntimeEventResponse(
                id=item.id,
                sequence_number=item.sequence_number,
                event_type=item.event_type,
                source=item.source,
                visibility=item.visibility,
                payload=item.payload,
                world_version_before=item.world_version_before,
                world_version_after=item.world_version_after,
                occurred_at=item.occurred_at,
            )
            for item in events
        ],
        observations=[
            ObservationResponse(
                id=item.id,
                source_event_id=item.source_event_id,
                sequence_number=item.sequence_number,
                observation_type=item.observation_type,
                factual_statement=item.factual_statement,
                payload=item.payload,
                occurred_at=item.occurred_at,
            )
            for item in observations
        ],
        created_at=instance.created_at,
        started_at=instance.started_at,
        completed_at=instance.completed_at,
    )


@router.get("/missions/active", response_model=list[MissionCatalogItem])
async def list_active_missions(
    actor: Annotated[ActorContext, Depends(require_role("CANDIDATE"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> list[MissionCatalogItem]:
    rows = (
        await db.execute(
            select(MissionVersion, MissionTemplate)
            .join(MissionTemplate, MissionVersion.template_id == MissionTemplate.id)
            .where(
                MissionVersion.status == "ACTIVE",
                MissionTemplate.organization_context_id
                == actor.organization_context_id,
            )
            .order_by(MissionTemplate.code, MissionVersion.version_number)
        )
    ).all()
    return [
        MissionCatalogItem(
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
        for version, template in rows
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
        require_active=True,
    )
    existing = (
        await db.execute(
            select(MissionInstance).where(
                MissionInstance.mission_version_id == version.id,
                MissionInstance.candidate_id == actor.person_id,
                MissionInstance.start_idempotency_key == body.idempotency_key,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return await _instance_response(db, existing)

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

    now = datetime.now(UTC)
    instance_id = uuid4()
    instance = MissionInstance(
        id=instance_id,
        organization_context_id=actor.organization_context_id,
        mission_version_id=version.id,
        candidate_id=actor.person_id,
        status=MissionInstanceStatus.CREATED.value,
        world_state=initial_state,
        world_state_version=1,
        simulation_seed=instance_id.int % 2_147_483_647,
        start_idempotency_key=body.idempotency_key,
        created_at=now,
        started_at=None,
        completed_at=None,
    )
    db.add(instance)
    await db.flush()

    previous_event_id: UUID | None = None
    for index, target in enumerate(
        (
            MissionInstanceStatus.ELIGIBILITY_CHECK,
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
            trigger_type="BEHAVIOUR_TRIGGERED",
            trigger_reference=str(actor.person_id),
            payload={
                "from_status": previous,
                "to_status": target.value,
                "mission_version_id": str(version.id),
            },
            world_version_before=instance.world_state_version,
            world_version_after=instance.world_state_version,
            idempotency_key=f"{body.idempotency_key}:status:{index}",
            now=now,
            causal_parent_ids=[str(previous_event_id)] if previous_event_id else [],
        )
        previous_event_id = event.id

    start_event = await _append_runtime_event(
        db,
        instance=instance,
        event_type="mission.started",
        source="ENGINE",
        trigger_type="BEHAVIOUR_TRIGGERED",
        trigger_reference=str(actor.person_id),
        payload={
            "mission_version_id": str(version.id),
            "mission_code": template.code,
            "simulation_seed": instance.simulation_seed,
        },
        world_version_before=1,
        world_version_after=1,
        idempotency_key=f"{body.idempotency_key}:started",
        now=now,
        causal_parent_ids=[str(previous_event_id)] if previous_event_id else [],
    )
    await _append_observation(
        db,
        instance=instance,
        source_event=start_event,
        observation_type="MISSION_STARTED",
        factual_statement=(
            f"Mission {template.code} started for the candidate at world state version 1."
        ),
        payload={"mission_version_id": str(version.id)},
        now=now,
    )

    record_event(
        db,
        new_event(
            event_type="mission.runtime_started.v1",
            aggregate_type="MissionInstance",
            aggregate_id=instance.id,
            aggregate_version=instance.version,
            actor={"type": "PERSON", "id": str(actor.person_id)},
            organization_context_id=actor.organization_context_id,
            data_classification="INTERNAL",
            payload={
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
