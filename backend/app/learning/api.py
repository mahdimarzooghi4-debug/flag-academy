from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.academy.models import ClassOffering, Cohort, CohortMembership, InstructorAssignment
from app.db import get_session
from app.errors import AppError
from app.identity.auth import ActorContext, require_role
from app.learning.models import (
    Assignment,
    InstructorFeedback,
    LearningUnit,
    LearningUnitProgress,
    PracticeAttempt,
    PracticeFeedback,
    Submission,
)
from app.platform.events import new_event, record_event

router = APIRouter(prefix="/api/v1", tags=["learning"])


class LearningUnitResponse(BaseModel):
    id: UUID
    class_offering_id: UUID
    capability_version_id: UUID
    unit_type: str
    phase: str
    practice_kind: str | None
    title: str
    body: str
    resource_url: str | None
    position: int
    status: str


class AssignmentResponse(BaseModel):
    id: UUID
    version: int
    class_offering_id: UUID
    capability_version_id: UUID
    title: str
    instructions: str
    due_at: datetime | None
    status: str


class ClassLearningResponse(BaseModel):
    class_offering_id: UUID
    learning_units: list[LearningUnitResponse]
    assignments: list[AssignmentResponse]


class LearningUnitProgressResponse(BaseModel):
    id: UUID
    learning_unit_id: UUID
    candidate_id: UUID
    state: str
    started_at: datetime | None
    completed_at: datetime | None


class PracticeAttemptCreate(BaseModel):
    response_text: str = Field(min_length=1, max_length=20_000)


class PracticeAttemptResponse(BaseModel):
    id: UUID
    learning_unit_id: UUID
    candidate_id: UUID
    attempt_number: int
    replay_of_attempt_id: UUID | None
    status: str
    submitted_at: datetime


class PracticeFeedbackCreate(BaseModel):
    feedback_text: str = Field(min_length=1, max_length=20_000)


class PracticeFeedbackResponse(BaseModel):
    id: UUID
    practice_attempt_id: UUID
    instructor_id: UUID
    feedback_text: str
    created_at: datetime


class SubmissionCreate(BaseModel):
    content_text: str = Field(min_length=1, max_length=20_000)


class SubmissionResponse(BaseModel):
    id: UUID
    assignment_id: UUID
    candidate_id: UUID
    status: str
    submitted_at: datetime


class FeedbackCreate(BaseModel):
    feedback_text: str = Field(min_length=1, max_length=20_000)


class FeedbackResponse(BaseModel):
    id: UUID
    submission_id: UUID
    instructor_id: UUID
    feedback_text: str
    created_at: datetime


async def _load_class_context(
    db: AsyncSession,
    *,
    class_offering_id: UUID,
    organization_context_id: UUID,
) -> tuple[ClassOffering, Cohort]:
    row = (
        await db.execute(
            select(ClassOffering, Cohort)
            .join(Cohort, ClassOffering.cohort_id == Cohort.id)
            .where(
                ClassOffering.id == class_offering_id,
                Cohort.organization_context_id == organization_context_id,
            )
        )
    ).first()
    if row is None:
        raise AppError("CLASS_NOT_FOUND", "Class not found.", status_code=404)
    return row[0], row[1]


async def _require_candidate_class_access(
    db: AsyncSession,
    *,
    actor: ActorContext,
    class_offering_id: UUID,
) -> tuple[ClassOffering, Cohort]:
    class_offering, cohort = await _load_class_context(
        db,
        class_offering_id=class_offering_id,
        organization_context_id=actor.organization_context_id,
    )
    membership = (
        await db.execute(
            select(CohortMembership.id).where(
                CohortMembership.cohort_id == cohort.id,
                CohortMembership.person_id == actor.person_id,
                CohortMembership.member_type == "CANDIDATE",
            )
        )
    ).scalar_one_or_none()
    if membership is None:
        raise AppError("CLASS_NOT_FOUND", "Class not found.", status_code=404)
    return class_offering, cohort


async def _require_instructor_class_access(
    db: AsyncSession,
    *,
    actor: ActorContext,
    class_offering_id: UUID,
) -> tuple[ClassOffering, Cohort]:
    class_offering, cohort = await _load_class_context(
        db,
        class_offering_id=class_offering_id,
        organization_context_id=actor.organization_context_id,
    )
    assignment = (
        await db.execute(
            select(InstructorAssignment.id).where(
                InstructorAssignment.class_offering_id == class_offering.id,
                InstructorAssignment.person_id == actor.person_id,
            )
        )
    ).scalar_one_or_none()
    if assignment is None:
        raise AppError("CLASS_NOT_FOUND", "Class not found.", status_code=404)
    return class_offering, cohort


