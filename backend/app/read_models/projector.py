from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.academy.models import (
    ClassOffering,
    Cohort,
    CohortMembership,
    InstructorAssignment,
    Session,
)
from app.curriculum.models import CapabilityVersion, CurriculumWave, WaveCapability
from app.journey.models import CandidateJourney
from app.read_models.models import CandidateHomeProjection, InstructorHomeProjection


async def _upsert_candidate_projection(
    db: AsyncSession,
    person_id: UUID,
    organization_context_id: UUID,
    payload: dict,
) -> None:
    existing = (
        await db.execute(
            select(CandidateHomeProjection).where(
                CandidateHomeProjection.person_id == person_id,
                CandidateHomeProjection.organization_context_id == organization_context_id,
            )
        )
    ).scalar_one_or_none()
    now = datetime.now(UTC)
    if existing is None:
        db.add(
            CandidateHomeProjection(
                person_id=person_id,
                organization_context_id=organization_context_id,
                payload=payload,
                updated_at=now,
            )
        )
    else:
        existing.payload = payload
        existing.updated_at = now


async def _upsert_instructor_projection(
    db: AsyncSession,
    person_id: UUID,
    organization_context_id: UUID,
    payload: dict,
) -> None:
    existing = (
        await db.execute(
            select(InstructorHomeProjection).where(
                InstructorHomeProjection.person_id == person_id,
                InstructorHomeProjection.organization_context_id == organization_context_id,
            )
        )
    ).scalar_one_or_none()
    now = datetime.now(UTC)
    if existing is None:
        db.add(
            InstructorHomeProjection(
                person_id=person_id,
                organization_context_id=organization_context_id,
                payload=payload,
                updated_at=now,
            )
        )
    else:
        existing.payload = payload
        existing.updated_at = now


async def rebuild_candidate_home(
    db: AsyncSession,
    *,
    person_id: UUID,
    organization_context_id: UUID,
) -> bool:
    journey = (
        await db.execute(
            select(CandidateJourney).where(
                CandidateJourney.person_id == person_id,
                CandidateJourney.organization_context_id == organization_context_id,
                CandidateJourney.state == "ACTIVE",
            )
        )
    ).scalar_one_or_none()
    if journey is None:
        return False

    cohort = (
        await db.execute(
            select(Cohort).where(
                Cohort.id == journey.cohort_id,
                Cohort.organization_context_id == organization_context_id,
            )
        )
    ).scalar_one_or_none()
    if cohort is None:
        return False

    wave = (
        await db.execute(
            select(CurriculumWave).where(
                CurriculumWave.curriculum_id == journey.curriculum_version_id,
                CurriculumWave.code == journey.current_wave,
            )
        )
    ).scalar_one_or_none()
    if wave is None:
        return False

    capability_rows = (
        await db.execute(
            select(CapabilityVersion)
            .join(WaveCapability, WaveCapability.capability_version_id == CapabilityVersion.id)
            .where(WaveCapability.wave_id == wave.id)
            .order_by(WaveCapability.position)
        )
    ).scalars().all()

    session_rows = (
        await db.execute(
            select(Session, ClassOffering, CapabilityVersion)
            .join(ClassOffering, Session.class_offering_id == ClassOffering.id)
            .join(
                CapabilityVersion,
                ClassOffering.primary_capability_version_id == CapabilityVersion.id,
            )
            .where(
                ClassOffering.cohort_id == cohort.id,
                Session.status == "SCHEDULED",
            )
            .order_by(Session.starts_at)
        )
    ).all()

    upcoming_sessions = [
        {
            "session_id": str(session.id),
            "title": session.title,
            "starts_at": session.starts_at.isoformat(),
            "ends_at": session.ends_at.isoformat(),
            "delivery_mode": session.delivery_mode,
        }
        for session, _, _ in session_rows
    ]

    first_session_by_capability: dict[UUID, dict] = {}
    for session, class_offering, capability in session_rows:
        first_session_by_capability.setdefault(
            class_offering.primary_capability_version_id,
            {
                "session_id": str(session.id),
                "title": session.title,
                "starts_at": session.starts_at.isoformat(),
                "ends_at": session.ends_at.isoformat(),
                "delivery_mode": session.delivery_mode,
            },
        )

    what_to_learn = []
    for capability in capability_rows:
        next_session = first_session_by_capability.get(capability.id)
        if next_session is not None:
            what_to_learn.append(
                {
                    "capability_version_id": str(capability.id),
                    "name": capability.name,
                    "learning_state": "TO_LEARN",
                    "next_session": next_session,
                }
            )

    what_to_prove = [
        {
            "capability_version_id": str(capability.id),
            "name": capability.name,
            "proof_state": "UNPROVEN",
        }
        for capability in capability_rows
    ]

    await _upsert_candidate_projection(
        db,
        person_id,
        organization_context_id,
        {
            "journey": {"track": journey.track_code, "state": journey.state},
            "cohort": {"id": str(cohort.id), "name": cohort.name},
            "current_wave": {"code": wave.code, "name": wave.name},
            "upcoming_sessions": upcoming_sessions,
            "what_to_learn": what_to_learn,
            "what_to_prove": what_to_prove,
            "learning_tasks": [],
            "open_missions": [],
            "profile_summary": {"status": "UNPROVEN"},
            "processing_states": [],
        },
    )
    return True


