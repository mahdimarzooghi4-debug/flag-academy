"""learning experience v1

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-04
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text('CREATE SCHEMA IF NOT EXISTS "learning"'))

    op.create_table(
        "learning_units",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("class_offering_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("capability_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("unit_type", sa.String(32), nullable=False),
        sa.Column("phase", sa.String(32), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("resource_url", sa.String(2048), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        schema="learning",
    )
    op.create_index(
        "ix_learning_units_class_position",
        "learning_units",
        ["class_offering_id", "position"],
        schema="learning",
    )

    op.create_table(
        "assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("class_offering_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("capability_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        schema="learning",
    )
    op.create_index(
        "ix_assignments_class_status",
        "assignments",
        ["class_offering_id", "status"],
        schema="learning",
    )

    op.create_table(
        "submissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("assignment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["assignment_id"], ["learning.assignments.id"]),
        sa.UniqueConstraint("assignment_id", "candidate_id"),
        schema="learning",
    )
    op.create_index(
        "ix_submissions_candidate",
        "submissions",
        ["candidate_id", "submitted_at"],
        schema="learning",
    )

    op.create_table(
        "instructor_feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("submission_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("instructor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("feedback_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["submission_id"], ["learning.submissions.id"]),
        schema="learning",
    )
    op.create_index(
        "ix_instructor_feedback_submission_created",
        "instructor_feedback",
        ["submission_id", "created_at"],
        schema="learning",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_instructor_feedback_submission_created",
        table_name="instructor_feedback",
        schema="learning",
    )
    op.drop_table("instructor_feedback", schema="learning")
    op.drop_index("ix_submissions_candidate", table_name="submissions", schema="learning")
    op.drop_table("submissions", schema="learning")
    op.drop_index("ix_assignments_class_status", table_name="assignments", schema="learning")
    op.drop_table("assignments", schema="learning")
    op.drop_index(
        "ix_learning_units_class_position",
        table_name="learning_units",
        schema="learning",
    )
    op.drop_table("learning_units", schema="learning")
    op.execute(sa.text('DROP SCHEMA IF EXISTS "learning"'))
