"""Immutable Evidence-owned independent classroom source review.

Revision ID: 0034
Revises: 0033
Create Date: 2026-10-09
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0034"
down_revision = "0033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    op.create_table(
        "classroom_observation_source_reviews",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("organization_context_id", uuid, nullable=False),
        sa.Column("source_observation_id", uuid, nullable=False),
        sa.Column("class_offering_id", uuid, nullable=False),
        sa.Column("session_id", uuid, nullable=False),
        sa.Column("subject_person_id", uuid, nullable=False),
        sa.Column("observer_person_id", uuid, nullable=False),
        sa.Column("reviewer_person_id", uuid, nullable=False),
        sa.Column("reviewer_grant_id", uuid, nullable=False),
        sa.Column("reviewer_grant_version", sa.BigInteger(), nullable=False),
        sa.Column("source_sha256", sa.String(64), nullable=False),
        sa.Column("decision", sa.String(16), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "organization_context_id", "source_observation_id",
            name="uq_classroom_source_review_per_observation",
        ),
        sa.CheckConstraint(
            "decision IN ('VERIFIED', 'REJECTED')",
            name="ck_classroom_source_review_decision",
        ),
        sa.CheckConstraint("length(trim(rationale)) > 0", name="ck_classroom_review_reason"),
        schema="evidence",
    )
    op.execute(sa.text("""
        CREATE FUNCTION evidence.reject_classroom_source_review_mutation()
        RETURNS trigger LANGUAGE plpgsql AS '
        BEGIN
            RAISE EXCEPTION ''Independent classroom source reviews are immutable'';
        END;'
    """))
    op.execute(sa.text("""
        CREATE TRIGGER trg_classroom_source_review_immutable
        BEFORE UPDATE OR DELETE ON evidence.classroom_observation_source_reviews
        FOR EACH ROW EXECUTE FUNCTION evidence.reject_classroom_source_review_mutation()
    """))


def downgrade() -> None:
    op.execute(sa.text(
        "DROP TRIGGER IF EXISTS trg_classroom_source_review_immutable "
        "ON evidence.classroom_observation_source_reviews"
    ))
    op.execute(sa.text(
        "DROP FUNCTION IF EXISTS evidence.reject_classroom_source_review_mutation()"
    ))
    op.drop_table("classroom_observation_source_reviews", schema="evidence")
