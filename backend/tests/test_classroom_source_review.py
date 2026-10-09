"""Evidence-owned human source review: independence, scope, integrity, audit."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Literal, cast
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import app.evidence.classroom_source_review_api as module
from app.academy.models import ClassAssessorObservation
from app.errors import AppError
from app.evidence.classroom_source_review_api import (
    ClassroomReviewCommand,
    classroom_source_digest,
    read_classroom_review_source,
    review_classroom_source,
)
from app.evidence.models import ClassroomObservationSourceReview, EvidenceCase
from app.identity.auth import ActorContext
from app.main import app
from app.platform.models import DomainEvent, OutboxEvent

ORG = UUID(int=7001)
CLASS = UUID(int=7002)
SESSION = UUID(int=7003)
SOURCE = UUID(int=7004)
OBSERVER = UUID(int=7005)
REVIEWER = UUID(int=7006)
SUBJECT = UUID(int=7007)
GRANT = UUID(int=7008)
SOURCE_GRANT = UUID(int=7009)
NOW = datetime(2026, 10, 9, 12, tzinfo=UTC)


class Rows:
    def __init__(self, records: list[object]) -> None:
        self.records = records

    def first(self) -> object | None:
        return self.records[0] if self.records else None

    def scalar_one_or_none(self) -> object | None:
        return self.records[0] if self.records else None


class FakeDB:
    def __init__(self, *batches: list[object]) -> None:
        self.batches = list(batches)
        self.statements: list[object] = []
        self.added: list[object] = []
        self.commits = 0

    async def execute(self, statement: object) -> Rows:
        self.statements.append(statement)
        assert self.batches, "Unexpected private data access"
        return Rows(self.batches.pop(0))

    def add(self, obj: object) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        self.commits += 1


def actor(person: UUID = REVIEWER, role: str = "ASSESSOR") -> ActorContext:
    return ActorContext(
        actor_id=str(person), person_id=person, organization_context_id=ORG,
        roles=frozenset({role}), trace_id="source-review-test",
    )


def observation() -> ClassAssessorObservation:
    return ClassAssessorObservation(
        id=SOURCE, organization_context_id=ORG, class_offering_id=CLASS,
        session_id=SESSION, candidate_person_id=SUBJECT,
        observer_person_id=OBSERVER, grant_id=SOURCE_GRANT, grant_version=2,
        observed_at=NOW - timedelta(minutes=40),
        recorded_at=NOW - timedelta(minutes=20),
        observed_fact="فراگیر تفاوت واقعیت و تفسیر را به‌روشنی توضیح داد.",
        idempotency_key="observed-one",
    )


def batches(source: ClassAssessorObservation | None = None,
            *, current: bool = True, original: bool = True,
            session_match: bool = True,
            prior: ClassroomObservationSourceReview | None = None) -> list[list[object]]:
    s = source or observation()
    reviewer_grant = SimpleNamespace(
        id=GRANT, version=1, starts_at=NOW - timedelta(hours=1),
        ends_at=NOW + timedelta(hours=1), revoked_at=None if current else NOW,
    )
    offering = SimpleNamespace(id=CLASS, status="ACTIVE")
    cohort = SimpleNamespace(status="ACTIVE")
    original_revision = SimpleNamespace(
        starts_at=NOW - timedelta(hours=2), ends_at=NOW + timedelta(hours=2),
    )
    session = SimpleNamespace(
        starts_at=NOW - timedelta(hours=1) if session_match else NOW,
        ends_at=NOW + timedelta(hours=1),
    )
    return [
        [s],
        [(reviewer_grant, offering, cohort)],
        [original_revision] if original else [],
        [session],
        [prior] if prior else [],
    ]


def command(source: ClassAssessorObservation | None = None,
            decision: Literal["VERIFIED", "REJECTED"] = "VERIFIED", rationale: str = "Reviewed factual context") -> ClassroomReviewCommand:
    return ClassroomReviewCommand(
        expected_source_sha256=classroom_source_digest(source or observation()),
        decision=decision,
        rationale=rationale,
    )


@pytest.mark.asyncio
async def test_explicit_independent_human_source_review_is_audited_without_evidence(monkeypatch) -> None:
    monkeypatch.setattr(module, "current_utc", lambda: NOW)

    async def authorized(*args, **kwargs):
        return True

    monkeypatch.setattr(module, "has_organization_role", authorized)
    s = observation()
    db = FakeDB(*batches(s))
    result = await review_classroom_source(
        SOURCE, command(s), actor(), cast(AsyncSession, db),
    )
    assert result.source_observation_id == SOURCE
    assert result.reviewer_person_id == REVIEWER
    assert result.source_sha256 == classroom_source_digest(s)
    assert result.decision == "VERIFIED"
    assert db.commits == 1
    review_rows = [x for x in db.added if isinstance(x, ClassroomObservationSourceReview)]
    assert len(review_rows) == 1
    assert review_rows[0].observer_person_id != review_rows[0].reviewer_person_id
    assert not any(isinstance(x, EvidenceCase) for x in db.added)
    events = [x for x in db.added if isinstance(x, DomainEvent)]
    outbox = [x for x in db.added if isinstance(x, OutboxEvent)]
    assert len(events) == len(outbox) == 1
    assert events[0].event_type == "evidence.classroom_source_reviewed.v1"
    assert events[0].actor == {"type": "PERSON", "id": str(REVIEWER)}
    assert "observed_fact" not in str(events[0].payload)
    assert s.observed_fact not in str(events[0].payload)
    assert s.observed_fact not in str(outbox[0].payload)
    assert "Reviewed factual context" not in str(outbox[0].payload)
    assert events[0].payload["evidence_case_created"] is False


@pytest.mark.asyncio
async def test_reviewer_must_be_another_currently_appointed_assessor(monkeypatch) -> None:
    monkeypatch.setattr(module, "current_utc", lambda: NOW)

    async def authorized(*args, **kwargs):
        return True

    monkeypatch.setattr(module, "has_organization_role", authorized)
    source = observation()
    for person, data in [
        (OBSERVER, [[source]]),
        (REVIEWER, [[source], []]),
        (REVIEWER, batches(source, current=False)),
    ]:
        db = FakeDB(*data)
        with pytest.raises(AppError) as exc:
            await review_classroom_source(
                SOURCE, command(source), actor(person), cast(AsyncSession, db),
            )
        assert exc.value.status_code == 404
        assert db.commits == 0 and not db.added

    no_role = FakeDB()
    with pytest.raises(AppError) as exc:
        await review_classroom_source(
            SOURCE, command(source), actor(REVIEWER, "CANDIDATE"),
            cast(AsyncSession, no_role),
        )
    assert exc.value.status_code == 404
    assert no_role.statements == []


@pytest.mark.asyncio
async def test_reject_invalid_original_source_grant_and_session(monkeypatch) -> None:
    monkeypatch.setattr(module, "current_utc", lambda: NOW)

    async def authorized(*args, **kwargs):
        return True

    monkeypatch.setattr(module, "has_organization_role", authorized)
    for rows in (batches(original=False), batches(session_match=False)):
        db = FakeDB(*rows)
        with pytest.raises(AppError) as exc:
            await read_classroom_review_source(SOURCE, actor(), cast(AsyncSession, db))
        assert exc.value.status_code == 404
        assert not db.added


@pytest.mark.asyncio
async def test_source_digest_is_pinned_and_stale_decision_fails(monkeypatch) -> None:
    monkeypatch.setattr(module, "current_utc", lambda: NOW)

    async def authorized(*args, **kwargs):
        return True

    monkeypatch.setattr(module, "has_organization_role", authorized)
    source = observation()
    first_digest = classroom_source_digest(source)
    source.observed_fact += " تغییر"
    assert first_digest != classroom_source_digest(source)
    db = FakeDB(*batches(source))
    with pytest.raises(AppError) as exc:
        await review_classroom_source(
            SOURCE, ClassroomReviewCommand(
                expected_source_sha256=first_digest,
                decision="VERIFIED", rationale="Reviewed",
            ),
            actor(), cast(AsyncSession, db),
        )
    assert exc.value.code == "CLASSROOM_SOURCE_CHANGED"
    assert db.commits == 0 and not db.added


@pytest.mark.asyncio
async def test_repeat_review_does_not_write_and_conflicting_decision_is_denied(monkeypatch) -> None:
    monkeypatch.setattr(module, "current_utc", lambda: NOW)

    async def authorized(*args, **kwargs):
        return True

    monkeypatch.setattr(module, "has_organization_role", authorized)
    source = observation()
    old = ClassroomObservationSourceReview(
        id=UUID(int=7020), organization_context_id=ORG,
        source_observation_id=SOURCE, class_offering_id=CLASS, session_id=SESSION,
        subject_person_id=SUBJECT, observer_person_id=OBSERVER,
        reviewer_person_id=REVIEWER, reviewer_grant_id=GRANT,
        reviewer_grant_version=1, source_sha256=classroom_source_digest(source),
        decision="VERIFIED", rationale="Reviewed factual context", decided_at=NOW,
    )
    replay = FakeDB(*batches(source, prior=old))
    result = await review_classroom_source(
        SOURCE, command(source), actor(), cast(AsyncSession, replay),
    )
    assert result.review_id == old.id
    assert replay.commits == 0 and replay.added == []
    conflict = FakeDB(*batches(source, prior=old))
    with pytest.raises(AppError) as exc:
        await review_classroom_source(
            SOURCE, command(source, decision="REJECTED"), actor(),
            cast(AsyncSession, conflict),
        )
    assert exc.value.code == "CLASSROOM_SOURCE_REVIEW_CONFLICT"
    assert conflict.commits == 0 and conflict.added == []


@pytest.mark.asyncio
async def test_explicit_rejection_creates_no_evidence_or_mutation(monkeypatch) -> None:
    monkeypatch.setattr(module, "current_utc", lambda: NOW)

    async def authorized(*args, **kwargs):
        return True

    monkeypatch.setattr(module, "has_organization_role", authorized)
    db = FakeDB(*batches())
    result = await review_classroom_source(
        SOURCE, command(decision="REJECTED", rationale="Insufficient factual context"),
        actor(), cast(AsyncSession, db),
    )
    assert result.decision == "REJECTED"
    assert not any(isinstance(x, EvidenceCase) for x in db.added)
    assert db.commits == 1


def test_source_review_openapi_and_database_append_only_guard() -> None:
    paths = app.openapi()["paths"]
    path = "/api/v1/classroom-observations/{observation_id}/review-source"
    assert set(paths[path]) == {"get", "post"}
    source = Path("app/evidence/classroom_source_review_api.py").read_text()
    assert "evidence.classroom_source_reviewed.v1" in source
    for disallowed in ("EvidenceCase(", "ProfileUpdateCase(", "GateAssessment(", "TrainingRun("):
        assert disallowed not in source
    migration = Path("alembic/versions/0034_classroom_source_review.py").read_text()
    assert "trg_classroom_source_review_immutable" in migration
    assert "BEFORE UPDATE OR DELETE" in migration
