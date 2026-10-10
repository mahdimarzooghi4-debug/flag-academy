"""Fail-closed classroom Evidence decision and interpretation integrity barrier.

Revision ID: 0035
Revises: 0034
Create Date: 2026-10-10

No final reviewer appointment contract exists yet. This migration cannot be
interpreted as permission for ACCEPTED or downstream Profile/Gate changes.
"""
import sqlalchemy as sa

from alembic import op

revision = "0035"
down_revision = "0034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("""
        CREATE FUNCTION evidence.guard_classroom_case_transition()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                IF OLD.source_context = 'CLASSROOM_OBSERVATION' THEN
                    RAISE EXCEPTION 'Private classroom Evidence cannot be deleted';
                END IF;
                RETURN OLD;
            END IF;
            IF TG_OP = 'UPDATE' AND OLD.source_context = 'CLASSROOM_OBSERVATION' THEN
                IF NEW.source_context IS DISTINCT FROM OLD.source_context
                    OR NEW.source_observation_id IS DISTINCT FROM OLD.source_observation_id
                    OR NEW.organization_context_id IS DISTINCT FROM OLD.organization_context_id
                    OR NEW.subject_person_id IS DISTINCT FROM OLD.subject_person_id
                    OR NEW.provenance IS DISTINCT FROM OLD.provenance
                    OR NEW.observed_fact IS DISTINCT FROM OLD.observed_fact
                    OR NEW.observed_payload IS DISTINCT FROM OLD.observed_payload
                    OR NEW.occurred_at IS DISTINCT FROM OLD.occurred_at
                    OR NEW.source_reference IS DISTINCT FROM OLD.source_reference
                    OR NEW.integrity_state IS DISTINCT FROM OLD.integrity_state
                    OR NEW.candidate_visible_payload IS DISTINCT FROM OLD.candidate_visible_payload
                THEN
                    RAISE EXCEPTION 'Private classroom Evidence lineage is immutable';
                END IF;
                IF OLD.status = 'SUBMITTED' AND NEW IS DISTINCT FROM OLD THEN
                    RAISE EXCEPTION 'Formal classroom review policy is not approved';
                END IF;
                IF OLD.status <> 'DRAFT' OR NEW.status <> 'SUBMITTED'
                    OR NEW.version <> OLD.version + 1
                THEN
                    RAISE EXCEPTION 'Only private DRAFT to SUBMITTED is authorized';
                END IF;
            ELSIF NEW.source_context = 'CLASSROOM_OBSERVATION'
                AND TG_OP = 'UPDATE' THEN
                RAISE EXCEPTION 'Cannot relabel ordinary Evidence as classroom Evidence';
            END IF;
            IF NEW.source_context = 'CLASSROOM_OBSERVATION' THEN
                IF NEW.status NOT IN ('DRAFT', 'SUBMITTED')
                    OR NEW.candidate_visible IS DISTINCT FROM FALSE
                    OR NEW.accepted_at IS NOT NULL OR NEW.rejected_at IS NOT NULL
                THEN
                    RAISE EXCEPTION 'Classroom Evidence final decisions are disabled';
                END IF;
                IF TG_OP = 'INSERT' AND (NEW.status <> 'DRAFT' OR NEW.version <> 1) THEN
                    RAISE EXCEPTION 'Classroom Evidence must begin as DRAFT v1';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$
    """))
    op.execute(sa.text("""
        CREATE TRIGGER trg_classroom_case_decision_barrier
        BEFORE INSERT OR UPDATE OR DELETE ON evidence.evidence_cases
        FOR EACH ROW EXECUTE FUNCTION evidence.guard_classroom_case_transition()
    """))
    op.execute(sa.text("""
        CREATE FUNCTION evidence.guard_classroom_interpretation_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM evidence.evidence_cases c
                WHERE c.id = OLD.evidence_case_id
                    AND c.source_context = 'CLASSROOM_OBSERVATION'
            ) THEN
                RAISE EXCEPTION 'Submitted classroom interpretation is immutable';
            END IF;
            RETURN OLD;
        END;
        $$
    """))
    op.execute(sa.text("""
        CREATE TRIGGER trg_classroom_interpretation_immutable
        BEFORE UPDATE OR DELETE ON evidence.evidence_interpretations
        FOR EACH ROW EXECUTE FUNCTION evidence.guard_classroom_interpretation_mutation()
    """))
    op.execute(sa.text("""
        CREATE FUNCTION evidence.guard_classroom_link_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM evidence.evidence_interpretations i
                JOIN evidence.evidence_cases c ON c.id = i.evidence_case_id
                WHERE i.id = OLD.interpretation_id
                    AND c.source_context = 'CLASSROOM_OBSERVATION'
            ) THEN
                RAISE EXCEPTION 'Classroom interpretation links are immutable';
            END IF;
            RETURN OLD;
        END;
        $$
    """))
    op.execute(sa.text("""
        CREATE TRIGGER trg_classroom_link_immutable
        BEFORE UPDATE OR DELETE ON evidence.evidence_links
        FOR EACH ROW EXECUTE FUNCTION evidence.guard_classroom_link_mutation()
    """))


def downgrade() -> None:
    for trigger, table in (
        ("trg_classroom_link_immutable", "evidence_links"),
        ("trg_classroom_interpretation_immutable", "evidence_interpretations"),
        ("trg_classroom_case_decision_barrier", "evidence_cases"),
    ):
        op.execute(sa.text(
            f"DROP TRIGGER IF EXISTS {trigger} ON evidence.{table}"
        ))
    for function in (
        "guard_classroom_link_mutation",
        "guard_classroom_interpretation_mutation",
        "guard_classroom_case_transition",
    ):
        op.execute(sa.text(f"DROP FUNCTION IF EXISTS evidence.{function}()"))
