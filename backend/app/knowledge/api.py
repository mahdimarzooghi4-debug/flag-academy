"""Draft-only Knowledge Registry: no publish, retrieval, council approvals, or AI learning."""

import hashlib
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.errors import AppError
from app.identity.auth import ActorContext, require_role
from app.identity.public_reader import has_organization_role
from app.knowledge.models import KnowledgeSource, KnowledgeSourceVersion
from app.platform.events import new_event, record_event

router = APIRouter(tags=["knowledge"])


class KnowledgeDraftRequest(BaseModel):
    source_key: str = Field(min_length=3, max_length=80, pattern=r"^[a-z0-9][a-z0-9-]+$")
    content_text: str = Field(min_length=1, max_length=20000)
    idempotency_key: str = Field(min_length=1, max_length=160)


class KnowledgeDraftResponse(BaseModel):
    source_id: UUID
    source_key: str
    source_version_id: UUID
    version_number: int
    author_person_id: UUID
    status: str
    classification: str
    content_digest: str
    created_at: datetime


class KnowledgeDraftPage(BaseModel):
    items: list[KnowledgeDraftResponse]
    next_offset: int | None


def draft_response(version: KnowledgeSourceVersion, source: KnowledgeSource) -> KnowledgeDraftResponse:
    return KnowledgeDraftResponse(
        source_id=source.id,
        source_key=source.source_key,
        source_version_id=version.id,
        version_number=version.version_number,
        author_person_id=version.author_person_id,
        status=version.status,
        classification=version.classification,
        content_digest=version.content_digest,
        created_at=version.created_at,
    )


