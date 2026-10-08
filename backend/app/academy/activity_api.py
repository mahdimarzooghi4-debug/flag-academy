"""Source-linked operational class timeline; never a formal evidence producer."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.academy.models import (
    AttendanceRecord,
    ClassOffering,
    Cohort,
    CohortMembership,
    InstructorAssignment,
    Session,
)
from app.db import get_session
from app.errors import AppError
from app.identity.auth import ActorContext, get_actor
from app.learning.models import (
    Assignment,
    InstructorFeedback,
    LearningUnit,
    LearningUnitProgress,
    PracticeAttempt,
    PracticeFeedback,
    Submission,
)

router = APIRouter(prefix="/api/v1", tags=["academy"])


class ClassActivityItem(BaseModel):
    source_type: str
    source_id: UUID
    source_parent_id: UUID | None = None
    person_id: UUID
    class_offering_id: UUID
    capability_version_id: UUID | None = None
    session_id: UUID | None = None
    occurred_at: datetime
    state: str | None = None


class ClassActivityResponse(BaseModel):
    class_offering_id: UUID
    items: list[ClassActivityItem]
    is_truncated: bool


async def _visible_candidate_ids(
    db: AsyncSession,
    *,
    actor: ActorContext,
    class_offering_id: UUID,
) -> list[UUID]:
    # Resolve class identity inside the selected organization before any data projection.
    row = (
        await db.execute(
            select(ClassOffering, Cohort)
            .join(Cohort, ClassOffering.cohort_id == Cohort.id)
            .where(
                ClassOffering.id == class_offering_id,
                Cohort.organization_context_id == actor.organization_context_id,
            )
        )
    ).first()
    if row is None:
        raise AppError("CLASS_NOT_FOUND", "Class not found.", status_code=404)
    offering, cohort = row
    candidate_ids = list(
        (
            await db.execute(
                select(CohortMembership.person_id)
                .where(
                    CohortMembership.cohort_id == cohort.id,
                    CohortMembership.member_type == "CANDIDATE",
                )
                .order_by(CohortMembership.person_id)
            )
        ).scalars().all()
    )
    if "ACADEMY_ADMIN" in actor.roles:
        return candidate_ids
    if "INSTRUCTOR" in actor.roles:
        assignment_id = (
            await db.execute(
                select(InstructorAssignment.id).where(
                    InstructorAssignment.class_offering_id == offering.id,
                    InstructorAssignment.person_id == actor.person_id,
                )
            )
        ).scalar_one_or_none()
        if assignment_id is not None:
            return candidate_ids
    if "CANDIDATE" in actor.roles and actor.person_id in candidate_ids:
        return [actor.person_id]
    # In particular ASSESSOR alone is not a class-wide authorization.
    raise AppError("CLASS_NOT_FOUND", "Class not found.", status_code=404)


@router.get(
    "/class-offerings/{class_offering_id}/activity",
    response_model=ClassActivityResponse,
)
async def class_activity(
    class_offering_id: UUID,
    actor: Annotated[ActorContext, Depends(get_actor)],
    db: Annotated[AsyncSession, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> ClassActivityResponse:
    """Read current source facts, not an invented historical event stream."""
    visible = await _visible_candidate_ids(
        db, actor=actor, class_offering_id=class_offering_id
    )
    if not visible:
        return ClassActivityResponse(
            class_offering_id=class_offering_id, items=[], is_truncated=False
        )

    items: list[ClassActivityItem] = []
    # Limit each source separately so a busy source cannot crowd out newer
    # activity elsewhere; merge/sort after source-local bounded reads.
    progress_rows = (
        await db.execute(
            select(LearningUnitProgress, LearningUnit)
            .join(LearningUnit, LearningUnitProgress.learning_unit_id == LearningUnit.id)
            .where(
                LearningUnit.class_offering_id == class_offering_id,
                LearningUnitProgress.candidate_id.in_(visible),
            )
            .order_by(LearningUnitProgress.updated_at.desc(), LearningUnitProgress.id)
            .limit(limit + 1)
        )
    ).all()
    for progress, unit in progress_rows:
        items.append(
            ClassActivityItem(
                source_type="LEARNING_UNIT_PROGRESS",
                source_id=progress.id,
                source_parent_id=unit.id,
                person_id=progress.candidate_id,
                class_offering_id=class_offering_id,
                capability_version_id=unit.capability_version_id,
                occurred_at=progress.updated_at,
                state=progress.state,
            )
        )

    submission_rows = (
        await db.execute(
            select(Submission, Assignment)
            .join(Assignment, Submission.assignment_id == Assignment.id)
            .where(
                Assignment.class_offering_id == class_offering_id,
                Submission.candidate_id.in_(visible),
            )
            .order_by(Submission.updated_at.desc(), Submission.id)
            .limit(limit + 1)
        )
    ).all()
    for submission, assignment in submission_rows:
        items.append(
            ClassActivityItem(
                source_type="ASSIGNMENT_SUBMISSION",
                source_id=submission.id,
                source_parent_id=assignment.id,
                person_id=submission.candidate_id,
                class_offering_id=class_offering_id,
                capability_version_id=assignment.capability_version_id,
                occurred_at=submission.updated_at,
                state=submission.status,
            )
        )

    feedback_rows = (
        await db.execute(
            select(InstructorFeedback, Submission, Assignment)
            .join(Submission, InstructorFeedback.submission_id == Submission.id)
            .join(Assignment, Submission.assignment_id == Assignment.id)
            .where(
                Assignment.class_offering_id == class_offering_id,
                Submission.candidate_id.in_(visible),
            )
            .order_by(InstructorFeedback.created_at.desc(), InstructorFeedback.id)
            .limit(limit + 1)
        )
    ).all()
    for feedback, submission, assignment in feedback_rows:
        items.append(
            ClassActivityItem(
                source_type="INSTRUCTOR_FEEDBACK",
                source_id=feedback.id,
                source_parent_id=submission.id,
                person_id=submission.candidate_id,
                class_offering_id=class_offering_id,
                capability_version_id=assignment.capability_version_id,
                occurred_at=feedback.created_at,
            )
        )

    practice_rows = (
        await db.execute(
            select(PracticeAttempt, LearningUnit)
            .join(LearningUnit, PracticeAttempt.learning_unit_id == LearningUnit.id)
            .where(
                LearningUnit.class_offering_id == class_offering_id,
                PracticeAttempt.candidate_id.in_(visible),
            )
            .order_by(PracticeAttempt.updated_at.desc(), PracticeAttempt.id)
            .limit(limit + 1)
        )
    ).all()
    for attempt, unit in practice_rows:
        items.append(
            ClassActivityItem(
                source_type="PRACTICE_ATTEMPT",
                source_id=attempt.id,
                source_parent_id=unit.id,
                person_id=attempt.candidate_id,
                class_offering_id=class_offering_id,
                capability_version_id=unit.capability_version_id,
                occurred_at=attempt.updated_at,
                state=attempt.status,
            )
        )

    practice_feedback_rows = (
        await db.execute(
            select(PracticeFeedback, PracticeAttempt, LearningUnit)
            .join(
                PracticeAttempt,
                PracticeFeedback.practice_attempt_id == PracticeAttempt.id,
            )
            .join(LearningUnit, PracticeAttempt.learning_unit_id == LearningUnit.id)
            .where(
                LearningUnit.class_offering_id == class_offering_id,
                PracticeAttempt.candidate_id.in_(visible),
            )
            .order_by(PracticeFeedback.created_at.desc(), PracticeFeedback.id)
            .limit(limit + 1)
        )
    ).all()
    for feedback, attempt, unit in practice_feedback_rows:
        items.append(
            ClassActivityItem(
                source_type="PRACTICE_FEEDBACK",
                source_id=feedback.id,
                source_parent_id=attempt.id,
                person_id=attempt.candidate_id,
                class_offering_id=class_offering_id,
                capability_version_id=unit.capability_version_id,
                occurred_at=feedback.created_at,
            )
        )

    attendance_rows = (
        await db.execute(
            select(AttendanceRecord, Session)
            .join(Session, AttendanceRecord.session_id == Session.id)
            .where(
                Session.class_offering_id == class_offering_id,
                AttendanceRecord.organization_context_id
                == actor.organization_context_id,
                AttendanceRecord.person_id.in_(visible),
            )
            .order_by(AttendanceRecord.updated_at.desc(), AttendanceRecord.id)
            .limit(limit + 1)
        )
    ).all()
    for record, class_session in attendance_rows:
        items.append(
            ClassActivityItem(
                source_type="ATTENDANCE_RECORD",
                source_id=record.id,
                source_parent_id=class_session.id,
                person_id=record.person_id,
                class_offering_id=class_offering_id,
                session_id=class_session.id,
                occurred_at=record.updated_at,
                state=record.status,
            )
        )

    # No Mission-to-ClassOffering authoritative link exists yet. Do not use
    # shared CapabilityVersion or candidate identity to guess class ownership.
    # No raw response_text, feedback_text, formal Evidence or AI data is exposed.
    items.sort(
        key=lambda item: (item.occurred_at, item.source_type, str(item.source_id)),
        reverse=True,
    )
    return ClassActivityResponse(
        class_offering_id=class_offering_id,
        items=items[:limit],
        is_truncated=len(items) > limit,
    )
