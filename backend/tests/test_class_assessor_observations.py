"""P23-09C immutable Assessor classroom observation source is not Evidence."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast
from uuid import UUID

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

import app.academy.class_observations_api as module
from app.academy.class_observations_api import (
    ClassObservationCreate,
    create_class_observation,
    list_my_class_observations,
)
from app.academy.models import (
    AssessorClassGrant,
    ClassAssessorObservation,
    ClassOffering,
    Cohort,
    Session,
)
from app.errors import AppError
from app.identity.auth import ActorContext
from app.main import app

ORG, CLASS, COHORT, SESSION, ASSESSOR, CANDIDATE, GRANT = [
    UUID(int=n) for n in range(9701, 9708)
]
T0 = datetime(2026, 10, 9, 10, tzinfo=UTC)


class Result:
    def __init__(self, rows: list):
        self.rows = rows

    def scalar_one_or_none(self):
        return self.rows[0] if self.rows else None

    def first(self):
        return self.rows[0] if self.rows else None

    def scalars(self):
        return self

    def all(self):
        return self.rows


class DB:
    def __init__(self, *rows: list):
        self.queue = list(rows)
        self.statements = []
        self.added = []
        self.commits = 0

    async def execute(self, stmt):
        self.statements.append(stmt)
        assert self.queue, "Unexpected private DB lookup"
        return Result(self.queue.pop(0))

    def add(self, value):
        self.added.append(value)

    async def commit(self):
        self.commits += 1


def actor(role: str = "ASSESSOR", org: UUID = ORG) -> ActorContext:
    return ActorContext(
        actor_id=str(ASSESSOR), person_id=ASSESSOR,
        organization_context_id=org, roles=frozenset({role}), trace_id="trace-test",
    )


def request(**kwargs) -> ClassObservationCreate:
    fields = {
        "session_id": SESSION,
        "candidate_person_id": CANDIDATE,
        "observed_at": T0 - timedelta(minutes=15),
        "observed_fact": "Observed candidate separate a claim from verifiable facts.",
        "idempotency_key": "observation-001",
    }
    fields.update(kwargs)
    return ClassObservationCreate(**fields)


def rows(*, class_status="ACTIVE", cohort_status="ACTIVE", revoked=None,
         grant_start=None, grant_end=None, session_id=SESSION,
         member=True, prior=None) -> list[list]:
    g = AssessorClassGrant(
        id=GRANT, organization_context_id=ORG, class_offering_id=CLASS,
        assessor_person_id=ASSESSOR, starts_at=grant_start or T0 - timedelta(hours=2),
        ends_at=grant_end or T0 + timedelta(hours=2), revoked_at=revoked,
        version=2, created_by=ASSESSOR, updated_by=ASSESSOR,
        created_at=T0, updated_at=T0,
    )
    offering = ClassOffering(
        id=CLASS, cohort_id=COHORT, title="Class", status=class_status,
        primary_capability_version_id=UUID(int=9710),
    )
    cohort = Cohort(
        id=COHORT, organization_context_id=ORG, code="CLASS",
        name="Cohort", status=cohort_status, track_code="PM",
        starts_on=T0.date(), ends_on=None,
    )
    session = Session(
        id=session_id, class_offering_id=CLASS, title="Session",
        starts_at=T0 - timedelta(hours=1),
        ends_at=T0 + timedelta(hours=1),
        delivery_mode="ONLINE", status="ACTIVE",
    )
    return [
        [None], [g], [(offering, cohort)], [prior] if prior else [],
        [session], [UUID(int=9750)] if member else [],
    ]


def test_class_observation_schema_is_immutable_with_no_evidence_mutator() -> None:
    fields = set(ClassAssessorObservation.__table__.c.keys())
    assert {
        "organization_context_id", "class_offering_id", "session_id",
        "candidate_person_id", "observer_person_id", "grant_id", "grant_version",
        "observed_at", "recorded_at", "observed_fact", "idempotency_key",
    }.issubset(fields)
    migration = Path("alembic/versions/0033_class_assessor_observations.py").read_text()
    assert "trg_class_observation_immutable" in migration
    assert "BEFORE UPDATE OR DELETE" in migration
    paths = app.openapi()["paths"]
    path = "/api/v1/class-offerings/{class_offering_id}/observations"
    assert set(paths[path]) == {"get", "post"}
    content = Path("app/academy/class_observations_api.py").read_text()
    for prohibited in ("app.evidence", "app.flag_profile", "app.gate_assessment", "TrainingRun"):
        assert prohibited not in content


@pytest.mark.parametrize("timestamp", [T0.replace(tzinfo=None)])
def test_no_naive_observed_at(timestamp: datetime) -> None:
    with pytest.raises(ValidationError):
        request(observed_at=timestamp)


@pytest.mark.asyncio
async def test_record_factual_observation_with_immutable_audit_and_outbox(monkeypatch) -> None:
    monkeypatch.setattr(module, "current_utc", lambda: T0)
    async def has_role(*args, **kwargs):
        return True
    monkeypatch.setattr(module, "has_organization_role", has_role)
    db = DB(*rows())
    result = await create_class_observation(
        CLASS, request(), actor(), cast(AsyncSession, db),
    )
    assert result.class_offering_id == CLASS
    assert result.session_id == SESSION
    assert result.candidate_person_id == CANDIDATE
    assert result.grant_version == 2
    assert result.observed_at == T0 - timedelta(minutes=15)
    assert result.recorded_at == T0
    assert db.commits == 1
    assert len(db.added) == 3  # ClassObservation + DomainEvent + Outbox
    events = [x for x in db.added if hasattr(x, "event_type")]
    assert {x.event_type for x in events} == {"academy.class_observation_recorded.v1"}
    assert all("observed_fact" not in str(e.payload) for e in events)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("test_rows", "expected_queries"),
    [
        (rows(revoked=T0 - timedelta(minutes=1)), 3),
        (rows(class_status="COMPLETED"), 3),
        (rows(cohort_status="CANCELLED"), 3),
        (rows(member=False), 6),
    ],
)
async def test_fail_closed_for_ended_or_wrong_subject(
    monkeypatch, test_rows: list[list], expected_queries: int,
) -> None:
    monkeypatch.setattr(module, "current_utc", lambda: T0)
    async def has_role(*args, **kwargs):
        return True
    monkeypatch.setattr(module, "has_organization_role", has_role)
    db = DB(*test_rows)
    with pytest.raises(AppError) as err:
        await create_class_observation(
            CLASS, request(), actor(), cast(AsyncSession, db),
        )
    assert err.value.status_code == 404
    assert db.commits == 0
    assert len(db.statements) == expected_queries


@pytest.mark.asyncio
async def test_idempotent_replay_and_conflict_no_second_audit(monkeypatch) -> None:
    monkeypatch.setattr(module, "current_utc", lambda: T0)
    async def has_role(*args, **kwargs):
        return True
    monkeypatch.setattr(module, "has_organization_role", has_role)
    old = ClassAssessorObservation(
        id=UUID(int=9800), organization_context_id=ORG,
        class_offering_id=CLASS, session_id=SESSION,
        candidate_person_id=CANDIDATE, observer_person_id=ASSESSOR,
        grant_id=GRANT, grant_version=2,
        observed_at=T0 - timedelta(minutes=15), recorded_at=T0,
        observed_fact=request().observed_fact, idempotency_key="observation-001",
    )
    db = DB(*rows(prior=old)[:4])
    result = await create_class_observation(CLASS, request(), actor(), cast(AsyncSession, db))
    assert result.observation_id == old.id
    assert db.commits == 0 and not db.added

    db = DB(*rows(prior=old)[:4])
    with pytest.raises(AppError) as err:
        await create_class_observation(
            CLASS, request(observed_fact="Different asserted fact"),
            actor(), cast(AsyncSession, db),
        )
    assert err.value.code == "CLASS_OBSERVATION_IDEMPOTENCY_CONFLICT"
    assert db.commits == 0


@pytest.mark.asyncio
async def test_wrong_actor_role_never_queries_private_rows() -> None:
    db = DB()
    with pytest.raises(AppError) as err:
        await create_class_observation(CLASS, request(), actor("CANDIDATE"),
                                       cast(AsyncSession, db))
    assert err.value.status_code == 404 and not db.statements


@pytest.mark.asyncio
async def test_read_rechecks_current_grant_and_filters_own_scope(monkeypatch) -> None:
    async def authorize(*args, **kwargs):
        return True
    monkeypatch.setattr(module, "has_live_assessor_class_access", authorize)
    item = ClassAssessorObservation(
        id=UUID(int=9810), organization_context_id=ORG,
        class_offering_id=CLASS, session_id=SESSION,
        candidate_person_id=CANDIDATE, observer_person_id=ASSESSOR,
        grant_id=GRANT, grant_version=1,
        observed_at=T0, recorded_at=T0, observed_fact="An observed fact",
        idempotency_key="read-1",
    )
    db = DB([item])
    result = await list_my_class_observations(CLASS, actor(), cast(AsyncSession, db))
    assert len(result) == 1 and result[0].observation_id == item.id
    sql_params = set(db.statements[0].compile().params.values())
    assert {ORG, CLASS, ASSESSOR}.issubset(sql_params)
