import asyncio
from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.errors import AppError
from app.identity.models import OrganizationMembership, Person

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class ActorContext:
    actor_id: str
    person_id: UUID
    organization_context_id: UUID
    roles: frozenset[str]
    trace_id: str = ""


async def get_actor(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    session: Annotated[AsyncSession, Depends(get_session)],
    organization_context: Annotated[
        UUID | None, Header(alias="X-Organization-Context")
    ] = None,
) -> ActorContext:
    if credentials is None:
        raise AppError(
            "AUTHENTICATION_REQUIRED",
            "Authentication is required.",
            status_code=401,
        )

    settings = get_settings()
    try:
        signing_key = await asyncio.to_thread(
            PyJWKClient(settings.oidc_jwks_url).get_signing_key_from_jwt,
            credentials.credentials,
        )
        claims = jwt.decode(
            credentials.credentials,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.oidc_audience,
            issuer=settings.oidc_issuer,
        )
    except Exception as exc:
        raise AppError(
            "AUTHENTICATION_REQUIRED",
            "The access token is invalid.",
            status_code=401,
        ) from exc

    subject = str(claims["sub"])
    person = (
        await session.execute(select(Person).where(Person.external_subject == subject))
    ).scalar_one_or_none()
    if person is None:
        raise AppError("PERSON_NOT_FOUND", "No person is mapped to this identity.", status_code=404)

    memberships = (
        await session.execute(
            select(OrganizationMembership).where(OrganizationMembership.person_id == person.id)
        )
    ).scalars().all()
    if not memberships:
        raise AppError(
            "ORGANIZATION_CONTEXT_REQUIRED",
            "No organization context is available.",
            status_code=403,
        )

    selected = None
    if organization_context is not None:
        selected = next(
            (m for m in memberships if m.organization_id == organization_context),
            None,
        )
        if selected is None:
            raise AppError(
                "INSUFFICIENT_PERMISSION",
                "The organization context is not available to this user.",
                status_code=403,
            )
    elif len({m.organization_id for m in memberships}) == 1:
        selected = memberships[0]
    else:
        raise AppError(
            "ORGANIZATION_CONTEXT_REQUIRED",
            "Choose an organization context.",
            status_code=422,
        )

    # Organization membership is authoritative for contextual product permissions.
    # Realm roles may describe identity-provider capabilities but must not grant
    # access in an organization where the person has no matching membership role.
    membership_roles = {
        m.membership_role
        for m in memberships
        if m.organization_id == selected.organization_id
    }
    return ActorContext(
        actor_id=subject,
        person_id=person.id,
        organization_context_id=selected.organization_id,
        roles=frozenset(membership_roles),
        trace_id=getattr(request.state, "trace_id", ""),
    )


def require_role(*allowed: str):
    async def dependency(actor: Annotated[ActorContext, Depends(get_actor)]) -> ActorContext:
        if not actor.roles.intersection(allowed):
            raise AppError(
                "INSUFFICIENT_PERMISSION",
                "You do not have permission to access this resource.",
                status_code=403,
            )
        return actor

    return dependency
