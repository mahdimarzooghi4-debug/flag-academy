"""Qualitative report-card provenance, missing-data, and authorization guards."""

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import cast
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.academy.report_card_api import qualitative_class_report_card
from app.errors import AppError
from app.identity.auth import ActorContext
from app.main import app

ORG = UUID(int=1001)
CLASS = UUID(int=1002)
COHORT = UUID(int=1003)
LEARNER = UUID(int=1004)
OTHER_LEARNER = UUID(int=1005)
INSTRUCTOR = UUID(int=1006)
CAPABILITY = UUID(int=1007)
UNIT = UUID(int=1008)
ASSIGNMENT = UUID(int=1009)
NOW = datetime(2026, 10, 8, 12, tzinfo=UTC)


class FakeResult:
    def __init__(self, rows: list):
        self.rows = rows

    def first(self):
        return self.rows[0] if self.rows else None

    def scalars(self):
        return self

    def all(self):
        return self.rows

    def scalar_one_or_none(self):
        assert len(self.rows) <= 1
        return self.rows[0] if self.rows else None


class FakeSession:
    def __init__(self, batches: list[list]):
        self.batches = batches
        self.queries: list = []

    async def execute(self, query):
        self.queries.append(query)
        assert self.batches, "Extra read not allowed"
        return FakeResult(self.batches.pop(0))


def actor(person: UUID, *roles: str) -> ActorContext:
    return ActorContext(
        actor_id=str(person),
        person_id=person,
        organization_context_id=ORG,
        roles=frozenset(roles),
    )


def context() -> list:
    return [(
        SimpleNamespace(
            id=CLASS,
            cohort_id=COHORT,
            primary_capability_version_id=CAPABILITY,
        ),
        SimpleNamespace(id=COHORT, track_code="FLAG_TRACK"),
    )]


def test_class_report_card_openapi_is_get_only_and_non_numeric() -> None:
    route = "/api/v1/class-offerings/{class_offering_id}/report-cards/{person_id}"
    paths = app.openapi()["paths"]
    assert set(paths[route]) == {"get"}
    schemas = app.openapi()["components"]["schemas"]
    subject_fields = schemas["QualitativeSubjectReportCard"]["properties"]
    assert {
        "capability_version_id",
        "capability_name",
        "capability_version_number",
        "learning_state",
        "proof_state",
        "next_learning_focus",
        "learning_sources",
        "feedback_sources",
    }.issubset(subject_fields)
    for forbidden in ("score", "gpa", "rank", "readiness", "percentage"):
        assert forbidden not in subject_fields


@pytest.mark.asyncio
async def test_candidate_qualitative_sources_and_missing_attendance_are_truthful() -> None:
    unit = SimpleNamespace(
        id=UNIT,
        title="Decision practice",
        position=1,
        capability_version_id=CAPABILITY,
        status="ACTIVE",
    )
    task = SimpleNamespace(
        id=ASSIGNMENT,
        title="Decision reflection",
        capability_version_id=CAPABILITY,
        created_at=NOW,
        status="ACTIVE",
    )
    version = SimpleNamespace(
        id=CAPABILITY, definition_id=UUID(int=2001), name="Decision Making", version_number=1
    )
    session_a = SimpleNamespace(
        id=UUID(int=1010), title="First meeting", starts_at=NOW
    )
    session_b = SimpleNamespace(
        id=UUID(int=1011), title="Second meeting", starts_at=NOW
    )
    attendance = SimpleNamespace(
        id=UUID(int=1012), session_id=session_a.id, status="PRESENT"
    )
    progress = SimpleNamespace(
        id=UUID(int=1013), learning_unit_id=UNIT,
        state="IN_PROGRESS", updated_at=NOW
    )
    attempt = SimpleNamespace(
        id=UUID(int=1014), learning_unit_id=UNIT,
        status="SUBMITTED", submitted_at=NOW, updated_at=NOW
    )
    submission = SimpleNamespace(
        id=UUID(int=1015), assignment_id=ASSIGNMENT,
        status="SUBMITTED", updated_at=NOW
    )
    teacher_feedback = SimpleNamespace(
        id=UUID(int=1016), submission_id=submission.id,
        feedback_text="Explain the reversibility assumption", created_at=NOW
    )
    practice_feedback = SimpleNamespace(
        id=UUID(int=1017), practice_attempt_id=attempt.id,
        feedback_text="Identify the missing evidence", created_at=NOW
    )
    db = FakeSession([
        context(),
        [UUID(int=2000)],
        [unit],
        [task],
        [version],
        [session_a, session_b],
        [attendance],
        [progress],
        [attempt],
        [submission],
        [teacher_feedback],
        [practice_feedback],
        [SimpleNamespace(
            id=UUID(int=3001), version=3, capability_id=UUID(int=2001),
            state="DEMONSTRATED", level="L2", reviewed_at=NOW,
        )],
    ])

    result = await qualitative_class_report_card(
        CLASS, LEARNER, actor(LEARNER, "CANDIDATE"), cast(AsyncSession, db)
    )

    assert result.person_id == LEARNER
    assert result.attendance_scope == "CLASS_OFFERING"
    assert [item.status for item in result.attendance] == [
        "PRESENT",
        "NOT_RECORDED",
    ]
    assert result.attendance[0].attendance_record_id == attendance.id
    assert result.attendance[1].attendance_record_id is None
    assert len(result.subjects) == 1
    subject = result.subjects[0]
    assert subject.capability_version_id == CAPABILITY
    assert subject.capability_name == "Decision Making"
    assert subject.learning_state == "IN_LEARNING"
    assert subject.proof_state is None
    assert subject.reviewed_claim is not None
    assert subject.reviewed_claim.claim_state == "DEMONSTRATED"
    assert subject.reviewed_claim.claim_id == UUID(int=3001)
    assert subject.reviewed_claim.claim_version == 3
    assert subject.reviewed_claim.level == "L2"
    assert subject.reviewed_claim.capability_definition_id == UUID(int=2001)
    assert subject.next_learning_focus is None
    assert [s.state for s in subject.learning_sources] == [
        "IN_PROGRESS",
        "SUBMITTED",
        "SUBMITTED",
    ]
    assert subject.learning_sources[0].state_source_id == progress.id
    assert subject.learning_sources[1].state_source_id == submission.id
    assert {f.source_id for f in subject.feedback_sources} == {
        teacher_feedback.id,
        practice_feedback.id,
    }
    assert all(s.capability_version_id is not None for s in result.subjects)
    assert not db.batches
    params = list(db.queries[-1].compile().params.values())
    assert ORG in params
    assert LEARNER in params
    assert "FLAG_TRACK" in params
    assert [UUID(int=2001)] in params
    # All person-specific reads follow successful membership/tenant authorization.
    assert ORG in db.queries[0].compile().params.values()
    assert LEARNER in db.queries[1].compile().params.values()
    assert LEARNER in db.queries[6].compile().params.values()
    assert LEARNER in db.queries[7].compile().params.values()
    assert LEARNER in db.queries[8].compile().params.values()
    assert LEARNER in db.queries[9].compile().params.values()


