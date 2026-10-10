"""Case-scoped human mandate issuance/revocation governance.

Revision ID: 0037
Revises: 0036
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision = "0037"
down_revision = "0036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_final_evidence_mandate_case",
        "classroom_final_evidence_review_mandates",
        ["evidence_case_id"],
        schema="evidence",
    )
    uuid = postgresql.UUID(as_uuid=True)
    op.create_table(
        "classroom_final_evidence_mandate_revisions",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("mandate_id", uuid, nullable=False),
        sa.Column("organization_context_id", uuid, nullable=False),
        sa.Column("evidence_case_id", uuid, nullable=False),
        sa.Column("actor_person_id", uuid, nullable=False),
        sa.Column("reviewer_person_id", uuid, nullable=False),
        sa.Column("action", sa.String(16), nullable=False),
        sa.Column("expected_version", sa.BigInteger(), nullable=False),
        sa.Column("resulting_version", sa.BigInteger(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("idempotency_key", sa.String(160), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["mandate_id"], ["evidence.classroom_final_evidence_review_mandates.id"],
        ),
        sa.UniqueConstraint(
            "organization_context_id", "actor_person_id", "idempotency_key",
            name="uq_final_evidence_mandate_actor_key",
        ),
        sa.UniqueConstraint(
            "mandate_id", "resulting_version",
            name="uq_final_evidence_mandate_revision_version",
        ),
        sa.CheckConstraint("action IN ('ISSUE', 'REVOKE')",
                           name="ck_final_evidence_mandate_action"),
        sa.CheckConstraint("length(trim(reason)) > 0",
                           name="ck_final_evidence_mandate_reason"),
        schema="evidence",
    )
    op.execute(sa.text("""
        CREATE FUNCTION evidence.reject_final_mandate_revision_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          RAISE EXCEPTION 'Final Evidence mandate history is append only';
        END;
        $$
    """))
    op.execute(sa.text("""
        CREATE TRIGGER trg_final_mandate_revision_immutable
        BEFORE UPDATE OR DELETE ON evidence.classroom_final_evidence_mandate_revisions
        FOR EACH ROW EXECUTE FUNCTION evidence.reject_final_mandate_revision_mutation()
    """))


def downgrade() -> None:
    op.execute(sa.text(
        "DROP TRIGGER IF EXISTS trg_final_mandate_revision_immutable "
        "ON evidence.classroom_final_evidence_mandate_revisions"
    ))
    op.execute(sa.text(
        "DROP FUNCTION IF EXISTS evidence.reject_final_mandate_revision_mutation()"
    ))
    op.drop_table("classroom_final_evidence_mandate_revisions", schema="evidence")
    op.drop_constraint(
        "uq_final_evidence_mandate_case",
        "classroom_final_evidence_review_mandates",
        schema="evidence",
    )
