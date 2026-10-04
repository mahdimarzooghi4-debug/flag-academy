from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import delete

from app.academy.models import (
    ClassOffering,
    Cohort,
    CohortMembership,
    InstructorAssignment,
    Session,
)
from app.curriculum.domain import CAPABILITY_CODES
from app.curriculum.models import (
    Capability,
    CapabilityVersion,
    Curriculum,
    CurriculumWave,
    WaveCapability,
)
from app.db import SessionFactory
from app.identity.models import Organization, OrganizationMembership, Person
from app.journey.models import CandidateJourney
from app.platform.events import new_event, record_event
from app.platform.models import DomainEvent, InboxEvent, OutboxEvent
from app.read_models.models import CandidateHomeProjection, InstructorHomeProjection
from app.read_models.projector import rebuild_candidate_home, rebuild_instructor_home

ORG_ID = UUID("00000000-0000-0000-0000-000000000001")
CANDIDATE_ID = UUID("00000000-0000-0000-0000-000000000101")
INSTRUCTOR_ID = UUID("00000000-0000-0000-0000-000000000102")
COHORT_ID = UUID("00000000-0000-0000-0000-000000000201")
CURRICULUM_ID = UUID("00000000-0000-0000-0000-000000000301")

NAMES = {
    "OWNERSHIP_ACCOUNTABILITY": "Ownership & Accountability",
    "PROBLEM_FRAMING": "Problem Framing",
    "DECISION_MAKING": "Decision Making",
    "DATA_THINKING": "Data Thinking",
    "CUSTOMER_UNDERSTANDING": "Customer Understanding",
    "PRODUCT_DISCOVERY": "Product Discovery",
    "PRODUCT_STRATEGY": "Product Strategy",
    "PRIORITIZATION": "Prioritization",
    "METRICS_EXPERIMENTATION": "Metrics & Experimentation",
    "PRODUCT_ECONOMICS": "Product Economics",
    "DELIVERY": "Delivery",
    "STAKEHOLDER_ALIGNMENT": "Stakeholder Alignment",
    "PRODUCT_LEADERSHIP": "Product Leadership",
    "SYSTEM_BUILDING": "System Building",
    "REFLECTION_LEARNING": "Reflection & Learning",
}
WAVES = [
    ("WAVE_1", "Think & Own", ["OWNERSHIP_ACCOUNTABILITY","PROBLEM_FRAMING","DECISION_MAKING","DATA_THINKING","REFLECTION_LEARNING"]),
    ("WAVE_2", "Discover & Decide", ["CUSTOMER_UNDERSTANDING","PRODUCT_DISCOVERY","METRICS_EXPERIMENTATION"]),
    ("WAVE_3", "Direct & Deliver", ["PRODUCT_STRATEGY","PRIORITIZATION","PRODUCT_ECONOMICS","DELIVERY","STAKEHOLDER_ALIGNMENT"]),
    ("WAVE_4", "Lead & Build", ["PRODUCT_LEADERSHIP","SYSTEM_BUILDING"]),
]