@pytest.mark.asyncio
async def test_missing_learning_and_capability_are_not_invented() -> None:
    db = FakeSession([
        context(), [UUID(int=2000)], [], [], [], [],
    ])
    result = await qualitative_class_report_card(
        CLASS, LEARNER, actor(LEARNER, "CANDIDATE"), cast(AsyncSession, db)
    )
    assert len(result.subjects) == 1
    assert result.subjects[0].capability_name is None
    assert result.subjects[0].learning_sources == []
    assert result.subjects[0].learning_state is None
    assert result.subjects[0].proof_state is None
    assert result.subjects[0].reviewed_claim is None
    assert result.attendance == []
    assert not db.batches


@pytest.mark.asyncio
async def test_unauthorized_candidate_cannot_read_another_candidates_report() -> None:
    db = FakeSession([context(), [UUID(int=2000)]])
    with pytest.raises(AppError) as error:
        await qualitative_class_report_card(
            CLASS, LEARNER, actor(OTHER_LEARNER, "CANDIDATE"),
            cast(AsyncSession, db)
        )
    assert error.value.status_code == 404
    assert len(db.queries) == 2


@pytest.mark.asyncio
async def test_unassigned_instructor_and_global_assessor_fail_closed() -> None:
    db = FakeSession([context(), [UUID(int=2000)], []])
    with pytest.raises(AppError) as error:
        await qualitative_class_report_card(
            CLASS, LEARNER, actor(INSTRUCTOR, "INSTRUCTOR"),
            cast(AsyncSession, db)
        )
    assert error.value.status_code == 404
    assert len(db.queries) == 3

    assessor = FakeSession([context(), [UUID(int=2000)], []])
    with pytest.raises(AppError) as denied:
        await qualitative_class_report_card(
            CLASS, LEARNER, actor(INSTRUCTOR, "ASSESSOR"),
            cast(AsyncSession, assessor)
        )
    assert denied.value.status_code == 404
    assert len(assessor.queries) == 3


@pytest.mark.asyncio
async def test_missing_class_or_member_fails_before_private_data_reads() -> None:
    class_missing = FakeSession([[]])
    with pytest.raises(AppError) as error:
        await qualitative_class_report_card(
            CLASS, LEARNER, actor(LEARNER, "ACADEMY_ADMIN"),
            cast(AsyncSession, class_missing)
        )
    assert error.value.status_code == 404
    assert len(class_missing.queries) == 1

    no_membership = FakeSession([context(), []])
    with pytest.raises(AppError) as denied:
        await qualitative_class_report_card(
            CLASS, LEARNER, actor(LEARNER, "ACADEMY_ADMIN"),
            cast(AsyncSession, no_membership)
        )
    assert denied.value.status_code == 404
    assert len(no_membership.queries) == 2


def test_report_card_never_creates_proof_or_mutates_source_domains() -> None:
    src = Path("app/academy/report_card_api.py").read_text()
    assert "CapabilityVersion.id.in_(capability_ids)" in src
    assert "Cohort.organization_context_id == actor.organization_context_id" in src
    assert "CohortMembership.member_type == \"CANDIDATE\"" in src
    assert "Session.class_offering_id == offering.id" in src
    assert "derive_learning_state(" in src
    assert 'unit.status == "ACTIVE"' in src
    assert 'assignment.status == "ACTIVE"' in src
    assert "proof_state=None" in src
    assert "read_candidate_safe_reviewed_claims(" in src
    assert "next_learning_focus=None" in src
    for forbidden in (
        "db.commit(",
        "db.add(",
        "record_event(",
        "MissionAssignment",
        "CapabilityClaim(",
        "GateAssessment(",
        "CandidateHomeProjection",
        "proof_state=\"UNPROVEN\"",
    ):
        assert forbidden not in src