@router.post("/api/v1/knowledge/draft-versions", response_model=KnowledgeDraftResponse, status_code=201)
async def propose_knowledge_draft(
    body: KnowledgeDraftRequest,
    actor: Annotated[ActorContext, Depends(require_role("INSTRUCTOR"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> KnowledgeDraftResponse:
    """Actor-owned versioned drafts; only a separate unimplemented council path may publish."""
    if not await has_organization_role(
        db, person_id=actor.person_id,
        organization_id=actor.organization_context_id, role="INSTRUCTOR",
    ):
        raise AppError("INSUFFICIENT_PERMISSION", "Current instructor role required.", status_code=403)

    # Both the author/idempotency key and the shared source identity are serialized.
    # Stable lock order prevents cross-replica deadlocks across overlapping commands.
    identities = (
        f"knowledge:actor:{actor.organization_context_id}:{actor.person_id}:{body.idempotency_key}",
        f"knowledge:source:{actor.organization_context_id}:{body.source_key}",
    )
    locks = sorted({
        int.from_bytes(
            hashlib.sha256(value.encode("utf-8")).digest()[:8],
            byteorder="big", signed=True,
        )
        for value in identities
    })
    for lock in locks:
        await db.execute(text("SELECT pg_advisory_xact_lock(:key)").bindparams(key=lock))
    digest = hashlib.sha256(body.content_text.encode("utf-8")).hexdigest()

    prior = (
        await db.execute(
            select(KnowledgeSourceVersion, KnowledgeSource)
            .join(KnowledgeSource, KnowledgeSourceVersion.source_id == KnowledgeSource.id)
            .where(
                KnowledgeSourceVersion.organization_context_id == actor.organization_context_id,
                KnowledgeSource.organization_context_id == actor.organization_context_id,
                KnowledgeSourceVersion.author_person_id == actor.person_id,
                KnowledgeSourceVersion.idempotency_key == body.idempotency_key,
            )
        )
    ).first()
    if prior is not None:
        earlier_version, earlier_source = prior
        if earlier_source.source_key != body.source_key or earlier_version.content_digest != digest:
            raise AppError("KNOWLEDGE_IDEMPOTENCY_CONFLICT", "Idempotency key used for another draft.", status_code=409)
        return draft_response(earlier_version, earlier_source)

    source = (
        await db.execute(
            select(KnowledgeSource).where(
                KnowledgeSource.organization_context_id == actor.organization_context_id,
                KnowledgeSource.source_key == body.source_key,
            ).with_for_update()
        )
    ).scalar_one_or_none()
    now = datetime.now(UTC)
    if source is None:
        source = KnowledgeSource(
            id=uuid4(), organization_context_id=actor.organization_context_id,
            source_key=body.source_key, owner_person_id=actor.person_id, created_at=now,
        )
        db.add(source)
        await db.flush()
        version_number = 1
    else:
        if source.owner_person_id != actor.person_id:
            raise AppError("KNOWLEDGE_SOURCE_NOT_FOUND", "Source is not available.", status_code=404)
        latest = (
            await db.execute(
                select(KnowledgeSourceVersion.version_number)
                .where(
                    KnowledgeSourceVersion.source_id == source.id,
                    KnowledgeSourceVersion.organization_context_id == actor.organization_context_id,
                )
                .order_by(KnowledgeSourceVersion.version_number.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        version_number = (latest or 0) + 1

    version = KnowledgeSourceVersion(
        id=uuid4(), source_id=source.id,
        organization_context_id=actor.organization_context_id,
        author_person_id=actor.person_id,
        version_number=version_number, status="DRAFT", classification="INTERNAL",
        content_text=body.content_text, content_digest=digest,
        idempotency_key=body.idempotency_key, created_at=now,
    )
    db.add(version)
    record_event(
        db,
        new_event(
            event_type="knowledge.draft_version_proposed.v1",
            aggregate_type="KnowledgeSource", aggregate_id=source.id,
            aggregate_version=version_number,
            actor={"type": "PERSON", "id": str(actor.person_id)},
            organization_context_id=actor.organization_context_id,
            data_classification="INTERNAL",
            payload={
                "source_version_id": str(version.id),
                "source_key": source.source_key,
                "status": "DRAFT",
                "content_digest": digest,
            },
            trace_id=actor.trace_id,
        ),
    )
    await db.commit()
    return draft_response(version, source)


async def _list_drafts(
    db: AsyncSession, actor: ActorContext, *, only_author: bool, limit: int, offset: int,
) -> KnowledgeDraftPage:
    query = (
        select(KnowledgeSourceVersion, KnowledgeSource)
        .join(KnowledgeSource, KnowledgeSourceVersion.source_id == KnowledgeSource.id)
        .where(
            KnowledgeSourceVersion.organization_context_id == actor.organization_context_id,
            KnowledgeSource.organization_context_id == actor.organization_context_id,
            KnowledgeSourceVersion.status == "DRAFT",
        )
    )
    if only_author:
        query = query.where(KnowledgeSourceVersion.author_person_id == actor.person_id)
    rows = (await db.execute(
        query.order_by(KnowledgeSource.source_key, KnowledgeSourceVersion.version_number)
        .offset(offset).limit(limit + 1)
    )).all()
    return KnowledgeDraftPage(
        items=[draft_response(v, s) for v, s in rows[:limit]],
        next_offset=offset + limit if len(rows) > limit else None,
    )


@router.get("/api/v1/knowledge/my-drafts", response_model=KnowledgeDraftPage)
async def list_my_knowledge_drafts(
    actor: Annotated[ActorContext, Depends(require_role("INSTRUCTOR"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> KnowledgeDraftPage:
    if not await has_organization_role(
        db, person_id=actor.person_id,
        organization_id=actor.organization_context_id, role="INSTRUCTOR",
    ):
        raise AppError("INSUFFICIENT_PERMISSION", "Current instructor role required.", status_code=403)
    return await _list_drafts(db, actor, only_author=True, limit=limit, offset=offset)


@router.get("/api/v1/admin/knowledge/draft-versions", response_model=KnowledgeDraftPage)
async def list_admin_knowledge_drafts(
    actor: Annotated[ActorContext, Depends(require_role("ACADEMY_ADMIN"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> KnowledgeDraftPage:
    if not await has_organization_role(
        db, person_id=actor.person_id,
        organization_id=actor.organization_context_id, role="ACADEMY_ADMIN",
    ):
        raise AppError("INSUFFICIENT_PERMISSION", "Current admin role required.", status_code=403)
    return await _list_drafts(db, actor, only_author=False, limit=limit, offset=offset)
