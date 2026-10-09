"""Knowledge Source immutable draft proposal registry.

Revision ID: 0032
Revises: 0031
Create Date: 2026-10-09
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0032"
down_revision = "0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("CREATE SCHEMA IF NOT EXISTS knowledge"))
    uuid = postgresql.UUID(as_uuid=True)
    op.create_table(
        "sources",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("organization_context_id", uuid, nullable=False),
        sa.Column("source_key", sa.String(96), nullable=False),
        sa.Column("owner_person_id", uuid, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "organization_context_id", "source_key", name="uq_knowledge_source_org_key",
        ),
        schema="knowledge",
    )
    op.create_table(
        "source_versions",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("source_id", uuid, nullable=False),
        sa.Column("organization_context_id", uuid, nullable=False),
        sa.Column("author_person_id", uuid, nullable=False),
        sa.Column("version_number", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("classification", sa.String(32), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("content_digest", sa.String(64), nullable=False),
        sa.Column("idempotency_key", sa.String(160), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["knowledge.sources.id"]),
        sa.UniqueConstraint("source_id", "version_number", name="uq_knowledge_source_version"),
        sa.UniqueConstraint(
            "organization_context_id", "author_person_id", "idempotency_key",
            name="uq_knowledge_draft_actor_idempotency",
        ),
        sa.CheckConstraint("version_number >= 1", name="ck_knowledge_version_positive"),
        sa.CheckConstraint("status = 'DRAFT'", name="ck_knowledge_draft_only"),
        sa.CheckConstraint(
            "content_digest ~ '^[0-9a-f]{64}$'",
            name="ck_knowledge_source_digest_sha256",
        ),
        schema="knowledge",
    )
    op.execute(sa.text("""
        CREATE FUNCTION knowledge.reject_source_version_mutation()
        RETURNS trigger LANGUAGE plpgsql AS '
        BEGIN
            RAISE EXCEPTION ''Knowledge SourceVersion history is immutable'';
        END;'
    """))
    op.execute(sa.text("""
        CREATE TRIGGER trg_knowledge_version_immutable
        BEFORE UPDATE OR DELETE ON knowledge.source_versions
        FOR EACH ROW EXECUTE FUNCTION knowledge.reject_source_version_mutation()
    """))


def downgrade() -> None:
    op.execute(sa.text(
        "DROP TRIGGER IF EXISTS trg_knowledge_version_immutable "
        "ON knowledge.source_versions"
    ))
    op.execute(sa.text("DROP FUNCTION IF EXISTS knowledge.reject_source_version_mutation()"))
    op.drop_table("source_versions", schema="knowledge")
    op.drop_table("sources", schema="knowledge")
    op.execute(sa.text("DROP SCHEMA IF EXISTS knowledge"))