async def seed() -> None:
    now = datetime.now(UTC)
    async with SessionFactory() as db:
        # Development seed is intentionally deterministic and disposable.
        for model in (
            InboxEvent,
            OutboxEvent,
            DomainEvent,
            CandidateHomeProjection,
            InstructorHomeProjection,
            CandidateJourney,
            InstructorAssignment,
            Session,
            ClassOffering,
            CohortMembership,
            Cohort,
            WaveCapability,
            CurriculumWave,
            Curriculum,
            CapabilityVersion,
            Capability,
            OrganizationMembership,
            Person,
            Organization,
        ):
            await db.execute(delete(model))

        org = Organization(id=ORG_ID, name="Flag Academy Demo", created_at=now, updated_at=now)
        candidate = Person(
            id=CANDIDATE_ID,
            external_subject="11111111-1111-1111-1111-111111111111",
            display_name="Candidate Demo",
            created_at=now,
            updated_at=now,
        )
        instructor = Person(
            id=INSTRUCTOR_ID,
            external_subject="22222222-2222-2222-2222-222222222222",
            display_name="Instructor Demo",
            created_at=now,
            updated_at=now,
        )
        db.add_all([org, candidate, instructor])
        await db.flush()
        db.add_all([
            OrganizationMembership(
                id=UUID("00000000-0000-0000-0000-000000000111"),
                person_id=CANDIDATE_ID,
                organization_id=ORG_ID,
                membership_role="CANDIDATE",
                created_at=now,
            ),
            OrganizationMembership(
                id=UUID("00000000-0000-0000-0000-000000000112"),
                person_id=INSTRUCTOR_ID,
                organization_id=ORG_ID,
                membership_role="INSTRUCTOR",
                created_at=now,
            ),
        ])

        versions: dict[str, UUID] = {}
        for index, code in enumerate(CAPABILITY_CODES, start=1):
            capability_id = UUID(f"10000000-0000-0000-0000-{index:012d}")
            version_id = UUID(f"20000000-0000-0000-0000-{index:012d}")
            versions[code] = version_id
            db.add(Capability(id=capability_id, code=code))
            db.add(
                CapabilityVersion(
                    id=version_id,
                    definition_id=capability_id,
                    version_number=1,
                    name=NAMES[code],
                    definition=f"Flag Academy capability: {NAMES[code]}",
                    status="ACTIVE",
                )
            )

        await db.flush()

        curriculum = Curriculum(
            id=CURRICULUM_ID,
            code="PRODUCT_MANAGER",
            version_number=1,
            name="Product Manager Curriculum v1",
            status="ACTIVE",
        )
        db.add(curriculum)
        await db.flush()
        for wave_index, (wave_code, wave_name, capability_codes) in enumerate(WAVES, start=1):
            wave_id = UUID(f"30000000-0000-0000-0000-{wave_index:012d}")
            db.add(
                CurriculumWave(
                    id=wave_id,
                    curriculum_id=CURRICULUM_ID,
                    code=wave_code,
                    name=wave_name,
                    position=wave_index,
                )
            )
            await db.flush()
            for position, code in enumerate(capability_codes, start=1):
                db.add(
                    WaveCapability(
                        id=UUID(f"31000000-0000-{wave_index:04d}-0000-{position:012d}"),
                        wave_id=wave_id,
                        capability_version_id=versions[code],
                        position=position,
                    )
                )

        await db.flush()
        db.add(
            Cohort(
                id=COHORT_ID,
                organization_context_id=ORG_ID,
                code="PM-2026-WINTER",
                name="PM Flag Cohort — Winter 2026",
                track_code="PRODUCT_MANAGER",
                status="ACTIVE",
                starts_on=date(2026, 10, 1),
                ends_on=date(2027, 1, 31),
            )
        )
        await db.flush()
        db.add_all([
            CohortMembership(
                id=UUID("00000000-0000-0000-0000-000000000211"),
                cohort_id=COHORT_ID,
                person_id=CANDIDATE_ID,
                member_type="CANDIDATE",
            ),
            CohortMembership(
                id=UUID("00000000-0000-0000-0000-000000000212"),
                cohort_id=COHORT_ID,
                person_id=INSTRUCTOR_ID,
                member_type="INSTRUCTOR",
            ),
        ])

        await db.flush()
        class_id = UUID("00000000-0000-0000-0000-000000000220")
        db.add(
            ClassOffering(
                id=class_id,
                cohort_id=COHORT_ID,
                title="Ownership & Accountability",
                primary_capability_version_id=versions["OWNERSHIP_ACCOUNTABILITY"],
                status="ACTIVE",
            )
        )
        await db.flush()
        db.add(
            InstructorAssignment(
                id=UUID("00000000-0000-0000-0000-000000000230"),
                class_offering_id=class_id,
                person_id=INSTRUCTOR_ID,
            )
        )
        session_items = []
        for index, day_offset in enumerate((1, 8), start=1):
            start = now + timedelta(days=day_offset)
            item = Session(
                id=UUID(f"00000000-0000-0000-0000-{240 + index:012d}"),
                class_offering_id=class_id,
                title=f"Ownership & Accountability — Session {index}",
                starts_at=start,
                ends_at=start + timedelta(hours=2),
                delivery_mode="HYBRID",
                status="SCHEDULED",
            )
            db.add(item)
            session_items.append(item)

        journey_id = UUID("00000000-0000-0000-0000-000000000401")
        db.add(
            CandidateJourney(
                id=journey_id,
                person_id=CANDIDATE_ID,
                organization_context_id=ORG_ID,
                cohort_id=COHORT_ID,
                track_code="PRODUCT_MANAGER",
                curriculum_version_id=CURRICULUM_ID,
                state="ACTIVE",
                current_wave="WAVE_1",
                created_at=now,
                updated_at=now,
            )
        )

        await db.flush()
        await rebuild_candidate_home(
            db,
            person_id=CANDIDATE_ID,
            organization_context_id=ORG_ID,
        )
        await rebuild_instructor_home(
            db,
            person_id=INSTRUCTOR_ID,
            organization_context_id=ORG_ID,
        )

        event_actor = {"type": "SYSTEM", "id": "development-seed"}
        for envelope in (
            new_event(
                event_type="academy.cohort_created.v1",
                aggregate_type="Cohort",
                aggregate_id=COHORT_ID,
                aggregate_version=1,
                actor=event_actor,
                organization_context_id=ORG_ID,
                data_classification="INTERNAL",
                payload={"cohort_id": str(COHORT_ID), "track_code": "PRODUCT_MANAGER"},
                trace_id="development-seed",
                occurred_at=now,
            ),
            new_event(
                event_type="academy.session_scheduled.v1",
                aggregate_type="ClassOffering",
                aggregate_id=class_id,
                aggregate_version=1,
                actor=event_actor,
                organization_context_id=ORG_ID,
                data_classification="INTERNAL",
                payload={
                    "class_offering_id": str(class_id),
                    "session_ids": [str(item.id) for item in session_items],
                },
                trace_id="development-seed",
                occurred_at=now,
            ),
            new_event(
                event_type="candidate.journey_created.v1",
                aggregate_type="CandidateJourney",
                aggregate_id=journey_id,
                aggregate_version=1,
                actor=event_actor,
                organization_context_id=ORG_ID,
                data_classification="INTERNAL",
                payload={
                    "journey_id": str(journey_id),
                    "candidate_id": str(CANDIDATE_ID),
                    "cohort_id": str(COHORT_ID),
                },
                trace_id="development-seed",
                occurred_at=now,
            ),
        ):
            record_event(db, envelope)

        await db.commit()


if __name__ == "__main__":
    asyncio.run(seed())
