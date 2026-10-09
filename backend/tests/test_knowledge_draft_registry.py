"""Knowledge drafts never bypass Scientific Council or Academy publication."""

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from uuid import UUID

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import AppError
from app.identity.auth import ActorContext
from app.knowledge.api import (
    KnowledgeDraftRequest,
    list_admin_knowledge_drafts,
    list_my_knowledge_drafts,
    propose_knowledge_draft,
)
from app.knowledge.models import KnowledgeSource, KnowledgeSourceVersion
from app.main import app

ORG, AUTHOR, OTHER = UUID(int=82001), UUID(int=82002), UUID(int=82003)
NOW = datetime(2026, 10, 9, tzinfo=UTC)


def actor(role: str = "INSTRUCTOR", person_id: UUID = AUTHOR) -> ActorContext:
    return ActorContext(
        actor_id=str(person_id), person_id=person_id,
        organization_context_id=ORG, roles=frozenset({role}),
    )


def draft(source_key: str = "decision-guidance", content_text: str = "Reason about tradeoffs", key: str = "one") -> KnowledgeDraftRequest:
    return KnowledgeDraftRequest(
        source_key=source_key, content_text=content_text, idempotency_key=key,
    )


def source(owner: UUID = AUTHOR) -> KnowledgeSource:
    return KnowledgeSource(
        id=UUID(int=82004), organization_context_id=ORG,
        owner_person_id=owner, source_key="decision-guidance", created_at=NOW,
    )


def version(src: KnowledgeSource, *, content: str = "Reason about tradeoffs", key: str = "one") -> KnowledgeSourceVersion:
    return KnowledgeSourceVersion(
        id=UUID(int=82005), source_id=src.id,
        organization_context_id=ORG, author_person_id=AUTHOR,
        version_number=1, status="DRAFT", classification="INTERNAL",
        content_text=content, content_digest=hashlib.sha256(content.encode()).hexdigest(),
        idempotency_key=key, created_at=NOW,
    )


class Result:
    def __init__(self, rows: list[Any]):
        self.rows = rows

    def first(self):
        return self.rows[0] if self.rows else None

    def scalar_one_or_none(self):
        assert len(self.rows) < 2
        return self.rows[0] if self.rows else None

    def all(self):
        return self.rows


class DB:
    def __init__(self, batches: list[list[Any]]):
        self.batches = list(batches)
        self.statements: list[Any] = []
        self.added: list[Any] = []
        self.flushes = 0
        self.commits = 0

    async def execute(self, query):
        self.statements.append(query)
        assert self.batches, "unexpected query"
        return Result(self.batches.pop(0))

    def add(self, item):
        self.added.append(item)

    async def flush(self):
        self.flushes += 1

    async def commit(self):
        self.commits += 1


def test_draft_contract_requires_separate_governed_publication():
    paths = app.openapi()["paths"]
    assert set(paths["/api/v1/knowledge/draft-versions"]) == {"post"}
    assert set(paths["/api/v1/knowledge/my-drafts"]) == {"get"}
    assert set(paths["/api/v1/admin/knowledge/draft-versions"]) == {"get"}
    assert not any("publish" in p or "retrieve" in p for p in paths if "knowledge" in p)
    assert all("security" in paths[path][method]
        for path, method in [
            ("/api/v1/knowledge/draft-versions", "post"),
            ("/api/v1/knowledge/my-drafts", "get"),
            ("/api/v1/admin/knowledge/draft-versions", "get"),
        ]
    )
    with pytest.raises(ValidationError):
        draft(source_key="../../private")
    with pytest.raises(ValidationError):
        draft(source_key="safe", content_text="")


