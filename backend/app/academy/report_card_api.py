"""Qualitative class report-card read model; educational observations are not formal proof."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends
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
from app.curriculum.models import CapabilityVersion
from app.db import get_session
from app.errors import AppError
from app.flag_profile.public_reader import read_candidate_safe_reviewed_claims
from app.identity.auth import ActorContext, get_actor
from app.learning.state_reader import derive_learning_state
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


class ReportCardAttendance(BaseModel):
    session_id: UUID
    title: str
    starts_at: datetime
    status: Literal["PRESENT", "ABSENT", "NOT_RECORDED"]
    attendance_record_id: UUID | None


class ReportCardLearningSource(BaseModel):
    source_type: Literal["LEARNING_UNIT", "ASSIGNMENT", "PRACTICE_ATTEMPT"]
    source_id: UUID
    parent_id: UUID | None = None
    title: str | None = None
    state: str | None = None
    state_source_id: UUID | None = None
    observed_at: datetime | None = None


class ReportCardFeedbackSource(BaseModel):
    source_type: Literal["INSTRUCTOR_FEEDBACK", "PRACTICE_FEEDBACK"]
    source_id: UUID
    parent_id: UUID
    feedback_text: str
    created_at: datetime


class ReportCardReviewedClaim(BaseModel):
    claim_id: UUID
    claim_version: int
    capability_definition_id: UUID
    claim_state: Literal["UNPROVEN", "EMERGING", "DEMONSTRATED", "PROVEN"]
    level: str
    reviewed_at: datetime


class QualitativeSubjectReportCard(BaseModel):
    capability_version_id: UUID
    capability_name: str | None
    capability_version_number: int | None
    learning_state: str | None = None
    proof_state: str | None = None
    next_learning_focus: str | None = None
    reviewed_claim: ReportCardReviewedClaim | None = None
    learning_sources: list[ReportCardLearningSource]
    feedback_sources: list[ReportCardFeedbackSource]


class QualitativeClassReportCard(BaseModel):
    class_offering_id: UUID
    cohort_id: UUID
    person_id: UUID
    attendance_scope: Literal["CLASS_OFFERING"] = "CLASS_OFFERING"
    attendance: list[ReportCardAttendance]
    subjects: list[QualitativeSubjectReportCard]


async def _authorized_report_card_context(
    db: AsyncSession,
    *,
    actor: ActorContext,
    class_offering_id: UUID,
    person_id: UUID,
) -> tuple[ClassOffering, Cohort]:
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

    membership = (
        await db.execute(
            select(CohortMembership.id).where(
                CohortMembership.cohort_id == cohort.id,
                CohortMembership.person_id == person_id,
                CohortMembership.member_type == "CANDIDATE",
            )
        )
    ).scalar_one_or_none()
    if membership is None:
        raise AppError("CLASS_NOT_FOUND", "Class not found.", status_code=404)

    if "ACADEMY_ADMIN" in actor.roles:
        return offering, cohort
    if "INSTRUCTOR" in actor.roles:
        assignment = (
            await db.execute(
                select(InstructorAssignment.id).where(
                    InstructorAssignment.class_offering_id == offering.id,
                    InstructorAssignment.person_id == actor.person_id,
                )
            )
        ).scalar_one_or_none()
        if assignment is not None:
            return offering, cohort
    if "CANDIDATE" in actor.roles and actor.person_id == person_id:
        return offering, cohort
    # ASSESSOR is not implicitly scoped to this class.
    raise AppError("CLASS_NOT_FOUND", "Class not found.", status_code=404)


@router.get(
    "/class-offerings/{class_offering_id}/report-cards/{person_id}",
    response_model=QualitativeClassReportCard,
)
async def qualitative_class_report_card(
    class_offering_id: UUID,
    person_id: UUID,
    actor: Annotated[ActorContext, Depends(get_actor)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> QualitativeClassReportCard:
    offering, cohort = await _authorized_report_card_context(
        db,
        actor=actor,
        class_offering_id=class_offering_id,
        person_id=person_id,
    )

    units = list(
        (
            await db.execute(
                select(LearningUnit)
                .where(LearningUnit.class_offering_id == offering.id)
                .order_by(LearningUnit.position, LearningUnit.id)
            )
        ).scalars().all()
    )
    assignments = list(
        (
            await db.execute(
                select(Assignment)
                .where(Assignment.class_offering_id == offering.id)
                .order_by(Assignment.created_at, Assignment.id)
            )
        ).scalars().all()
    )
    capability_ids = {
        offering.primary_capability_version_id,
        *(unit.capability_version_id for unit in units),
        *(assignment.capability_version_id for assignment in assignments),
    }
    capability_versions = {
        item.id: item
        for item in (
            await db.execute(
                select(CapabilityVersion).where(CapabilityVersion.id.in_(capability_ids))
            )
        ).scalars().all()
    }

    sessions = list(
        (
            await db.execute(
                select(Session)
                .where(Session.class_offering_id == offering.id)
                .order_by(Session.starts_at, Session.id)
            )
        ).scalars().all()
    )
    attendance_records = (
        list(
            (
                await db.execute(
                    select(AttendanceRecord).where(
                        AttendanceRecord.organization_context_id
                        == actor.organization_context_id,
                        AttendanceRecord.session_id.in_([item.id for item in sessions]),
                        AttendanceRecord.person_id == person_id,
                    )
                )
            ).scalars().all()
        )
        if sessions
        else []
    )
    attendance_by_session = {item.session_id: item for item in attendance_records}

    unit_ids = [item.id for item in units]
    progresses = (
        list(
            (
                await db.execute(
                    select(LearningUnitProgress).where(
                        LearningUnitProgress.learning_unit_id.in_(unit_ids),
                        LearningUnitProgress.candidate_id == person_id,
                    )
                )
            ).scalars().all()
        )
        if unit_ids
        else []
    )
    progress_by_unit = {item.learning_unit_id: item for item in progresses}
    attempts = (
        list(
            (
                await db.execute(
                    select(PracticeAttempt).where(
                        PracticeAttempt.learning_unit_id.in_(unit_ids),
                        PracticeAttempt.candidate_id == person_id,
                    )
                )
            ).scalars().all()
        )
        if unit_ids
        else []
    )
    attempts.sort(key=lambda item: (item.submitted_at, str(item.id)))

    assignment_ids = [item.id for item in assignments]
    submissions = (
        list(
            (
                await db.execute(
                    select(Submission).where(
                        Submission.assignment_id.in_(assignment_ids),
                        Submission.candidate_id == person_id,
                    )
                )
            ).scalars().all()
        )
        if assignment_ids
        else []
    )
    submissions_by_assignment = {item.assignment_id: item for item in submissions}

    feedback = (
        list(
            (
                await db.execute(
                    select(InstructorFeedback).where(
                        InstructorFeedback.submission_id.in_(
                            [item.id for item in submissions]
                        )
                    )
                )
            ).scalars().all()
        )
        if submissions
        else []
    )
    practice_feedback = (
        list(
            (
                await db.execute(
                    select(PracticeFeedback).where(
                        PracticeFeedback.practice_attempt_id.in_(
                            [item.id for item in attempts]
                        )
                    )
                )
            ).scalars().all()
        )
        if attempts
        else []
    )
    submission_capability = {
        item.id: next(
            assignment.capability_version_id
            for assignment in assignments
            if assignment.id == item.assignment_id
        )
        for item in submissions
    }
    attempt_capability = {
        item.id: next(
            unit.capability_version_id
            for unit in units
            if unit.id == item.learning_unit_id
        )
        for item in attempts
    }

    # The public Flag Profile reader is the only source of reviewed claims.
    # CapabilityVersion ID and Capability definition ID are different identities;
    # never join a reviewed claim by the version ID alone.
    reviewed_claims = await read_candidate_safe_reviewed_claims(
        db,
        organization_context_id=actor.organization_context_id,
        subject_person_id=person_id,
        track_code=cohort.track_code,
        capability_definition_ids={
            version.definition_id for version in capability_versions.values()
        },
    )

    subjects: list[QualitativeSubjectReportCard] = []
    for capability_id in sorted(capability_ids, key=str):
        version = capability_versions.get(capability_id)
        reviewed = (
            None
            if version is None
            else reviewed_claims.get(version.definition_id)
        )
        learning_sources: list[ReportCardLearningSource] = []
        feedback_sources: list[ReportCardFeedbackSource] = []
        for unit in units:
            if unit.capability_version_id != capability_id:
                continue
            progress = progress_by_unit.get(unit.id)
            learning_sources.append(
                ReportCardLearningSource(
                    source_type="LEARNING_UNIT",
                    source_id=unit.id,
                    title=unit.title,
                    state=None if progress is None else progress.state,
                    state_source_id=None if progress is None else progress.id,
                    observed_at=None if progress is None else progress.updated_at,
                )
            )
        for assignment in assignments:
            if assignment.capability_version_id != capability_id:
                continue
            submission = submissions_by_assignment.get(assignment.id)
            learning_sources.append(
                ReportCardLearningSource(
                    source_type="ASSIGNMENT",
                    source_id=assignment.id,
                    title=assignment.title,
                    state=None if submission is None else submission.status,
                    state_source_id=None if submission is None else submission.id,
                    observed_at=None if submission is None else submission.updated_at,
                )
            )
        for attempt in attempts:
            if attempt_capability[attempt.id] != capability_id:
                continue
            learning_sources.append(
                ReportCardLearningSource(
                    source_type="PRACTICE_ATTEMPT",
                    source_id=attempt.id,
                    parent_id=attempt.learning_unit_id,
                    state=attempt.status,
                    state_source_id=attempt.id,
                    observed_at=attempt.updated_at,
                )
            )
        for item in feedback:
            if submission_capability[item.submission_id] != capability_id:
                continue
            feedback_sources.append(
                ReportCardFeedbackSource(
                    source_type="INSTRUCTOR_FEEDBACK",
                    source_id=item.id,
                    parent_id=item.submission_id,
                    feedback_text=item.feedback_text,
                    created_at=item.created_at,
                )
            )
        for item in practice_feedback:
            if attempt_capability[item.practice_attempt_id] != capability_id:
                continue
            feedback_sources.append(
                ReportCardFeedbackSource(
                    source_type="PRACTICE_FEEDBACK",
                    source_id=item.id,
                    parent_id=item.practice_attempt_id,
                    feedback_text=item.feedback_text,
                    created_at=item.created_at,
                )
            )
        feedback_sources.sort(key=lambda item: (item.created_at, str(item.source_id)))
        subjects.append(
            QualitativeSubjectReportCard(
                capability_version_id=capability_id,
                capability_name=None if version is None else version.name,
                capability_version_number=(
                    None if version is None else version.version_number
                ),
                # Learning state reuses the Learning-owned CandidateHome rule.
                # This reports education only, never formal proof.
                learning_state=derive_learning_state(
                    unit_progress_states=[
                        progress_by_unit[unit.id].state
                        if unit.id in progress_by_unit
                        else None
                        for unit in units
                        if unit.capability_version_id == capability_id
                        and unit.status == "ACTIVE"
                    ],
                    assignment_submitted=[
                        assignment.id in submissions_by_assignment
                        for assignment in assignments
                        if assignment.capability_version_id == capability_id
                        and assignment.status == "ACTIVE"
                    ],
                ),
                proof_state=None,
                next_learning_focus=None,
                reviewed_claim=(
                    None
                    if reviewed is None
                    else ReportCardReviewedClaim(
                        claim_id=reviewed.claim_id,
                        claim_version=reviewed.claim_version,
                        capability_definition_id=reviewed.capability_id,
                        claim_state=reviewed.claim_state,
                        level=reviewed.level,
                        reviewed_at=reviewed.reviewed_at,
                    )
                ),
                learning_sources=learning_sources,
                feedback_sources=feedback_sources,
            )
        )

    def observed_attendance_status(
        record: AttendanceRecord | None,
    ) -> Literal["PRESENT", "ABSENT", "NOT_RECORDED"]:
        if record is None:
            return "NOT_RECORDED"
        if record.status == "PRESENT":
            return "PRESENT"
        if record.status == "ABSENT":
            return "ABSENT"
        raise AppError(
            "ATTENDANCE_STATUS_INVALID",
            "Invalid recorded attendance status.",
            status_code=409,
        )

    return QualitativeClassReportCard(
        class_offering_id=offering.id,
        cohort_id=cohort.id,
        person_id=person_id,
        attendance=[
            ReportCardAttendance(
                session_id=session.id,
                title=session.title,
                starts_at=session.starts_at,
                status=observed_attendance_status(
                    attendance_by_session.get(session.id)
                ),
                attendance_record_id=(
                    None
                    if session.id not in attendance_by_session
                    else attendance_by_session[session.id].id
                ),
            )
            for session in sessions
        ],
        subjects=subjects,
    )
