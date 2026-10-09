"""Identity-owned read contract for current organization role membership."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.identity.models import OrganizationMembership


async def has_organization_role(
    db: AsyncSession, *, person_id: UUID, organization_id: UUID, role: str
) -> bool:
    membership_id = (
        await db.execute(
            select(OrganizationMembership.id).where(
                OrganizationMembership.person_id == person_id,
                OrganizationMembership.organization_id == organization_id,
                OrganizationMembership.membership_role == role,
            )
        )
    ).scalar_one_or_none()
    return membership_id is not None
