"""attendance persistence foundation

Revision ID: 0030
Revises: 0029
Create Date: 2026-10-08
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0030"
down_revision = "0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "attendance_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column(
            "organization_context_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "person_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "updated_by",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('PRESENT', 'ABSENT')",
            name="ck_attendance_record_status",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["academy.sessions.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "session_id",
            "person_id",
            name="uq_attendance_record_session_person",
        ),
        schema="academy",
    )
    op.create_table(
        "attendance_revisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "attendance_record_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "organization_context_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "person_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("expected_version", sa.BigInteger(), nullable=False),
        sa.Column("prior_version", sa.BigInteger(), nullable=True),
        sa.Column("prior_status", sa.String(length=16), nullable=True),
        sa.Column("resulting_version", sa.BigInteger(), nullable=False),
        sa.Column("resulting_status", sa.String(length=16), nullable=False),
        sa.Column(
            "changed_by",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.String(length=160), nullable=False),
        sa.CheckConstraint(
            "prior_status IS NULL OR prior_status IN ('PRESENT', 'ABSENT')",
            name="ck_attendance_revision_prior_status",
        ),
        sa.CheckConstraint(
            "resulting_status IN ('PRESENT', 'ABSENT')",
            name="ck_attendance_revision_resulting_status",
        ),
        sa.CheckConstraint(
            "expected_version >= 0",
            name="ck_attendance_revision_expected_version",
        ),
        sa.CheckConstraint(
            "resulting_version >= 1",
            name="ck_attendance_revision_resulting_version",
        ),
        sa.ForeignKeyConstraint(
            ["attendance_record_id"],
            ["academy.attendance_records.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_context_id",
            "changed_by",
            "idempotency_key",
            name="uq_attendance_revision_idempotency",
        ),
        schema="academy",
    )


def downgrade() -> None:
    op.drop_table("attendance_revisions", schema="academy")
    op.drop_table("attendance_records", schema="academy")
