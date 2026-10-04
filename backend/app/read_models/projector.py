from __future__ import annotations

from collections.abc import Sequence
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
from app.identity.models import Person
from app.journey.models import CandidateJourney
from app.learning.models import (
    Assignment,
    InstructorFeedback,
    LearningUnit,
    LearningUnitProgress,
    PracticeAttempt,
    PracticeFeedback,
    Submission,
)
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


async def _latest_feedback_by_submission(
    db: AsyncSession,
    submission_ids: list[UUID],
) -> dict[UUID, InstructorFeedback]:
    if not submission_ids:
        return {}
    rows = (
        await db.execute(
            select(InstructorFeedback)
            .where(InstructorFeedback.submission_id.in_(submission_ids))
            .order_by(InstructorFeedback.created_at)
        )
    ).scalars().all()
    result: dict[UUID, InstructorFeedback] = {}
    for row in rows:
        result[row.submission_id] = row
    return result


async def _practice_feedback_history(
    db: AsyncSession,
    attempt_ids: list[UUID],
) -> dict[UUID, list[PracticeFeedback]]:
    if not attempt_ids:
        return {}
    rows = (
        await db.execute(
            select(PracticeFeedback)
            .where(PracticeFeedback.practice_attempt_id.in_(attempt_ids))
            .order_by(PracticeFeedback.created_at)
        )
    ).scalars().all()
    result: dict[UUID, list[PracticeFeedback]] = {}
    for row in rows:
        result.setdefault(row.practice_attempt_id, []).append(row)
    return result


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

    class_offerings = (
        await db.execute(
            select(ClassOffering)
            .where(ClassOffering.cohort_id == cohort.id, ClassOffering.status == "ACTIVE")
            .order_by(ClassOffering.title)
        )
    ).scalars().all()
    class_ids = [item.id for item in class_offerings]

    session_rows = []
    if class_ids:
        session_rows = (
            await db.execute(
                select(Session, ClassOffering)
                .join(ClassOffering, Session.class_offering_id == ClassOffering.id)
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
        for session, _ in session_rows
    ]

    first_session_by_capability: dict[UUID, dict] = {}
    for session, class_offering in session_rows:
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

    units: Sequence[LearningUnit] = []
    assignments: Sequence[Assignment] = []
    if class_ids:
        units = (
            await db.execute(
                select(LearningUnit)
                .where(
                    LearningUnit.class_offering_id.in_(class_ids),
                    LearningUnit.status == "ACTIVE",
                )
                .order_by(LearningUnit.class_offering_id, LearningUnit.position)
            )
        ).scalars().all()
        assignments = (
            await db.execute(
                select(Assignment)
                .where(
                    Assignment.class_offering_id.in_(class_ids),
                    Assignment.status == "ACTIVE",
                )
                .order_by(Assignment.due_at)
            )
        ).scalars().all()

    unit_ids = [item.id for item in units]
    progresses: Sequence[LearningUnitProgress] = []
    if unit_ids:
        progresses = (
            await db.execute(
                select(LearningUnitProgress).where(
                    LearningUnitProgress.learning_unit_id.in_(unit_ids),
                    LearningUnitProgress.candidate_id == person_id,
                )
            )
        ).scalars().all()
    progress_by_unit = {item.learning_unit_id: item for item in progresses}

    practice_attempts: Sequence[PracticeAttempt] = []
    practice_unit_ids = [item.id for item in units if item.phase == "PRACTICE"]
    if practice_unit_ids:
        practice_attempts = (
            await db.execute(
                select(PracticeAttempt)
                .where(
                    PracticeAttempt.learning_unit_id.in_(practice_unit_ids),
                    PracticeAttempt.candidate_id == person_id,
                )
                .order_by(
                    PracticeAttempt.learning_unit_id,
                    PracticeAttempt.attempt_number,
                )
            )
        ).scalars().all()
    practice_attempts_by_unit: dict[UUID, list[PracticeAttempt]] = {}
    for attempt in practice_attempts:
        practice_attempts_by_unit.setdefault(attempt.learning_unit_id, []).append(attempt)
    practice_feedback_history = await _practice_feedback_history(
        db, [item.id for item in practice_attempts]
    )

    assignment_ids = [item.id for item in assignments]
    submissions: Sequence[Submission] = []
    if assignment_ids:
        submissions = (
            await db.execute(
                select(Submission).where(
                    Submission.assignment_id.in_(assignment_ids),
                    Submission.candidate_id == person_id,
                )
            )
        ).scalars().all()
    submission_by_assignment = {item.assignment_id: item for item in submissions}
    feedback_by_submission = await _latest_feedback_by_submission(
        db, [item.id for item in submissions]
    )

    what_to_learn = []
    for capability in capability_rows:
        next_session = first_session_by_capability.get(capability.id)
        capability_units = [
            unit for unit in units if unit.capability_version_id == capability.id
        ]
        capability_assignments = [
            assignment
            for assignment in assignments
            if assignment.capability_version_id == capability.id
        ]
        has_requirements = bool(capability_units or capability_assignments)
        all_units_completed = all(
            progress_by_unit.get(unit.id) is not None
            and progress_by_unit[unit.id].state == "COMPLETED"
            for unit in capability_units
        )
        all_assignments_submitted = all(
            assignment.id in submission_by_assignment
            for assignment in capability_assignments
        )
        has_activity = any(
            unit.id in progress_by_unit for unit in capability_units
        ) or any(
            assignment.id in submission_by_assignment
            for assignment in capability_assignments
        )

        if has_requirements and all_units_completed and all_assignments_submitted:
            learning_state = "LEARNING_COMPLETED"
        elif has_activity:
            learning_state = "IN_LEARNING"
        else:
            learning_state = "TO_LEARN"

        if next_session is not None or has_requirements:
            what_to_learn.append(
                {
                    "capability_version_id": str(capability.id),
                    "name": capability.name,
                    "learning_state": learning_state,
                    "next_session": next_session,
                }
            )

    learning_tasks: list[dict] = []
    for unit in units:
        task_type = (
            "PRE_WORK"
            if unit.phase == "PRE_WORK"
            else "PRACTICE"
            if unit.phase == "PRACTICE"
            else unit.unit_type
        )
        unit_attempts = practice_attempts_by_unit.get(unit.id, [])
        latest_attempt = unit_attempts[-1] if unit_attempts else None
        latest_feedback = (
            practice_feedback_history.get(latest_attempt.id, [])
            if latest_attempt is not None
            else []
        )
        learning_tasks.append(
            {
                "id": str(unit.id),
                "task_type": task_type,
                "title": unit.title,
                "class_offering_id": str(unit.class_offering_id),
                "capability_version_id": str(unit.capability_version_id),
                "status": (
                    progress_by_unit[unit.id].state
                    if unit.id in progress_by_unit
                    else "NOT_STARTED"
                ),
                "body": unit.body,
                "due_at": None,
                "submission_id": (
                    str(latest_attempt.id) if latest_attempt is not None else None
                ),
                "feedback_text": (
                    latest_feedback[-1].feedback_text if latest_feedback else None
                ),
                "replay_available": (
                    latest_attempt is not None
                    and latest_attempt.status == "FEEDBACK_PROVIDED"
                ),
                "practice_attempts": [
                    {
                        "id": str(attempt.id),
                        "attempt_number": attempt.attempt_number,
                        "replay_of_attempt_id": (
                            str(attempt.replay_of_attempt_id)
                            if attempt.replay_of_attempt_id is not None
                            else None
                        ),
                        "response_text": attempt.response_text,
                        "status": attempt.status,
                        "submitted_at": attempt.submitted_at.isoformat(),
                        "feedback_history": [
                            {
                                "id": str(feedback.id),
                                "feedback_text": feedback.feedback_text,
                                "created_at": feedback.created_at.isoformat(),
                            }
                            for feedback in practice_feedback_history.get(attempt.id, [])
                        ],
                    }
                    for attempt in unit_attempts
                ],
            }
        )

    for assignment in assignments:
        submission = submission_by_assignment.get(assignment.id)
        feedback = feedback_by_submission.get(submission.id) if submission else None
        learning_tasks.append(
            {
                "id": str(assignment.id),
                "task_type": "ASSIGNMENT",
                "title": assignment.title,
                "class_offering_id": str(assignment.class_offering_id),
                "capability_version_id": str(assignment.capability_version_id),
                "status": submission.status if submission else "NOT_SUBMITTED",
                "body": assignment.instructions,
                "due_at": assignment.due_at.isoformat() if assignment.due_at else None,
                "submission_id": str(submission.id) if submission else None,
                "feedback_text": feedback.feedback_text if feedback else None,
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
            "learning_tasks": learning_tasks,
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

    learning_units = (
        await db.execute(
            select(LearningUnit)
            .where(
                LearningUnit.class_offering_id.in_(class_ids),
                LearningUnit.status == "ACTIVE",
            )
            .order_by(LearningUnit.class_offering_id, LearningUnit.position)
        )
    ).scalars().all()
    practice_units = [item for item in learning_units if item.phase == "PRACTICE"]
    practice_attempts: Sequence[PracticeAttempt] = []
    if practice_units:
        practice_attempts = (
            await db.execute(
                select(PracticeAttempt)
                .where(
                    PracticeAttempt.learning_unit_id.in_(
                        [item.id for item in practice_units]
                    )
                )
                .order_by(
                    PracticeAttempt.candidate_id,
                    PracticeAttempt.learning_unit_id,
                    PracticeAttempt.attempt_number,
                )
            )
        ).scalars().all()
    practice_feedback_history = await _practice_feedback_history(
        db, [item.id for item in practice_attempts]
    )
    practice_unit_by_id = {item.id: item for item in practice_units}

    learning_assignments = (
        await db.execute(
            select(Assignment)
            .where(
                Assignment.class_offering_id.in_(class_ids),
                Assignment.status == "ACTIVE",
            )
            .order_by(Assignment.due_at)
        )
    ).scalars().all()

    assignment_ids = [item.id for item in learning_assignments]
    submissions: Sequence[Submission] = []
    if assignment_ids:
        submissions = (
            await db.execute(
                select(Submission)
                .where(Submission.assignment_id.in_(assignment_ids))
                .order_by(Submission.submitted_at)
            )
        ).scalars().all()
    feedback_by_submission = await _latest_feedback_by_submission(
        db, [item.id for item in submissions]
    )
    assignment_by_id = {item.id: item for item in learning_assignments}

    candidate_ids = list(
        {item.candidate_id for item in submissions}
        | {item.candidate_id for item in practice_attempts}
    )
    person_by_id: dict[UUID, Person] = {}
    if candidate_ids:
        people = (
            await db.execute(select(Person).where(Person.id.in_(candidate_ids)))
        ).scalars().all()
        person_by_id = {item.id: item for item in people}

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
            "learning_units": [
                {
                    "id": str(item.id),
                    "title": item.title,
                    "phase": item.phase,
                    "unit_type": item.unit_type,
                    "body": item.body,
                }
                for item in learning_units
            ],
            "assignments": [
                {
                    "id": str(item.id),
                    "title": item.title,
                    "instructions": item.instructions,
                    "due_at": item.due_at.isoformat() if item.due_at else None,
                    "status": item.status,
                }
                for item in learning_assignments
            ],
            "practice_attempts": [
                {
                    "id": str(item.id),
                    "learning_unit_id": str(item.learning_unit_id),
                    "practice_title": practice_unit_by_id[item.learning_unit_id].title,
                    "candidate_id": str(item.candidate_id),
                    "candidate_name": (
                        person_by_id[item.candidate_id].display_name
                        if item.candidate_id in person_by_id
                        else str(item.candidate_id)
                    ),
                    "attempt_number": item.attempt_number,
                    "replay_of_attempt_id": (
                        str(item.replay_of_attempt_id)
                        if item.replay_of_attempt_id is not None
                        else None
                    ),
                    "response_text": item.response_text,
                    "status": item.status,
                    "feedback_text": (
                        practice_feedback_history[item.id][-1].feedback_text
                        if item.id in practice_feedback_history
                        and practice_feedback_history[item.id]
                        else None
                    ),
                    "feedback_history": [
                        {
                            "id": str(feedback.id),
                            "feedback_text": feedback.feedback_text,
                            "created_at": feedback.created_at.isoformat(),
                        }
                        for feedback in practice_feedback_history.get(item.id, [])
                    ],
                }
                for item in practice_attempts
            ],
            "submissions": [
                {
                    "id": str(item.id),
                    "assignment_id": str(item.assignment_id),
                    "assignment_title": assignment_by_id[item.assignment_id].title,
                    "candidate_id": str(item.candidate_id),
                    "candidate_name": (
                        person_by_id[item.candidate_id].display_name
                        if item.candidate_id in person_by_id
                        else str(item.candidate_id)
                    ),
                    "content_text": item.content_text,
                    "status": item.status,
                    "feedback_text": (
                        feedback_by_submission[item.id].feedback_text
                        if item.id in feedback_by_submission
                        else None
                    ),
                }
                for item in submissions
            ],
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
