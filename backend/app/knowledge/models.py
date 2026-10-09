"""Knowledge-source authoring registry, intentionally without publication or retrieval rights."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class KnowledgeSource(Base):
    __tablename__ = "sources"
    __table_args__ = (
        UniqueConstraint("organization_context_id", "source_key", name="uq_knowledge_source_org_key"),
        {"schema": "knowledge"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_context_id: Mapped[UUID]
    source_key: Mapped[str] = mapped_column(String(96))
    owner_person_id: Mapped[UUID]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class KnowledgeSourceVersion(Base):
    """Immutable proposal; not published, approved, indexed, or AI-learning eligible."""

    __tablename__ = "source_versions"
    __table_args__ = (
        UniqueConstraint("source_id", "version_number", name="uq_knowledge_source_version"),
        UniqueConstraint(
            "organization_context_id", "author_person_id", "idempotency_key",
            name="uq_knowledge_draft_actor_idempotency",
        ),
        CheckConstraint("version_number >= 1", name="ck_knowledge_version_positive"),
        CheckConstraint("status = 'DRAFT'", name="ck_knowledge_draft_only"),
        CheckConstraint(
            "content_digest ~ '^[0-9a-f]{64}$'",
            name="ck_knowledge_source_digest_sha256",
        ),
        {"schema": "knowledge"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    source_id: Mapped[UUID] = mapped_column(ForeignKey("knowledge.sources.id"))
    organization_context_id: Mapped[UUID]
    author_person_id: Mapped[UUID]
    version_number: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(16))
    classification: Mapped[str] = mapped_column(String(32))
    content_text: Mapped[str] = mapped_column(Text)
    content_digest: Mapped[str] = mapped_column(String(64))
    idempotency_key: Mapped[str] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
