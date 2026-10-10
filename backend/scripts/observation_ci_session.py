"""CI-ONLY: add a short synthetic Session for genuine OIDC Observation testing.

No production bootstrap, sample approval, or operational Session state is changed.
"""
from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.academy.models import ClassOffering, Cohort, Session
from app.db import SessionFactory
from app.identity.models import Organization, OrganizationMembership, Person

CLASS_ID = UUID("00000000-0000-0000-0000-000000000220")
CI_SESSION_ID = UUID("00000000-0000-0000-0000-000000000243")
REVIEWER_PERSON_ID = UUID("00000000-0000-0000-0000-000000000105")
FINAL_PERSON_ID = UUID("00000000-0000-0000-0000-000000000106")
ORG_ID = UUID("00000000-0000-0000-0000-000000000001")
SECOND_CLASS_ID = UUID("00000000-0000-0000-0000-000000000221")
SECOND_SESSION_ID = UUID("00000000-0000-0000-0000-000000000244")
FOREIGN_ORG_ID = UUID("00000000-0000-0000-0000-000000000002")
FOREIGN_COHORT_ID = UUID("00000000-0000-0000-0000-000000000202")
FOREIGN_CLASS_ID = UUID("00000000-0000-0000-0000-000000000222")
BASE_CAPABILITY_ID = UUID("20000000-0000-0000-0000-000000000001")


async def main() -> None:
    now = datetime.now(UTC)
    async with SessionFactory() as db:
        # Identity is mapped to the fresh Keycloak user created only in CI.
        db.add(
            Person(
                id=REVIEWER_PERSON_ID,
                external_subject=str(UUID(os.environ["PARCHAM_CI_REVIEWER_SUBJECT"])),
                display_name="CI-only independent Assessor",
                created_at=now,
                updated_at=now,
            )
        )
        await db.flush()  # Foreign key requires the new Person row first.
        db.add(
            OrganizationMembership(
                id=UUID("00000000-0000-0000-0000-000000000115"),
                person_id=REVIEWER_PERSON_ID,
                organization_id=ORG_ID,
                membership_role="ASSESSOR",
                created_at=now,
            )
        )
        db.add(
            Person(
                id=FINAL_PERSON_ID,
                external_subject=str(UUID(os.environ["PARCHAM_CI_FINAL_REVIEWER_SUBJECT"])),
                display_name="CI-only final Evidence reviewer",
                created_at=now,
                updated_at=now,
            )
        )
        await db.flush()
        db.add(
            OrganizationMembership(
                id=UUID("00000000-0000-0000-0000-000000000116"),
                person_id=FINAL_PERSON_ID,
                organization_id=ORG_ID,
                membership_role="ASSESSOR",
                created_at=now,
            )
        )
        # These additional classes exist ONLY in isolated CI, never in
        # Production seed, curriculum, or a customer's operational database.
        db.add(Organization(
            id=FOREIGN_ORG_ID, name="CI foreign organization",
            created_at=now, updated_at=now,
        ))
        db.add(Cohort(
            id=FOREIGN_COHORT_ID, organization_context_id=FOREIGN_ORG_ID,
            code="CI-FOREIGN", name="CI foreign cohort", track_code="PRODUCT_MANAGER",
            status="ACTIVE", starts_on=now.date(), ends_on=None,
        ))
        await db.flush()
        db.add_all([
            ClassOffering(
                id=SECOND_CLASS_ID,
                cohort_id=UUID("00000000-0000-0000-0000-000000000201"),
                title="ZZ CI-only same-tenant second class",
                primary_capability_version_id=BASE_CAPABILITY_ID,
                status="ACTIVE",
            ),
            ClassOffering(
                id=FOREIGN_CLASS_ID, cohort_id=FOREIGN_COHORT_ID,
                title="CI-only other-tenant class",
                primary_capability_version_id=BASE_CAPABILITY_ID,
                status="ACTIVE",
            ),
        ])
        await db.flush()
        db.add_all([
            Session(
                id=CI_SESSION_ID, class_offering_id=CLASS_ID,
                title="CI-only current session, not a real Academy class",
                starts_at=now - timedelta(minutes=30),
                ends_at=now + timedelta(minutes=30),
                delivery_mode="ONLINE", status="ACTIVE",
            ),
            Session(
                id=SECOND_SESSION_ID, class_offering_id=SECOND_CLASS_ID,
                title="CI-only second-class current session",
                starts_at=now - timedelta(minutes=30),
                ends_at=now + timedelta(minutes=30),
                delivery_mode="ONLINE", status="ACTIVE",
            ),
        ])
        await db.commit()


if __name__ == "__main__":
    asyncio.run(main())