@router.get("/classes/{class_offering_id}/learning", response_model=ClassLearningResponse)
async def class_learning(
    class_offering_id: UUID,
    actor: Annotated[ActorContext, Depends(require_role("CANDIDATE", "INSTRUCTOR"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> ClassLearningResponse:
    if "CANDIDATE" in actor.roles:
        await _require_candidate_class_access(
            db,
            actor=actor,
            class_offering_id=class_offering_id,
        )
    else:
        await _require_instructor_class_access(
            db,
            actor=actor,
            class_offering_id=class_offering_id,
        )

    units = (
        await db.execute(
            select(LearningUnit)
            .where(
                LearningUnit.class_offering_id == class_offering_id,
                LearningUnit.status == "ACTIVE",
            )
            .order_by(LearningUnit.position)
        )
    ).scalars().all()
    assignments = (
        await db.execute(
            select(Assignment)
            .where(
                Assignment.class_offering_id == class_offering_id,
                Assignment.status == "ACTIVE",
            )
            .order_by(Assignment.due_at)
        )
    ).scalars().all()

    return ClassLearningResponse(
        class_offering_id=class_offering_id,
        learning_units=[
            LearningUnitResponse(
                id=item.id,
                class_offering_id=item.class_offering_id,
                capability_version_id=item.capability_version_id,
                unit_type=item.unit_type,
                phase=item.phase,
                practice_kind=item.practice_kind,
                title=item.title,
                body=item.body,
                resource_url=item.resource_url,
                position=item.position,
                status=item.status,
            )
            for item in units
        ],
        assignments=[
            AssignmentResponse(
                id=item.id,
                version=item.version,
                class_offering_id=item.class_offering_id,
                capability_version_id=item.capability_version_id,
                title=item.title,
                instructions=item.instructions,
                due_at=item.due_at,
                status=item.status,
            )
            for item in assignments
        ],
    )


async def _load_candidate_learning_unit(
    db: AsyncSession,
    *,
    actor: ActorContext,
    learning_unit_id: UUID,
) -> tuple[LearningUnit, Cohort]:
    unit = await db.get(LearningUnit, learning_unit_id)
    if unit is None or unit.status != "ACTIVE":
        raise AppError(
            "LEARNING_UNIT_NOT_FOUND",
            "Learning unit not found.",
            status_code=404,
        )
    _, cohort = await _require_candidate_class_access(
        db,
        actor=actor,
        class_offering_id=unit.class_offering_id,
    )
    return unit, cohort


@router.post(
    "/learning-units/{learning_unit_id}/start",
    response_model=LearningUnitProgressResponse,
)
async def start_learning_unit(
    learning_unit_id: UUID,
    actor: Annotated[ActorContext, Depends(require_role("CANDIDATE"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> LearningUnitProgressResponse:
    unit, cohort = await _load_candidate_learning_unit(
        db,
        actor=actor,
        learning_unit_id=learning_unit_id,
    )
    progress = (
        await db.execute(
            select(LearningUnitProgress).where(
                LearningUnitProgress.learning_unit_id == unit.id,
                LearningUnitProgress.candidate_id == actor.person_id,
            )
        )
    ).scalar_one_or_none()

    now = datetime.now(UTC)
    if progress is None:
        progress = LearningUnitProgress(
            id=uuid4(),
            learning_unit_id=unit.id,
            candidate_id=actor.person_id,
            state="IN_PROGRESS",
            started_at=now,
            completed_at=None,
            updated_at=now,
        )
        db.add(progress)
        await db.flush()
        record_event(
            db,
            new_event(
                event_type="learning.unit_started.v1",
                aggregate_type="LearningUnitProgress",
                aggregate_id=progress.id,
                aggregate_version=progress.version,
                actor={"type": "PERSON", "id": str(actor.person_id)},
                organization_context_id=actor.organization_context_id,
                data_classification="INTERNAL",
                payload={
                    "progress_id": str(progress.id),
                    "learning_unit_id": str(unit.id),
                    "candidate_id": str(actor.person_id),
                    "class_offering_id": str(unit.class_offering_id),
                    "cohort_id": str(cohort.id),
                },
                trace_id=actor.trace_id,
            ),
        )
        await db.commit()

    return LearningUnitProgressResponse(
        id=progress.id,
        learning_unit_id=progress.learning_unit_id,
        candidate_id=progress.candidate_id,
        state=progress.state,
        started_at=progress.started_at,
        completed_at=progress.completed_at,
    )


@router.post(
    "/learning-units/{learning_unit_id}/complete",
    response_model=LearningUnitProgressResponse,
)
async def complete_learning_unit(
    learning_unit_id: UUID,
    actor: Annotated[ActorContext, Depends(require_role("CANDIDATE"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> LearningUnitProgressResponse:
    unit, cohort = await _load_candidate_learning_unit(
        db,
        actor=actor,
        learning_unit_id=learning_unit_id,
    )
    progress = (
        await db.execute(
            select(LearningUnitProgress).where(
                LearningUnitProgress.learning_unit_id == unit.id,
                LearningUnitProgress.candidate_id == actor.person_id,
            )
        )
    ).scalar_one_or_none()
    if progress is None:
        raise AppError(
            "LEARNING_UNIT_NOT_STARTED",
            "Learning unit must be started before completion.",
            status_code=409,
        )

    if progress.state != "COMPLETED":
        now = datetime.now(UTC)
        progress.state = "COMPLETED"
        progress.completed_at = now
        progress.updated_at = now
        progress.version += 1
        record_event(
            db,
            new_event(
                event_type="learning.unit_completed.v1",
                aggregate_type="LearningUnitProgress",
                aggregate_id=progress.id,
                aggregate_version=progress.version,
                actor={"type": "PERSON", "id": str(actor.person_id)},
                organization_context_id=actor.organization_context_id,
                data_classification="INTERNAL",
                payload={
                    "progress_id": str(progress.id),
                    "learning_unit_id": str(unit.id),
                    "candidate_id": str(actor.person_id),
                    "class_offering_id": str(unit.class_offering_id),
                    "cohort_id": str(cohort.id),
                },
                trace_id=actor.trace_id,
            ),
        )
        await db.commit()

    return LearningUnitProgressResponse(
        id=progress.id,
        learning_unit_id=progress.learning_unit_id,
        candidate_id=progress.candidate_id,
        state=progress.state,
        started_at=progress.started_at,
        completed_at=progress.completed_at,
    )


@router.post(
    "/practice-units/{learning_unit_id}/attempts",
    response_model=PracticeAttemptResponse,
    status_code=201,
)
async def submit_practice_attempt(
    learning_unit_id: UUID,
    body: PracticeAttemptCreate,
    actor: Annotated[ActorContext, Depends(require_role("CANDIDATE"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> PracticeAttemptResponse:
    unit, cohort = await _load_candidate_learning_unit(
        db,
        actor=actor,
        learning_unit_id=learning_unit_id,
    )
    if unit.phase != "PRACTICE":
        raise AppError(
            "PRACTICE_UNIT_REQUIRED",
            "Learning unit is not a practice activity.",
            status_code=422,
        )

    latest_attempt = (
        await db.execute(
            select(PracticeAttempt)
            .where(
                PracticeAttempt.learning_unit_id == unit.id,
                PracticeAttempt.candidate_id == actor.person_id,
            )
            .order_by(PracticeAttempt.attempt_number.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if latest_attempt is not None and latest_attempt.status != "FEEDBACK_PROVIDED":
        raise AppError(
            "PRACTICE_REPLAY_REQUIRES_FEEDBACK",
            "The latest practice attempt must receive feedback before replay.",
            status_code=409,
            details={"practice_attempt_id": str(latest_attempt.id)},
        )

    now = datetime.now(UTC)
    progress = (
        await db.execute(
            select(LearningUnitProgress).where(
                LearningUnitProgress.learning_unit_id == unit.id,
                LearningUnitProgress.candidate_id == actor.person_id,
            )
        )
    ).scalar_one_or_none()
    if progress is None:
        progress = LearningUnitProgress(
            id=uuid4(),
            learning_unit_id=unit.id,
            candidate_id=actor.person_id,
            state="COMPLETED",
            started_at=now,
            completed_at=now,
            updated_at=now,
        )
        db.add(progress)
    else:
        progress.state = "COMPLETED"
        progress.completed_at = now
        progress.updated_at = now
        progress.version += 1

    attempt = PracticeAttempt(
        id=uuid4(),
        learning_unit_id=unit.id,
        candidate_id=actor.person_id,
        attempt_number=(
            1 if latest_attempt is None else latest_attempt.attempt_number + 1
        ),
        replay_of_attempt_id=latest_attempt.id if latest_attempt is not None else None,
        response_text=body.response_text.strip(),
        status="SUBMITTED",
        submitted_at=now,
        updated_at=now,
    )
    db.add(attempt)
    await db.flush()

    record_event(
        db,
        new_event(
            event_type="learning.practice_attempt_submitted.v1",
            aggregate_type="PracticeAttempt",
            aggregate_id=attempt.id,
            aggregate_version=attempt.version,
            actor={"type": "PERSON", "id": str(actor.person_id)},
            organization_context_id=actor.organization_context_id,
            data_classification="INTERNAL",
            payload={
                "practice_attempt_id": str(attempt.id),
                "learning_unit_id": str(unit.id),
                "candidate_id": str(actor.person_id),
                "attempt_number": attempt.attempt_number,
                "replay_of_attempt_id": (
                    str(attempt.replay_of_attempt_id)
                    if attempt.replay_of_attempt_id is not None
                    else None
                ),
                "class_offering_id": str(unit.class_offering_id),
                "cohort_id": str(cohort.id),
            },
            trace_id=actor.trace_id,
        ),
    )
    await db.commit()

    return PracticeAttemptResponse(
        id=attempt.id,
        learning_unit_id=attempt.learning_unit_id,
        candidate_id=attempt.candidate_id,
        attempt_number=attempt.attempt_number,
        replay_of_attempt_id=attempt.replay_of_attempt_id,
        status=attempt.status,
        submitted_at=attempt.submitted_at,
    )


@router.post(
    "/practice-attempts/{practice_attempt_id}/feedback",
    response_model=PracticeFeedbackResponse,
    status_code=201,
)
async def record_practice_feedback(
    practice_attempt_id: UUID,
    body: PracticeFeedbackCreate,
    actor: Annotated[ActorContext, Depends(require_role("INSTRUCTOR"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> PracticeFeedbackResponse:
    attempt = await db.get(PracticeAttempt, practice_attempt_id)
    if attempt is None:
        raise AppError(
            "PRACTICE_ATTEMPT_NOT_FOUND",
            "Practice attempt not found.",
            status_code=404,
        )
    unit = await db.get(LearningUnit, attempt.learning_unit_id)
    if unit is None:
        raise AppError(
            "PRACTICE_ATTEMPT_NOT_FOUND",
            "Practice attempt not found.",
            status_code=404,
        )

    _, cohort = await _require_instructor_class_access(
        db,
        actor=actor,
        class_offering_id=unit.class_offering_id,
    )

    now = datetime.now(UTC)
    feedback = PracticeFeedback(
        id=uuid4(),
        practice_attempt_id=attempt.id,
        instructor_id=actor.person_id,
        feedback_text=body.feedback_text.strip(),
        created_at=now,
    )
    db.add(feedback)
    attempt.status = "FEEDBACK_PROVIDED"
    attempt.version += 1
    attempt.updated_at = now

    record_event(
        db,
        new_event(
            event_type="learning.practice_feedback_recorded.v1",
            aggregate_type="PracticeAttempt",
            aggregate_id=attempt.id,
            aggregate_version=attempt.version,
            actor={"type": "PERSON", "id": str(actor.person_id)},
            organization_context_id=actor.organization_context_id,
            data_classification="INTERNAL",
            payload={
                "practice_attempt_id": str(attempt.id),
                "learning_unit_id": str(unit.id),
                "candidate_id": str(attempt.candidate_id),
                "class_offering_id": str(unit.class_offering_id),
                "cohort_id": str(cohort.id),
                "feedback_id": str(feedback.id),
            },
            trace_id=actor.trace_id,
        ),
    )
    await db.commit()

    return PracticeFeedbackResponse(
        id=feedback.id,
        practice_attempt_id=feedback.practice_attempt_id,
        instructor_id=feedback.instructor_id,
        feedback_text=feedback.feedback_text,
        created_at=feedback.created_at,
    )


@router.post(
    "/assignments/{assignment_id}/submissions",
    response_model=SubmissionResponse,
    status_code=201,
)
async def submit_assignment(
    assignment_id: UUID,
    body: SubmissionCreate,
    actor: Annotated[ActorContext, Depends(require_role("CANDIDATE"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> SubmissionResponse:
    assignment = await db.get(Assignment, assignment_id)
    if assignment is None or assignment.status != "ACTIVE":
        raise AppError("ASSIGNMENT_NOT_FOUND", "Assignment not found.", status_code=404)

    _, cohort = await _require_candidate_class_access(
        db,
        actor=actor,
        class_offering_id=assignment.class_offering_id,
    )

    existing = (
        await db.execute(
            select(Submission).where(
                Submission.assignment_id == assignment.id,
                Submission.candidate_id == actor.person_id,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise AppError(
            "SUBMISSION_ALREADY_EXISTS",
            "This assignment already has a submission.",
            status_code=409,
            details={"submission_id": str(existing.id)},
        )

    now = datetime.now(UTC)
    submission = Submission(
        id=uuid4(),
        assignment_id=assignment.id,
        candidate_id=actor.person_id,
        content_text=body.content_text.strip(),
        status="SUBMITTED",
        submitted_at=now,
        updated_at=now,
    )
    db.add(submission)
    await db.flush()

    record_event(
        db,
        new_event(
            event_type="learning.submission_submitted.v1",
            aggregate_type="Submission",
            aggregate_id=submission.id,
            aggregate_version=submission.version,
            actor={"type": "PERSON", "id": str(actor.person_id)},
            organization_context_id=actor.organization_context_id,
            data_classification="INTERNAL",
            payload={
                "submission_id": str(submission.id),
                "assignment_id": str(assignment.id),
                "candidate_id": str(actor.person_id),
                "class_offering_id": str(assignment.class_offering_id),
                "cohort_id": str(cohort.id),
            },
            trace_id=actor.trace_id,
        ),
    )
    await db.commit()

    return SubmissionResponse(
        id=submission.id,
        assignment_id=submission.assignment_id,
        candidate_id=submission.candidate_id,
        status=submission.status,
        submitted_at=submission.submitted_at,
    )


@router.post(
    "/submissions/{submission_id}/feedback",
    response_model=FeedbackResponse,
    status_code=201,
)
async def record_feedback(
    submission_id: UUID,
    body: FeedbackCreate,
    actor: Annotated[ActorContext, Depends(require_role("INSTRUCTOR"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> FeedbackResponse:
    submission = await db.get(Submission, submission_id)
    if submission is None:
        raise AppError("SUBMISSION_NOT_FOUND", "Submission not found.", status_code=404)
    assignment = await db.get(Assignment, submission.assignment_id)
    if assignment is None:
        raise AppError("SUBMISSION_NOT_FOUND", "Submission not found.", status_code=404)

    _, cohort = await _require_instructor_class_access(
        db,
        actor=actor,
        class_offering_id=assignment.class_offering_id,
    )

    now = datetime.now(UTC)
    feedback = InstructorFeedback(
        id=uuid4(),
        submission_id=submission.id,
        instructor_id=actor.person_id,
        feedback_text=body.feedback_text.strip(),
        created_at=now,
    )
    db.add(feedback)
    submission.status = "FEEDBACK_PROVIDED"
    submission.version += 1
    submission.updated_at = now

    record_event(
        db,
        new_event(
            event_type="learning.instructor_feedback_recorded.v1",
            aggregate_type="Submission",
            aggregate_id=submission.id,
            aggregate_version=submission.version,
            actor={"type": "PERSON", "id": str(actor.person_id)},
            organization_context_id=actor.organization_context_id,
            data_classification="INTERNAL",
            payload={
                "submission_id": str(submission.id),
                "assignment_id": str(assignment.id),
                "candidate_id": str(submission.candidate_id),
                "class_offering_id": str(assignment.class_offering_id),
                "cohort_id": str(cohort.id),
                "feedback_id": str(feedback.id),
            },
            trace_id=actor.trace_id,
        ),
    )
    await db.commit()

    return FeedbackResponse(
        id=feedback.id,
        submission_id=feedback.submission_id,
        instructor_id=feedback.instructor_id,
        feedback_text=feedback.feedback_text,
        created_at=feedback.created_at,
    )
