from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.curriculum.models import (
    Capability,
    CapabilityVersion,
    Curriculum,
    CurriculumWave,
    WaveCapability,
)
from app.db import get_session
from app.errors import AppError
from app.identity.auth import ActorContext, get_actor

router = APIRouter(prefix="/api/v1", tags=["curriculum"])


@router.get("/capabilities")
async def capabilities(
    _: Annotated[ActorContext, Depends(get_actor)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[dict]:
    rows = (
        await session.execute(
            select(Capability, CapabilityVersion)
            .join(CapabilityVersion, CapabilityVersion.definition_id == Capability.id)
            .where(CapabilityVersion.status == "ACTIVE")
            .order_by(Capability.code)
        )
    ).all()
    return [
        {
            "id": str(cap.id),
            "code": cap.code,
            "version_id": str(version.id),
            "version_number": version.version_number,
            "name": version.name,
            "definition": version.definition,
            "status": version.status,
        }
        for cap, version in rows
    ]


@router.get("/capabilities/{capability_id}")
async def capability(
    capability_id: UUID,
    _: Annotated[ActorContext, Depends(get_actor)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    row = (
        await session.execute(
            select(Capability, CapabilityVersion)
            .join(CapabilityVersion, CapabilityVersion.definition_id == Capability.id)
            .where(Capability.id == capability_id, CapabilityVersion.status == "ACTIVE")
        )
    ).first()
    if row is None:
        raise AppError("CAPABILITY_NOT_FOUND", "Capability not found.", status_code=404)
    cap, version = row
    return {
        "id": str(cap.id),
        "code": cap.code,
        "version_id": str(version.id),
        "version_number": version.version_number,
        "name": version.name,
        "definition": version.definition,
        "status": version.status,
    }


@router.get("/curricula/{curriculum_id}")
async def curriculum(
    curriculum_id: UUID,
    _: Annotated[ActorContext, Depends(get_actor)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    current = await session.get(Curriculum, curriculum_id)
    if current is None:
        raise AppError("CURRICULUM_NOT_FOUND", "Curriculum not found.", status_code=404)
    waves = (
        await session.execute(
            select(CurriculumWave)
            .where(CurriculumWave.curriculum_id == current.id)
            .order_by(CurriculumWave.position)
        )
    ).scalars().all()
    wave_items = []
    for wave in waves:
        caps = (
            await session.execute(
                select(CapabilityVersion)
                .join(WaveCapability, WaveCapability.capability_version_id == CapabilityVersion.id)
                .where(WaveCapability.wave_id == wave.id)
                .order_by(WaveCapability.position)
            )
        ).scalars().all()
        wave_items.append(
            {
                "id": str(wave.id),
                "code": wave.code,
                "name": wave.name,
                "position": wave.position,
                "capabilities": [{"version_id": str(c.id), "name": c.name} for c in caps],
            }
        )
    return {
        "id": str(current.id),
        "code": current.code,
        "version_number": current.version_number,
        "name": current.name,
        "status": current.status,
        "waves": wave_items,
    }
