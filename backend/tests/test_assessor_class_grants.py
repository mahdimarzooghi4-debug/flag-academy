"""P23-09: an Academy-granted class mandate is not a global ASSESSOR role."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import cast
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.academy.assessor_grants_api import (
    GrantCreateRequest,
    GrantExtendRequest,
    GrantRevokeRequest,
    create_assessor_class_grant,
    extend_assessor_class_grant,
    revoke_assessor_class_grant,
)
from app.academy.assessor_grants_policy import active_class_grant
from app.academy.models import AssessorClassGrant, AssessorClassGrantRevision
from app.errors import AppError
from app.identity.auth import ActorContext
from app.main import app

ORG, CLASS, COHORT, ADMIN, ASSESSOR = [UUID(int=x) for x in (8201, 8202, 8203, 8204, 8205)]
T0 = datetime(2026, 10, 9, 10, tzinfo=UTC)


def actor(role: str = "ACADEMY_ADMIN", org: UUID = ORG) -> ActorContext:
    return ActorContext(
        actor_id=str(ADMIN),
        person_id=ADMIN,
        organization_context_id=org,
        roles=frozenset({role}),
    )


def grant(**overrides):
    row = dict(
        id=UUID(int=8206),
        version=1,
        organization_context_id=ORG,
        class_offering_id=CLASS,
        assessor_person_id=ASSESSOR,
        starts_at=T0 - timedelta(days=1),
        ends_at=T0 + timedelta(days=1),
        revoked_at=None,
        created_by=ADMIN,
        updated_by=ADMIN,
        created_at=T0,
        updated_at=T0,
    )
    row.update(overrides)
    return AssessorClassGrant(**row)


class FakeResult:
    def __init__(self, rows: list):
        self.rows = rows

    def first(self):
        return self.rows[0] if self.rows else None

    def scalar_one_or_none(self):
        assert len(self.rows) <= 1
        return self.rows[0] if self.rows else None


class FakeDB:
    def __init__(self, batches: list[list]):
        self.batches = list(batches)
        self.statements = []
        self.added = []
        self.commits = 0

    async def execute(self, stmt):
        self.statements.append(stmt)
        assert self.batches, "unexpected data access"
        return FakeResult(self.batches.pop(0))

    def add(self, item):
        self.added.append(item)

    async def commit(self):
        self.commits += 1


def test_grant_policy_is_fail_closed_for_time_role_and_class_state():
    g = grant()
    assert active_class_grant(g, now=T0, class_status="ACTIVE", cohort_status="ACTIVE")
    assert not active_class_grant(g, now=T0 - timedelta(days=2), class_status="ACTIVE", cohort_status="ACTIVE")
    assert not active_class_grant(g, now=g.ends_at, class_status="ACTIVE", cohort_status="ACTIVE")
    assert not active_class_grant(g, now=T0, class_status="COMPLETED", cohort_status="ACTIVE")
    assert not active_class_grant(g, now=T0, class_status="ACTIVE", cohort_status="CANCELLED")
    assert not active_class_grant(grant(revoked_at=T0), now=T0, class_status="ACTIVE", cohort_status="ACTIVE")


def test_grant_schema_has_tenant_class_identity_and_immutable_audit():
    names = set(AssessorClassGrant.__table__.c.keys())
    assert {"organization_context_id", "class_offering_id", "assessor_person_id",
            "starts_at", "ends_at", "revoked_at", "version", "created_by", "updated_by"}.issubset(names)
    revision_names = set(AssessorClassGrantRevision.__table__.c.keys())
    assert {"grant_id", "action", "actor_id", "idempotency_key", "expected_version",
            "resulting_version", "reason", "occurred_at"}.issubset(revision_names)
    source = Path("alembic/versions/0031_assessor_class_grants.py").read_text()
    assert "uq_assessor_grant_class_person" in source
    assert "uq_assessor_grant_revision_actor_key" in source
    assert "trg_assessor_grant_revision_immutable" in source
    assert "BEFORE UPDATE OR DELETE" in source


def test_openapi_exposes_admin_only_commands_without_automatic_evidence():
    paths = app.openapi()["paths"]
    assert set(paths["/api/v1/admin/academy/classes/{class_offering_id}/assessor-grants"]) == {"post"}
    assert set(paths["/api/v1/admin/academy/assessor-grants/{grant_id}/extend"]) == {"post"}
    assert set(paths["/api/v1/admin/academy/assessor-grants/{grant_id}/revoke"]) == {"post"}
    source = Path("app/academy/assessor_grants_api.py").read_text()
    assert 'require_role("ACADEMY_ADMIN")' in source
    for forbidden in ("app.evidence", "app.flag_profile", "app.gate_assessment", "GateAssessment"):
        assert forbidden not in source


@pytest.mark.asyncio
async def test_cross_tenant_class_rejected_before_grant_or_identity_lookup():
    db = FakeDB([[]])
    with pytest.raises(AppError) as err:
        await create_assessor_class_grant(
            CLASS,
            GrantCreateRequest(assessor_person_id=ASSESSOR,
                               starts_at=T0, ends_at=T0 + timedelta(days=2),
                               idempotency_key="create-1"),
            actor(), cast(AsyncSession, db),
        )
    assert err.value.status_code == 404
    assert len(db.statements) == 1 and db.commits == 0


@pytest.mark.asyncio
async def test_non_assessor_membership_denied_without_grant_write():
    offering = SimpleNamespace(id=CLASS, status="ACTIVE")
    cohort = SimpleNamespace(id=COHORT, status="ACTIVE")
    db = FakeDB([[(offering, cohort)], []])
    with pytest.raises(AppError) as err:
        await create_assessor_class_grant(
            CLASS,
            GrantCreateRequest(assessor_person_id=ASSESSOR,
                               starts_at=T0, ends_at=T0 + timedelta(days=2),
                               idempotency_key="create-2"),
            actor(), cast(AsyncSession, db),
        )
    assert err.value.status_code in (403, 404)
    assert db.added == [] and db.commits == 0


@pytest.mark.asyncio
async def test_stale_extend_and_revoke_do_not_mutate_grant():
    existing = grant(version=3)
    for payload in (
        GrantExtendRequest(expected_version=2, ends_at=T0 + timedelta(days=7),
                           reason="extend approved", idempotency_key="ext-1"),
        GrantRevokeRequest(expected_version=2, reason="appointment ended",
                           idempotency_key="revoke-1"),
    ):
        db = FakeDB([[existing], []])
        with pytest.raises(AppError) as err:
            if isinstance(payload, GrantExtendRequest):
                await extend_assessor_class_grant(
                    existing.id, payload, actor(), cast(AsyncSession, db)
                )
            else:
                await revoke_assessor_class_grant(
                    existing.id, payload, actor(), cast(AsyncSession, db)
                )
        assert err.value.status_code == 409
        assert db.commits == 0


def test_invalid_intervals_fail_schema_validation():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        GrantCreateRequest(assessor_person_id=ASSESSOR, starts_at=T0,
                           ends_at=T0, idempotency_key="no-duration")
    with pytest.raises(ValidationError):
        GrantExtendRequest(expected_version=1, ends_at=T0.replace(tzinfo=None),
                           reason="invalid timestamp", idempotency_key="naive")
