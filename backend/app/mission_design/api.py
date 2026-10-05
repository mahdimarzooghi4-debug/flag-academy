from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.curriculum.models import CapabilityVersion
from app.db import get_session
from app.errors import AppError
from app.identity.auth import ActorContext, require_role
from app.mission_design.domain import (
    MissionDifficulty,
    MissionMode,
    MissionVersionStatus,
    transition_allowed,
)
from app.mission_design.models import MissionTemplate, MissionVersion
from app.platform.events import new_event, record_event

router = APIRouter(prefix="/api/v1/studio", tags=["mission-design"])


class ActorSpec(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    goal: str = Field(min_length=1, max_length=1000)
    authority: str = Field(min_length=1, max_length=1000)


class InformationSpec(BaseModel):
    label: str = Field(min_length=1, max_length=160)
    access: str = Field(pattern="^(DEFAULT|DISCOVERABLE|RESTRICTED|UNAVAILABLE|NOISY)$")
    content: str = Field(min_length=1, max_length=4000)


class ConstraintSpec(BaseModel):
    label: str = Field(min_length=1, max_length=160)
    description: str = Field(min_length=1, max_length=2000)


class DecisionPointSpec(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    prompt: str = Field(min_length=1, max_length=3000)


class ConsequenceRuleSpec(BaseModel):
    trigger: str = Field(min_length=1, max_length=1000)
    effect: str = Field(min_length=1, max_length=2000)


class EvidenceOpportunitySpec(BaseModel):
    behaviour: str = Field(min_length=1, max_length=1000)
    source: str = Field(min_length=1, max_length=120)


class MissionDefinitionInput(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    purpose: str = Field(min_length=1, max_length=3000)
    objective: str = Field(min_length=1, max_length=3000)
    primary_capability_version_id: UUID
    mission_mode: MissionMode
    difficulty: MissionDifficulty
    world_context: dict[str, Any]
    actors: list[ActorSpec] = Field(min_length=1)
    information_items: list[InformationSpec] = Field(min_length=1)
    constraints: list[ConstraintSpec] = Field(min_length=1)
    decision_points: list[DecisionPointSpec] = Field(min_length=1)
    consequence_rules: list[ConsequenceRuleSpec] = Field(min_length=1)
    evidence_opportunities: list[EvidenceOpportunitySpec] = Field(min_length=1)
    replay_policy: dict[str, Any]
    safety_policy: dict[str, Any]


class MissionTemplateCreate(MissionDefinitionInput):
    code: str = Field(min_length=2, max_length=128, pattern="^[A-Z0-9_-]+$")
    name: str = Field(min_length=1, max_length=255)


class MissionNewVersionCreate(MissionDefinitionInput):
    base_version_id: UUID


class MissionTransitionRequest(BaseModel):
    expected_version: int = Field(ge=1)


class MissionVersionResponse(BaseModel):
    id: UUID
    template_id: UUID
    aggregate_version: int
    version_number: int
    status: str
    title: str
    purpose: str
    objective: str
    primary_capability_version_id: UUID
    mission_mode: str
    difficulty: str
    world_context: dict[str, Any]
    actors: list[dict[str, Any]]
    information_items: list[dict[str, Any]]
    constraints: list[dict[str, Any]]
    decision_points: list[dict[str, Any]]
    consequence_rules: list[dict[str, Any]]
    evidence_opportunities: list[dict[str, Any]]
    replay_policy: dict[str, Any]
    safety_policy: dict[str, Any]
    created_at: datetime
    validated_at: datetime | None
    activated_at: datetime | None
    retired_at: datetime | None


class MissionTemplateResponse(BaseModel):
    id: UUID
    code: str
    name: str
    versions: list[MissionVersionResponse]


class MissionDefinitionValidationResponse(BaseModel):
    valid: bool
    errors: list[str]
    warnings: list[str]


async def _ensure_capability_version(
    db: AsyncSession,
    capability_version_id: UUID,
) -> None:
    capability = await db.get(CapabilityVersion, capability_version_id)
    if capability is None or capability.status != "ACTIVE":
        raise AppError(
            "CAPABILITY_VERSION_NOT_FOUND",
            "Capability version not found.",
            status_code=422,
        )


async def _get_owned_template(
    db: AsyncSession,
    actor: ActorContext,
    template_id: UUID,
) -> MissionTemplate:
    template = await db.get(MissionTemplate, template_id)
    if (
        template is None
        or template.organization_context_id != actor.organization_context_id
    ):
        raise AppError(
            "MISSION_TEMPLATE_NOT_FOUND",
            "Mission template not found.",
            status_code=404,
        )
    return template


async def _get_owned_version(
    db: AsyncSession,
    actor: ActorContext,
    version_id: UUID,
) -> tuple[MissionTemplate, MissionVersion]:
    version = await db.get(MissionVersion, version_id)
    if version is None:
        raise AppError(
            "MISSION_VERSION_NOT_FOUND",
            "Mission version not found.",
            status_code=404,
        )
    template = await _get_owned_template(db, actor, version.template_id)
    return template, version


def _version_response(version: MissionVersion) -> MissionVersionResponse:
    return MissionVersionResponse(
        id=version.id,
        template_id=version.template_id,
        aggregate_version=version.aggregate_version,
        version_number=version.version_number,
        status=version.status,
        title=version.title,
        purpose=version.purpose,
        objective=version.objective,
        primary_capability_version_id=version.primary_capability_version_id,
        mission_mode=version.mission_mode,
        difficulty=version.difficulty,
        world_context=version.world_context,
        actors=version.actors,
        information_items=version.information_items,
        constraints=version.constraints,
        decision_points=version.decision_points,
        consequence_rules=version.consequence_rules,
        evidence_opportunities=version.evidence_opportunities,
        replay_policy=version.replay_policy,
        safety_policy=version.safety_policy,
        created_at=version.created_at,
        validated_at=version.validated_at,
        activated_at=version.activated_at,
        retired_at=version.retired_at,
    )


async def _template_response(
    db: AsyncSession,
    template: MissionTemplate,
) -> MissionTemplateResponse:
    versions = (
        await db.execute(
            select(MissionVersion)
            .where(MissionVersion.template_id == template.id)
            .order_by(MissionVersion.version_number)
        )
    ).scalars().all()
    return MissionTemplateResponse(
        id=template.id,
        code=template.code,
        name=template.name,
        versions=[_version_response(item) for item in versions],
    )


def _definition_validation(version: MissionVersion) -> MissionDefinitionValidationResponse:
    errors: list[str] = []
    warnings: list[str] = []

    if not version.world_context:
        errors.append("WORLD_CONTEXT_REQUIRED")
    if not version.actors:
        errors.append("ACTOR_REQUIRED")
    if not version.information_items:
        errors.append("INFORMATION_REQUIRED")
    if not version.constraints:
        errors.append("CONSTRAINT_REQUIRED")
    if not version.decision_points:
        errors.append("DECISION_POINT_REQUIRED")
    if not version.consequence_rules:
        errors.append("CONSEQUENCE_RULE_REQUIRED")
    if not version.evidence_opportunities:
        errors.append("EVIDENCE_OPPORTUNITY_REQUIRED")

    allowed_access = {
        "DEFAULT",
        "DISCOVERABLE",
        "RESTRICTED",
        "UNAVAILABLE",
        "NOISY",
    }
    for item in version.information_items:
        if item.get("access") not in allowed_access:
            errors.append("INFORMATION_ACCESS_INVALID")
            break

    if version.mission_mode == "ASSESSMENT":
        if version.replay_policy.get("immediate", False):
            warnings.append("ASSESSMENT_IMMEDIATE_REPLAY_SHOULD_BE_DISABLED")
        if version.safety_policy.get("reveal_hidden_targets", False):
            errors.append("ASSESSMENT_HIDDEN_TARGET_DISCLOSURE_FORBIDDEN")

    return MissionDefinitionValidationResponse(
        valid=not errors,
        errors=errors,
        warnings=warnings,
    )


def _new_version(
    *,
    template_id: UUID,
    version_number: int,
    body: MissionDefinitionInput,
    actor: ActorContext,
    now: datetime,
) -> MissionVersion:
    payload = body.model_dump(mode="json")
    return MissionVersion(
        id=uuid4(),
        template_id=template_id,
        version_number=version_number,
        status=MissionVersionStatus.DRAFT.value,
        title=body.title,
        purpose=body.purpose,
        objective=body.objective,
        primary_capability_version_id=body.primary_capability_version_id,
        mission_mode=body.mission_mode.value,
        difficulty=body.difficulty.value,
        world_context=payload["world_context"],
        actors=payload["actors"],
        information_items=payload["information_items"],
        constraints=payload["constraints"],
        decision_points=payload["decision_points"],
        consequence_rules=payload["consequence_rules"],
        evidence_opportunities=payload["evidence_opportunities"],
        replay_policy=payload["replay_policy"],
        safety_policy=payload["safety_policy"],
        created_by=actor.person_id,
        created_at=now,
        validated_at=None,
        activated_at=None,
        retired_at=None,
    )


@router.get("/mission-templates", response_model=list[MissionTemplateResponse])
async def list_mission_templates(
    actor: Annotated[ActorContext, Depends(require_role("ACADEMY_ADMIN"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> list[MissionTemplateResponse]:
    templates = (
        await db.execute(
            select(MissionTemplate)
            .where(
                MissionTemplate.organization_context_id
                == actor.organization_context_id
            )
            .order_by(MissionTemplate.created_at, MissionTemplate.code)
        )
    ).scalars().all()
    return [await _template_response(db, item) for item in templates]


@router.post(
    "/mission-templates",
    response_model=MissionTemplateResponse,
    status_code=201,
)
async def create_mission_template(
    body: MissionTemplateCreate,
    actor: Annotated[ActorContext, Depends(require_role("ACADEMY_ADMIN"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> MissionTemplateResponse:
    existing = (
        await db.execute(
            select(MissionTemplate.id).where(
                MissionTemplate.organization_context_id
                == actor.organization_context_id,
                MissionTemplate.code == body.code,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise AppError(
            "MISSION_TEMPLATE_CODE_EXISTS",
            "Mission template code already exists.",
            status_code=409,
        )
    await _ensure_capability_version(db, body.primary_capability_version_id)

    now = datetime.now(UTC)
    template = MissionTemplate(
        id=uuid4(),
        organization_context_id=actor.organization_context_id,
        code=body.code,
        name=body.name,
        created_by=actor.person_id,
        created_at=now,
    )
    db.add(template)
    await db.flush()

    version = _new_version(
        template_id=template.id,
        version_number=1,
        body=body,
        actor=actor,
        now=now,
    )
    db.add(version)
    await db.flush()

    record_event(
        db,
        new_event(
            event_type="mission.template_created.v1",
            aggregate_type="MissionTemplate",
            aggregate_id=template.id,
            aggregate_version=template.version,
            actor={"type": "PERSON", "id": str(actor.person_id)},
            organization_context_id=actor.organization_context_id,
            data_classification="INTERNAL",
            payload={
                "template_id": str(template.id),
                "mission_version_id": str(version.id),
                "version_number": 1,
                "code": template.code,
            },
            trace_id=actor.trace_id,
        ),
    )
    await db.commit()
    return await _template_response(db, template)


@router.post(
    "/mission-templates/{template_id}/versions",
    response_model=MissionVersionResponse,
    status_code=201,
)
async def create_mission_version(
    template_id: UUID,
    body: MissionNewVersionCreate,
    actor: Annotated[ActorContext, Depends(require_role("ACADEMY_ADMIN"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> MissionVersionResponse:
    template = await _get_owned_template(db, actor, template_id)
    base = await db.get(MissionVersion, body.base_version_id)
    if base is None or base.template_id != template.id:
        raise AppError(
            "BASE_MISSION_VERSION_NOT_FOUND",
            "Base mission version not found.",
            status_code=404,
        )
    if base.status not in {
        MissionVersionStatus.ACTIVE.value,
        MissionVersionStatus.RETIRED.value,
        MissionVersionStatus.VALIDATED.value,
    }:
        raise AppError(
            "BASE_MISSION_VERSION_NOT_STABLE",
            "New versions require a stable base version.",
            status_code=409,
        )
    await _ensure_capability_version(db, body.primary_capability_version_id)

    max_version = (
        await db.execute(
            select(MissionVersion.version_number)
            .where(MissionVersion.template_id == template.id)
            .order_by(MissionVersion.version_number.desc())
            .limit(1)
        )
    ).scalar_one()
    now = datetime.now(UTC)
    version = _new_version(
        template_id=template.id,
        version_number=max_version + 1,
        body=body,
        actor=actor,
        now=now,
    )
    db.add(version)
    template.version += 1
    record_event(
        db,
        new_event(
            event_type="mission.version_created.v1",
            aggregate_type="MissionTemplate",
            aggregate_id=template.id,
            aggregate_version=template.version,
            actor={"type": "PERSON", "id": str(actor.person_id)},
            organization_context_id=actor.organization_context_id,
            data_classification="INTERNAL",
            payload={
                "template_id": str(template.id),
                "mission_version_id": str(version.id),
                "version_number": version.version_number,
                "base_version_id": str(base.id),
            },
            trace_id=actor.trace_id,
        ),
    )
    await db.commit()
    return _version_response(version)


@router.post(
    "/mission-versions/{version_id}/validate-definition",
    response_model=MissionDefinitionValidationResponse,
)
async def validate_mission_definition(
    version_id: UUID,
    actor: Annotated[ActorContext, Depends(require_role("ACADEMY_ADMIN"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> MissionDefinitionValidationResponse:
    _, version = await _get_owned_version(db, actor, version_id)
    await _ensure_capability_version(db, version.primary_capability_version_id)
    return _definition_validation(version)


async def _transition(
    *,
    db: AsyncSession,
    actor: ActorContext,
    version_id: UUID,
    body: MissionTransitionRequest,
    target: MissionVersionStatus,
) -> MissionVersionResponse:
    template, version = await _get_owned_version(db, actor, version_id)
    if version.aggregate_version != body.expected_version:
        raise AppError(
            "VERSION_CONFLICT",
            "Mission version changed. Refresh and retry.",
            status_code=409,
            details={
                "expected_version": body.expected_version,
                "current_version": version.aggregate_version,
            },
        )
    if not transition_allowed(version.status, target.value):
        raise AppError(
            "MISSION_STATUS_TRANSITION_INVALID",
            "Mission status transition is invalid.",
            status_code=422,
            details={"current": version.status, "target": target.value},
        )
    validation = _definition_validation(version)
    if not validation.valid:
        raise AppError(
            "MISSION_DEFINITION_INVALID",
            "Mission definition is not valid for progression.",
            status_code=422,
            details={"errors": validation.errors},
        )

    now = datetime.now(UTC)
    previous = version.status
    version.status = target.value
    version.aggregate_version += 1

    if target == MissionVersionStatus.VALIDATED:
        version.validated_at = now
    elif target == MissionVersionStatus.ACTIVE:
        current_active = (
            await db.execute(
                select(MissionVersion).where(
                    MissionVersion.template_id == template.id,
                    MissionVersion.status == MissionVersionStatus.ACTIVE.value,
                    MissionVersion.id != version.id,
                )
            )
        ).scalars().all()
        for active in current_active:
            active.status = MissionVersionStatus.RETIRED.value
            active.aggregate_version += 1
            active.retired_at = now
        version.activated_at = now
    elif target == MissionVersionStatus.RETIRED:
        version.retired_at = now

    template.version += 1
    record_event(
        db,
        new_event(
            event_type="mission.version_status_changed.v1",
            aggregate_type="MissionTemplate",
            aggregate_id=template.id,
            aggregate_version=template.version,
            actor={"type": "PERSON", "id": str(actor.person_id)},
            organization_context_id=actor.organization_context_id,
            data_classification="INTERNAL",
            payload={
                "template_id": str(template.id),
                "mission_version_id": str(version.id),
                "version_number": version.version_number,
                "from_status": previous,
                "to_status": target.value,
            },
            trace_id=actor.trace_id,
        ),
    )
    await db.commit()
    return _version_response(version)


@router.post(
    "/mission-versions/{version_id}/pilot",
    response_model=MissionVersionResponse,
)
async def pilot_mission_version(
    version_id: UUID,
    body: MissionTransitionRequest,
    actor: Annotated[ActorContext, Depends(require_role("ACADEMY_ADMIN"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> MissionVersionResponse:
    return await _transition(
        db=db,
        actor=actor,
        version_id=version_id,
        body=body,
        target=MissionVersionStatus.PILOT,
    )


@router.post(
    "/mission-versions/{version_id}/mark-validated",
    response_model=MissionVersionResponse,
)
async def mark_mission_validated(
    version_id: UUID,
    body: MissionTransitionRequest,
    actor: Annotated[ActorContext, Depends(require_role("ACADEMY_ADMIN"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> MissionVersionResponse:
    return await _transition(
        db=db,
        actor=actor,
        version_id=version_id,
        body=body,
        target=MissionVersionStatus.VALIDATED,
    )


@router.post(
    "/mission-versions/{version_id}/activate",
    response_model=MissionVersionResponse,
)
async def activate_mission_version(
    version_id: UUID,
    body: MissionTransitionRequest,
    actor: Annotated[ActorContext, Depends(require_role("ACADEMY_ADMIN"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> MissionVersionResponse:
    return await _transition(
        db=db,
        actor=actor,
        version_id=version_id,
        body=body,
        target=MissionVersionStatus.ACTIVE,
    )


@router.post(
    "/mission-versions/{version_id}/retire",
    response_model=MissionVersionResponse,
)
async def retire_mission_version(
    version_id: UUID,
    body: MissionTransitionRequest,
    actor: Annotated[ActorContext, Depends(require_role("ACADEMY_ADMIN"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> MissionVersionResponse:
    return await _transition(
        db=db,
        actor=actor,
        version_id=version_id,
        body=body,
        target=MissionVersionStatus.RETIRED,
    )
