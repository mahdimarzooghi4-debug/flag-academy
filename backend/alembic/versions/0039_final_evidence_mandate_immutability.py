"""Final Evidence mandates cannot be rewritten, deleted or un-revoked.

Revision ID: 0039
Revises: 0038

An approved Academy Admin can issue/revoke through Evidence domain commands.
PostgreSQL enforces irreversible revocation and immutable reviewer, scope,
issuer and timestamps even if an SQL writer bypasses the API.
"""
import sqlalchemy as sa

from alembic import op

revision = "0039"
down_revision = "0038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("""
        CREATE FUNCTION evidence.guard_final_mandate_lifecycle()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'Final Evidence mandates cannot be deleted';
            END IF;
            IF OLD.revoked_at IS NOT NULL
                OR NEW.revoked_at IS NULL
                OR NEW.revoked_at < OLD.issued_at
                OR NEW.version <> OLD.version + 1
                OR (to_jsonb(NEW) - 'version' - 'revoked_at')
                   IS DISTINCT FROM
                   (to_jsonb(OLD) - 'version' - 'revoked_at')
            THEN
                RAISE EXCEPTION 'Final Evidence mandate identity and revocation are immutable';
            END IF;
            RETURN NEW;
        END;
        $$
    """))
    op.execute(sa.text("""
        CREATE TRIGGER trg_final_mandate_lifecycle
        BEFORE UPDATE OR DELETE ON evidence.classroom_final_evidence_review_mandates
        FOR EACH ROW EXECUTE FUNCTION evidence.guard_final_mandate_lifecycle()
    """))


def downgrade() -> None:
    op.execute(sa.text(
        "DROP TRIGGER IF EXISTS trg_final_mandate_lifecycle "
        "ON evidence.classroom_final_evidence_review_mandates"
    ))
    op.execute(sa.text(
        "DROP FUNCTION IF EXISTS evidence.guard_final_mandate_lifecycle()"
    ))