async def rebuild_instructor_home(
    db: AsyncSession,
    *,
    person_id: UUID,
    organization_context_id: UUID,
) -> bool:
    assignments = (
        await db.execute(
            select(InstructorAssignment, ClassOffering, Cohort)
            .join(
                ClassOffering,
                InstructorAssignment.class_offering_id == ClassOffering.id,
            )
            .join(Cohort, ClassOffering.cohort_id == Cohort.id)
            .where(
                InstructorAssignment.person_id == person_id,
                Cohort.organization_context_id == organization_context_id,
            )
            .order_by(Cohort.starts_on, ClassOffering.title)
        )
    ).all()
    if not assignments:
        return False

    first_cohort = assignments[0][2]
    cohort_assignments = [row for row in assignments if row[2].id == first_cohort.id]
    class_ids = [row[1].id for row in cohort_assignments]

    sessions = (
        await db.execute(
            select(Session)
            .where(Session.class_offering_id.in_(class_ids), Session.status == "SCHEDULED")
            .order_by(Session.starts_at)
        )
    ).scalars().all()

    candidate_count = (
        await db.execute(
            select(func.count())
            .select_from(CohortMembership)
            .where(
                CohortMembership.cohort_id == first_cohort.id,
                CohortMembership.member_type == "CANDIDATE",
            )
        )
    ).scalar_one()

    first_class = cohort_assignments[0][1]
    capability = await db.get(CapabilityVersion, first_class.primary_capability_version_id)
    journey = (
        await db.execute(
            select(CandidateJourney)
            .where(
                CandidateJourney.cohort_id == first_cohort.id,
                CandidateJourney.state == "ACTIVE",
            )
            .limit(1)
        )
    ).scalar_one_or_none()

    wave_name = journey.current_wave if journey is not None else "—"
    if journey is not None:
        wave = (
            await db.execute(
                select(CurriculumWave).where(
                    CurriculumWave.curriculum_id == journey.curriculum_version_id,
                    CurriculumWave.code == journey.current_wave,
                )
            )
        ).scalar_one_or_none()
        if wave is not None:
            wave_name = wave.name

    await _upsert_instructor_projection(
        db,
        person_id,
        organization_context_id,
        {
            "assigned_cohort": {"id": str(first_cohort.id), "name": first_cohort.name},
            "assigned_classes": [
                {"id": str(class_offering.id), "title": class_offering.title}
                for _, class_offering, _ in cohort_assignments
            ],
            "upcoming_sessions": [
                {
                    "session_id": str(session.id),
                    "title": session.title,
                    "starts_at": session.starts_at.isoformat(),
                    "ends_at": session.ends_at.isoformat(),
                    "delivery_mode": session.delivery_mode,
                }
                for session in sessions
            ],
            "candidate_count": candidate_count,
            "capability_focus": capability.name if capability is not None else "—",
            "current_wave": {
                "code": journey.current_wave if journey is not None else "—",
                "name": wave_name,
            },
        },
    )
    return True


async def rebuild_cohort_read_models(
    db: AsyncSession,
    *,
    cohort_id: UUID,
    organization_context_id: UUID,
) -> None:
    members = (
        await db.execute(
            select(CohortMembership).where(CohortMembership.cohort_id == cohort_id)
        )
    ).scalars().all()
    for member in members:
        if member.member_type == "CANDIDATE":
            await rebuild_candidate_home(
                db,
                person_id=member.person_id,
                organization_context_id=organization_context_id,
            )
        elif member.member_type == "INSTRUCTOR":
            await rebuild_instructor_home(
                db,
                person_id=member.person_id,
                organization_context_id=organization_context_id,
            )
