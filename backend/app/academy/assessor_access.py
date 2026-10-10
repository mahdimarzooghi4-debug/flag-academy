"""Single fail-closed Academy Assessor class read-authorization contract.

Class mandates are Academy-owned. Evidence/Flag Profile/Gate authorization
stays in its own bounded context; this helper only gates classroom projections.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.academy.assessor_grants_policy import (
    GrantWindow,
    active_class_grant,
    current_utc,
)
from app.academy.models import AssessorClassGrant, ClassOffering, Cohort
from app.identity.auth import ActorContext
from app.identity.public_reader import has_organization_role


async def has_live_assessor_class_access(
    db: AsyncSession,
    *,
    actor: ActorContext,
    class_offering_id: UUID,
) -> bool:
    """Require current ASSESSOR membership AND an active grant for this exact class.

    Never infer a mandate from the organization, cohort, CapabilityVersion,
    person identity or access to an EvidenceCase. Revocation/expiry and
    non-operational classes invalidate grants without any cache.
    """
    if "ASSESSOR" not in actor.roles:
        return False

    scoped_row = (
        await db.execute(
            select(AssessorClassGrant, ClassOffering, Cohort)
            .join(
                ClassOffering,
                AssessorClassGrant.class_offering_id == ClassOffering.id,
            )
            .join(Cohort, ClassOffering.cohort_id == Cohort.id)
            .where(
                AssessorClassGrant.organization_context_id
                == actor.organization_context_id,
                AssessorClassGrant.assessor_person_id == actor.person_id,
                AssessorClassGrant.class_offering_id == class_offering_id,
                Cohort.organization_context_id == actor.organization_context_id,
            )
        )
    ).first()
    if scoped_row is None:
        return False
    grant, offering, cohort = scoped_row

    if not active_class_grant(
        GrantWindow(
            starts_at=grant.starts_at,
            ends_at=grant.ends_at,
            revoked_at=grant.revoked_at,
        ),
        now=current_utc(),
        class_status=offering.status,
        cohort_status=cohort.status,
    ):
        return False

    # A persisted grant is not evidence of current organization membership.
    return await has_organization_role(
        db,
        person_id=actor.person_id,
        organization_id=actor.organization_context_id,
        role="ASSESSOR",
    )
