"""Explicit human-reviewed private Classroom Evidence Draft contract tests."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import cast
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import app.evidence.classroom_source_review_api as review_module
from app.academy.models import ClassAssessorObservation
from app.errors import AppError
from app.evidence.api import EvidenceSubmitRequest
from app.evidence.classroom_evidence_draft_api import (
    ClassroomDraftCommand,
    create_classroom_evidence_draft,
    get_classroom_evidence_draft,
)
from app.evidence.classroom_evidence_submission_api import submit_classroom_evidence
from app.evidence.classroom_source_review_api import classroom_source_digest
from app.evidence.consumer import apply_event
from app.evidence.models import (
    ClassroomObservationSourceReview,
    EvidenceCase,
    EvidenceInterpretation,
    EvidenceLink,
)
from app.identity.auth import ActorContext
from app.main import app
from app.platform.events import EventEnvelope
from app.platform.models import DomainEvent, OutboxEvent

ORG = UUID(int=31001)
CLASS = UUID(int=31002)
SESSION = UUID(int=31003)
SOURCE = UUID(int=31004)
OBSERVER = UUID(int=31005)
REVIEWER = UUID(int=31006)
SUBJECT = UUID(int=31007)
GRANT = UUID(int=31008)
SOURCE_GRANT = UUID(int=31009)
REVIEW = UUID(int=31010)
NOW = datetime(2026, 10, 10, 8, tzinfo=UTC)
REASON = "Human explicitly requests private Draft for formal assessment"


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
        self.queries: list[object] = []
        self.added: list[object] = []
        self.commits = 0

    async def execute(self, query: object) -> Rows:
        self.queries.append(query)
        assert self.batches, "unexpected evidence scope database access"
        return Rows(self.batches.pop(0))

    def add(self, value: object) -> None:
        self.added.append(value)

    async def commit(self) -> None:
        self.commits += 1

    async def flush(self) -> None:
        return None


def actor(person: UUID = REVIEWER, role: str = "ASSESSOR") -> ActorContext:
    return ActorContext(
        actor_id=str(person), person_id=person,
        organization_context_id=ORG, roles=frozenset({role}), trace_id="draft-ci",
    )


def observation() -> ClassAssessorObservation:
    return ClassAssessorObservation(
        id=SOURCE, organization_context_id=ORG, class_offering_id=CLASS,
        session_id=SESSION, candidate_person_id=SUBJECT,
        observer_person_id=OBSERVER, grant_id=SOURCE_GRANT, grant_version=2,
        observed_at=NOW - timedelta(minutes=40),
        recorded_at=NOW - timedelta(minutes=20),
        observed_fact="Human-observed class fact in a confidential session",
        idempotency_key="source-test",
    )


def reviewed(s: ClassAssessorObservation) -> ClassroomObservationSourceReview:
    return ClassroomObservationSourceReview(
        id=REVIEW, organization_context_id=ORG, source_observation_id=SOURCE,
        class_offering_id=CLASS, session_id=SESSION, subject_person_id=SUBJECT,
        observer_person_id=OBSERVER, reviewer_person_id=REVIEWER,
        reviewer_grant_id=GRANT, reviewer_grant_version=1,
        source_sha256=classroom_source_digest(s), decision="VERIFIED",
        rationale="Independent factual integrity review", decided_at=NOW,
    )


def command(s: ClassAssessorObservation) -> ClassroomDraftCommand:
    return ClassroomDraftCommand(
        expected_review_id=REVIEW,
        expected_source_sha256=classroom_source_digest(s),
        submission_reason=REASON,
    )


def batches(s: ClassAssessorObservation,
            review: ClassroomObservationSourceReview | None,
            case: EvidenceCase | None = None,
            *, revoked: bool = False) -> list[list[object]]:
    grant = SimpleNamespace(
        id=GRANT, version=1,
        starts_at=NOW - timedelta(hours=1),
        ends_at=NOW + timedelta(hours=1),
        revoked_at=NOW if revoked else None,
    )
    return [
        [s],
        [(grant, SimpleNamespace(status="ACTIVE"), SimpleNamespace(status="ACTIVE"))],
        [SimpleNamespace(
            starts_at=NOW - timedelta(hours=2), ends_at=NOW + timedelta(hours=2),
        )],
        [SimpleNamespace(
            starts_at=NOW - timedelta(hours=1), ends_at=NOW + timedelta(hours=1),
        )],
        [review] if review is not None else [],
        [case] if case is not None else [],
    ]


def get_batches(s: ClassAssessorObservation, review: ClassroomObservationSourceReview,
                case: EvidenceCase) -> list[list[object]]:
    return [[case], *batches(s, review)[:-1]]


@pytest.fixture(autouse=True)
def authorized_time(monkeypatch):
    monkeypatch.setattr(review_module, "current_utc", lambda: NOW)

    async def has_role(*args, **kwargs):
        return True

    monkeypatch.setattr(review_module, "has_organization_role", has_role)


@pytest.mark.asyncio
async def test_explicit_human_draft_created_once_with_private_event() -> None:
    s = observation()
    db = FakeDB(*batches(s, reviewed(s)))
    response = await create_classroom_evidence_draft(
        SOURCE, command(s), actor(), cast(AsyncSession, db),
    )
    assert response.status == "DRAFT"
    assert response.candidate_visible is False
    assert response.observed_fact == s.observed_fact
    assert response.source_review_id == REVIEW
    cases = [v for v in db.added if isinstance(v, EvidenceCase)]
    assert len(cases) == 1
    case = cases[0]
    assert case.provenance["source_sha256"] == classroom_source_digest(s)
    assert case.provenance["created_by_person_id"] == str(REVIEWER)
    assert case.provenance["submission_reason"] == REASON
    assert case.candidate_visible_payload == {}
    assert case.integrity_state == "SOURCE_REVIEWED"
    assert case.source_runtime_event_id is None
    assert case.status == "DRAFT"
    assert db.commits == 1
    events = [v for v in db.added if isinstance(v, DomainEvent)]
    outbox = [v for v in db.added if isinstance(v, OutboxEvent)]
    assert len(events) == len(outbox) == 1
    assert events[0].event_type == "evidence.classroom_draft_created.v1"
    assert events[0].actor == {"type": "PERSON", "id": str(REVIEWER)}
    assert events[0].payload["formal_evidence_accepted"] is False
    for data in (events[0].payload, outbox[0].payload):
        assert s.observed_fact not in str(data)
        assert REASON not in str(data)


@pytest.mark.asyncio
async def test_exact_replay_and_changed_submission_are_idempotent_or_conflict() -> None:
    s = observation()
    created = FakeDB(*batches(s, reviewed(s)))
    await create_classroom_evidence_draft(
        SOURCE, command(s), actor(), cast(AsyncSession, created),
    )
    case = next(x for x in created.added if isinstance(x, EvidenceCase))
    replay = FakeDB(*batches(s, reviewed(s), case))
    response = await create_classroom_evidence_draft(
        SOURCE, command(s), actor(), cast(AsyncSession, replay),
    )
    assert response.evidence_case_id == case.id
    assert replay.commits == 0 and replay.added == []
    conflict = FakeDB(*batches(s, reviewed(s), case))
    with pytest.raises(AppError) as exc:
        await create_classroom_evidence_draft(
            SOURCE, ClassroomDraftCommand(
                expected_review_id=REVIEW,
                expected_source_sha256=classroom_source_digest(s),
                submission_reason="Different human reason cannot rewrite prior Draft",
            ),
            actor(), cast(AsyncSession, conflict),
        )
    assert exc.value.code == "CLASSROOM_DRAFT_CONFLICT"
    assert not conflict.added


@pytest.mark.asyncio
async def test_rejected_or_other_reviewer_never_opens_draft() -> None:
    s = observation()
    for rejected, wrong_identity in ((True, False), (False, True)):
        review = reviewed(s)
        if rejected:
            review.decision = "REJECTED"
        if wrong_identity:
            review.reviewer_person_id = UUID(int=31012)
        db = FakeDB(*batches(s, review)[:-1])
        with pytest.raises(AppError) as exc:
            await create_classroom_evidence_draft(
                SOURCE, command(s), actor(), cast(AsyncSession, db),
            )
        assert exc.value.status_code == 404
        assert db.added == [] and db.commits == 0


@pytest.mark.asyncio
async def test_revoked_grant_or_original_author_cannot_create_draft() -> None:
    s = observation()
    revoked = FakeDB(*batches(s, reviewed(s), revoked=True)[:2])
    with pytest.raises(AppError) as exc:
        await create_classroom_evidence_draft(
            SOURCE, command(s), actor(), cast(AsyncSession, revoked),
        )
    assert exc.value.status_code == 404
    assert revoked.commits == 0 and not revoked.added
    author_db = FakeDB([s])
    with pytest.raises(AppError) as exc:
        await create_classroom_evidence_draft(
            SOURCE, command(s), actor(OBSERVER), cast(AsyncSession, author_db),
        )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_stale_digest_and_wrong_review_id_fail_before_case_insert() -> None:
    s = observation()
    for submitted in (
        ClassroomDraftCommand(
            expected_review_id=UUID(int=31020),
            expected_source_sha256=classroom_source_digest(s),
            submission_reason=REASON,
        ),
        ClassroomDraftCommand(
            expected_review_id=REVIEW,
            expected_source_sha256="0" * 64,
            submission_reason=REASON,
        ),
    ):
        db = FakeDB(*batches(s, reviewed(s))[:-1])
        with pytest.raises(AppError) as exc:
            await create_classroom_evidence_draft(
                SOURCE, submitted, actor(), cast(AsyncSession, db),
            )
        assert exc.value.code == "CLASSROOM_DRAFT_STALE_REVIEW"
        assert db.added == []


@pytest.mark.asyncio
async def test_private_draft_reads_require_creator_and_current_mandate() -> None:
    s = observation()
    db = FakeDB(*batches(s, reviewed(s)))
    await create_classroom_evidence_draft(
        SOURCE, command(s), actor(), cast(AsyncSession, db),
    )
    case = next(x for x in db.added if isinstance(x, EvidenceCase))
    read = FakeDB(*get_batches(s, reviewed(s), case))
    response = await get_classroom_evidence_draft(
        case.id, actor(), cast(AsyncSession, read),
    )
    assert response.observed_fact == s.observed_fact
    other = FakeDB([case])
    with pytest.raises(AppError) as exc:
        await get_classroom_evidence_draft(
            case.id, actor(UUID(int=31022)), cast(AsyncSession, other),
        )
    assert exc.value.status_code == 404
    assert len(other.queries) == 1  # no private Academy source read
    denied = FakeDB([case], *batches(s, reviewed(s), revoked=True)[:2])
    with pytest.raises(AppError) as exc:
        await get_classroom_evidence_draft(
            case.id, actor(), cast(AsyncSession, denied),
        )
    assert exc.value.status_code == 404
    assert denied.commits == 0 and denied.added == []


@pytest.mark.asyncio
async def test_tampered_case_source_is_not_returned_even_to_reviewer() -> None:
    s = observation()
    created = FakeDB(*batches(s, reviewed(s)))
    await create_classroom_evidence_draft(
        SOURCE, command(s), actor(), cast(AsyncSession, created),
    )
    case = next(x for x in created.added if isinstance(x, EvidenceCase))
    case.provenance = {**case.provenance, "source_sha256": "0" * 64}
    read = FakeDB(*get_batches(s, reviewed(s), case))
    with pytest.raises(AppError) as exc:
        await get_classroom_evidence_draft(
            case.id, actor(), cast(AsyncSession, read),
        )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_legacy_event_cannot_sneak_private_classroom_case_into_evidence() -> None:
    fake_envelope = SimpleNamespace(
        event_type="observation.sealed.v1",
        payload={"source_context": "CLASSROOM_OBSERVATION"},
    )
    db = FakeDB()
    await apply_event(cast(EventEnvelope, fake_envelope), cast(AsyncSession, db))
    assert db.queries == [] and db.added == []


def test_private_draft_routes_are_isolated_in_openapi() -> None:
    paths = app.openapi()["paths"]
    assert "post" in paths["/api/v1/classroom-observations/{observation_id}/evidence-draft"]
    assert "get" in paths["/api/v1/classroom-evidence-drafts/{case_id}"]
    assert "post" not in paths["/api/v1/classroom-evidence-drafts/{case_id}"]


def human_interpretation_command() -> EvidenceSubmitRequest:
    return EvidenceSubmitRequest.model_validate({
        "expected_version": 1,
        "interpretation": {
            "behaviour_code": "CLASSROOM_HUMAN_OBSERVATION",
            "behaviour_description": "Human interpretation of an observed fact",
            "signal": "NEUTRAL",
            "scope": "Isolated classroom session",
            "confidence": "LOW",
            "context_difficulty": "Limited CI context",
            "prompt_contamination": "Unknown, explicitly noted by the human",
            "ai_contribution": "NONE",
            "mode": "HUMAN",
            "rationale": "Human review without claims of proof",
            "links": [{
                "target_type": "CAPABILITY",
                "target_ref": "CI_UNAPPROVED_OPAQUE_REFERENCE",
                "signal": "NEUTRAL",
                "scope": "CI session",
                "relevance": "LOW",
                "confidence": "LOW",
            }],
        },
    })


@pytest.mark.asyncio
async def test_classroom_interpretation_submission_is_human_and_confidential() -> None:
    source = observation()
    create = FakeDB(*batches(source, reviewed(source)))
    await create_classroom_evidence_draft(
        SOURCE, command(source), actor(), cast(AsyncSession, create),
    )
    case = next(x for x in create.added if isinstance(x, EvidenceCase))
    db = FakeDB([SOURCE], *batches(source, reviewed(source))[:5], [case])
    result = await submit_classroom_evidence(
        case.id, human_interpretation_command(), actor(), cast(AsyncSession, db),
    )
    assert result.status == "SUBMITTED"
    assert result.version == 2
    assert result.candidate_visible is False
    assert case.accepted_at is None
    assert case.rejected_at is None
    interpretations = [x for x in db.added if isinstance(x, EvidenceInterpretation)]
    links = [x for x in db.added if isinstance(x, EvidenceLink)]
    events = [x for x in db.added if isinstance(x, DomainEvent)]
    outbox = [x for x in db.added if isinstance(x, OutboxEvent)]
    assert len(interpretations) == len(links) == len(events) == len(outbox) == 1
    assert interpretations[0].created_by == REVIEWER
    assert interpretations[0].ai_contribution == "NONE"
    assert links[0].interpretation_id == interpretations[0].id
    assert events[0].event_type == "evidence.interpretation_submitted.v1"
    assert db.commits == 1
    for event_data in (events[0].payload, outbox[0].payload):
        assert source.observed_fact not in str(event_data)
        assert interpretations[0].rationale not in str(event_data)
    scoped = FakeDB(*get_batches(source, reviewed(source), case))
    view = await get_classroom_evidence_draft(
        case.id, actor(), cast(AsyncSession, scoped),
    )
    assert view.status == "SUBMITTED"


@pytest.mark.asyncio
async def test_classroom_submission_denies_unreviewed_and_revoked_person() -> None:
    source = observation()
    case = EvidenceCase(id=UUID(int=31200), version=1)
    missing = FakeDB([SOURCE], *batches(source, None)[:5])
    with pytest.raises(AppError) as exc:
        await submit_classroom_evidence(
            case.id, human_interpretation_command(),
            actor(), cast(AsyncSession, missing),
        )
    assert exc.value.status_code == 404
    assert missing.added == [] and missing.commits == 0
    revoked = FakeDB([SOURCE], *batches(source, reviewed(source), revoked=True)[:2])
    with pytest.raises(AppError) as exc:
        await submit_classroom_evidence(
            case.id, human_interpretation_command(),
            actor(), cast(AsyncSession, revoked),
        )
    assert exc.value.status_code == 404
    assert revoked.added == [] and revoked.commits == 0


def test_classroom_submission_openapi_does_not_expose_generic_mutations() -> None:
    routes = app.openapi()["paths"]
    assert "post" in routes["/api/v1/classroom-evidence-cases/{case_id}/submit"]
    assert "accept" not in routes["/api/v1/classroom-evidence-cases/{case_id}/submit"]
