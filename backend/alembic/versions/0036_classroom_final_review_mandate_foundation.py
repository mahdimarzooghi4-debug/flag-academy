"""Inert Evidence final-review mandate schema and stricter classroom history protection.

Revision ID: 0036
Revises: 0035
Create Date: 2026-10-10

The table does NOT establish who may issue a mandate and has no write API.
The existing 0035 decision barrier remains in force.
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0036"
down_revision = "0035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "classroom_final_evidence_review_mandates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("organization_context_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evidence_case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("class_offering_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reviewer_person_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("issued_by_person_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["evidence_case_id"], ["evidence.evidence_cases.id"],
        ),
        sa.CheckConstraint("version >= 1", name="ck_classroom_final_mandate_version"),
        sa.CheckConstraint("ends_at > starts_at", name="ck_classroom_final_mandate_window"),
        schema="evidence",
    )
    # The original 0035 trigger guards status/version/acceptance. Its permissive
    # DRAFT->SUBMITTED update path previously left other lineage fields editable.
    # A separate trigger now makes every non-transition field immutable.
    op.execute(sa.text("""
        CREATE FUNCTION evidence.guard_classroom_case_complete_lineage()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF OLD.source_context = 'CLASSROOM_OBSERVATION' THEN
                IF OLD.status = 'SUBMITTED' THEN
                    RAISE EXCEPTION 'Submitted classroom Evidence cannot be mutated';
                END IF;
                IF (to_jsonb(NEW) - 'status' - 'version' - 'updated_at')
                    IS DISTINCT FROM
                   (to_jsonb(OLD) - 'status' - 'version' - 'updated_at') THEN
                    RAISE EXCEPTION 'Classroom Evidence immutable fields changed';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$
    """))
    op.execute(sa.text("""
        CREATE TRIGGER trg_classroom_case_complete_lineage
        BEFORE UPDATE ON evidence.evidence_cases
        FOR EACH ROW EXECUTE FUNCTION evidence.guard_classroom_case_complete_lineage()
    """))


def downgrade() -> None:
    op.execute(sa.text(
        "DROP TRIGGER IF EXISTS trg_classroom_case_complete_lineage "
        "ON evidence.evidence_cases"
    ))
    op.execute(sa.text(
        "DROP FUNCTION IF EXISTS evidence.guard_classroom_case_complete_lineage()"
    ))
    op.drop_table("classroom_final_evidence_review_mandates", schema="evidence")
