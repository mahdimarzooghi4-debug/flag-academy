from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.identity.auth import ActorContext, get_actor

router = APIRouter(prefix="/api/v1", tags=["identity"])


class MeResponse(BaseModel):
    person_id: str
    organization_context_id: str
    roles: list[str]


@router.get("/me", response_model=MeResponse)
async def me(actor: Annotated[ActorContext, Depends(get_actor)]) -> MeResponse:
    return MeResponse(
        person_id=str(actor.person_id),
        organization_context_id=str(actor.organization_context_id),
        roles=sorted(actor.roles),
    )
