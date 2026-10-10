"""Academy Assessor class mandates and append-only history.

Revision ID: 0031
Revises: 0030
Create Date: 2026-10-09
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0031"
down_revision = "0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    op.create_table(
        "assessor_class_grants",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("organization_context_id", uuid, nullable=False),
        sa.Column("class_offering_id", uuid, nullable=False),
        sa.Column("assessor_person_id", uuid, nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", uuid, nullable=False),
        sa.Column("updated_by", uuid, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["class_offering_id"], ["academy.class_offerings.id"]),
        sa.UniqueConstraint(
            "class_offering_id", "assessor_person_id",
            name="uq_assessor_grant_class_person",
        ),
        sa.CheckConstraint("ends_at > starts_at", name="ck_assessor_grant_window"),
        sa.CheckConstraint("version >= 1", name="ck_assessor_grant_version"),
        schema="academy",
    )
    op.create_table(
        "assessor_class_grant_revisions",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("grant_id", uuid, nullable=False),
        sa.Column("organization_context_id", uuid, nullable=False),
        sa.Column("class_offering_id", uuid, nullable=False),
        sa.Column("assessor_person_id", uuid, nullable=False),
        sa.Column("actor_id", uuid, nullable=False),
        sa.Column("action", sa.String(16), nullable=False),
        sa.Column("reason", sa.String(500), nullable=True),
        sa.Column("expected_version", sa.BigInteger(), nullable=False),
        sa.Column("resulting_version", sa.BigInteger(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("idempotency_key", sa.String(160), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["grant_id"], ["academy.assessor_class_grants.id"]),
        sa.UniqueConstraint(
            "organization_context_id", "actor_id", "idempotency_key",
            name="uq_assessor_grant_revision_actor_key",
        ),
        sa.CheckConstraint("expected_version >= 0", name="ck_assessor_revision_expected"),
        sa.CheckConstraint("resulting_version >= 1", name="ck_assessor_revision_version"),
        schema="academy",
    )
    op.execute(
        sa.text(
            """
            CREATE FUNCTION academy.reject_assessor_grant_revision_mutation()
            RETURNS trigger LANGUAGE plpgsql AS '
            BEGIN
                RAISE EXCEPTION ''assessor grant audit history is append-only'';
            END;'
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE TRIGGER trg_assessor_grant_revision_immutable
            BEFORE UPDATE OR DELETE ON academy.assessor_class_grant_revisions
            FOR EACH ROW
            EXECUTE FUNCTION academy.reject_assessor_grant_revision_mutation()
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            DROP TRIGGER IF EXISTS trg_assessor_grant_revision_immutable
            ON academy.assessor_class_grant_revisions
            """
        )
    )
    op.execute(sa.text("DROP FUNCTION IF EXISTS academy.reject_assessor_grant_revision_mutation()"))
    op.drop_table("assessor_class_grant_revisions", schema="academy")
    op.drop_table("assessor_class_grants", schema="academy")