@pytest.mark.asyncio
async def test_author_creates_immutable_draft_and_outbox_atomically():
    db = DB([[UUID(int=100)], [], [], []])
    response = await propose_knowledge_draft(draft(), actor(), cast(AsyncSession, db))
    assert response.source_key == "decision-guidance"
    assert response.version_number == 1 and response.status == "DRAFT"
    assert response.classification == "INTERNAL"
    assert response.content_digest == hashlib.sha256(b"Reason about tradeoffs").hexdigest()
    assert db.flushes == 1 and db.commits == 1
    assert len([i for i in db.added if isinstance(i, KnowledgeSource)]) == 1
    assert len([i for i in db.added if isinstance(i, KnowledgeSourceVersion)]) == 1
    assert len(db.added) == 4  # source, version, domain event, transactional outbox
    assert ORG in set(db.statements[2].compile().params.values())
    assert AUTHOR in set(db.statements[2].compile().params.values())
    assert "pg_advisory_xact_lock" in str(db.statements[1])


@pytest.mark.asyncio
async def test_retry_replays_same_snapshot_but_rejects_different_payload():
    s = source()
    v = version(s)
    ok = DB([[UUID(int=100)], [], [(v, s)]])
    reply = await propose_knowledge_draft(draft(), actor(), cast(AsyncSession, ok))
    assert reply.source_version_id == v.id
    assert reply.version_number == 1 and ok.commits == 0 and not ok.added

    wrong = DB([[UUID(int=100)], [], [(v, s)]])
    with pytest.raises(AppError) as exc:
        await propose_knowledge_draft(draft(content_text="different"), actor(), cast(AsyncSession, wrong))
    assert exc.value.status_code == 409 and not wrong.added


@pytest.mark.asyncio
async def test_second_version_preserves_source_and_checks_ownership():
    s = source()
    db = DB([[UUID(int=100)], [], [], [s], [1]])
    reply = await propose_knowledge_draft(draft(key="two"), actor(), cast(AsyncSession, db))
    assert reply.version_number == 2
    assert db.flushes == 0 and db.commits == 1
    assert len([i for i in db.added if isinstance(i, KnowledgeSourceVersion)]) == 1

    foreign_owner = DB([[UUID(int=100)], [], [], [source(owner=OTHER)]])
    with pytest.raises(AppError) as exc:
        await propose_knowledge_draft(draft(key="two"), actor(), cast(AsyncSession, foreign_owner))
    assert exc.value.status_code == 404 and not foreign_owner.added


@pytest.mark.asyncio
async def test_no_current_instructor_role_denies_before_source_or_idempotency_reads():
    db = DB([[]])
    with pytest.raises(AppError) as exc:
        await propose_knowledge_draft(draft(), actor(), cast(AsyncSession, db))
    assert exc.value.status_code == 403
    assert len(db.statements) == 1 and not db.added


@pytest.mark.asyncio
async def test_metadata_reads_are_tenant_and_author_scoped_and_exclude_content():
    s = source()
    v = version(s)
    instructor = DB([[UUID(int=100)], [(v, s)]])
    page = await list_my_knowledge_drafts(actor(), cast(AsyncSession, instructor), limit=1, offset=7)
    assert page.items[0].source_id == s.id
    assert page.next_offset is None
    assert "content_text" not in page.model_dump_json()
    filters = str(instructor.statements[1])
    assert "author_person_id" in filters and "organization_context_id" in filters

    admin = DB([[UUID(int=100)], [(v, s)]])
    result = await list_admin_knowledge_drafts(actor("ACADEMY_ADMIN"), cast(AsyncSession, admin), limit=5, offset=0)
    assert result.items[0].status == "DRAFT"
    assert "organization_context_id" in str(admin.statements[1])
    assert "author_person_id" not in str(admin.statements[1])


def test_migration_has_append_only_db_trigger_and_exact_model_columns():
    migration = Path("alembic/versions/0032_knowledge_draft_registry.py").read_text()
    assert "CREATE TRIGGER trg_knowledge_version_immutable" in migration
    assert "BEFORE UPDATE OR DELETE" in migration
    assert "status = 'DRAFT'" in migration
    from app.db import Base

    table = Base.metadata.tables["knowledge.source_versions"]
    assert table.c.content_digest is not None
    assert table.c.content_text is not None
    assert table.c.idempotency_key is not None
