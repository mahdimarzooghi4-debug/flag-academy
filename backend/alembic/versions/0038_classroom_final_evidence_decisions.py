"""Authorized human classroom Evidence review transitions and immutable decision history.

Revision ID: 0038
Revises: 0037
"""
import sqlalchemy as sa

from alembic import op

revision = "0038"
down_revision = "0037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # No guessed role/privilege can pass this DB barrier: a real issued mandate
    # plus an exact human EvidenceReview row is required for the transition.
    op.execute(sa.text("""
        CREATE OR REPLACE FUNCTION evidence.guard_classroom_case_transition()
        RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE
            required_review TEXT;
        BEGIN
            IF TG_OP = 'DELETE' THEN
                IF OLD.source_context = 'CLASSROOM_OBSERVATION' THEN
                    RAISE EXCEPTION 'Private classroom Evidence cannot be deleted';
                END IF;
                RETURN OLD;
            END IF;
            IF TG_OP = 'INSERT' THEN
                IF NEW.source_context = 'CLASSROOM_OBSERVATION'
                    AND (NEW.status <> 'DRAFT' OR NEW.version <> 1
                         OR NEW.candidate_visible IS DISTINCT FROM FALSE
                         OR NEW.accepted_at IS NOT NULL OR NEW.rejected_at IS NOT NULL)
                THEN
                    RAISE EXCEPTION 'Classroom Evidence must begin as private DRAFT v1';
                END IF;
                RETURN NEW;
            END IF;
            IF OLD.source_context <> 'CLASSROOM_OBSERVATION' THEN
                IF NEW.source_context = 'CLASSROOM_OBSERVATION' THEN
                    RAISE EXCEPTION 'Cannot relabel another Evidence source';
                END IF;
                RETURN NEW;
            END IF;
            IF NEW.source_context <> 'CLASSROOM_OBSERVATION'
                OR NEW.candidate_visible IS DISTINCT FROM FALSE
                OR NEW.version <> OLD.version + 1
                OR NEW.updated_at < OLD.updated_at
                OR (
                    (to_jsonb(NEW) - 'status' - 'version' - 'updated_at'
                     - 'accepted_at' - 'rejected_at')
                    IS DISTINCT FROM
                    (to_jsonb(OLD) - 'status' - 'version' - 'updated_at'
                     - 'accepted_at' - 'rejected_at')
                )
            THEN
                RAISE EXCEPTION 'Classroom Evidence lineage or version changed';
            END IF;

            IF OLD.status = 'DRAFT' AND NEW.status = 'SUBMITTED' THEN
                IF NEW.accepted_at IS NOT NULL OR NEW.rejected_at IS NOT NULL THEN
                    RAISE EXCEPTION 'Submitted classroom Evidence is not accepted';
                END IF;
                RETURN NEW;
            ELSIF OLD.status = 'SUBMITTED' AND NEW.status = 'UNDER_REVIEW' THEN
                required_review := 'REVIEW_STARTED';
                IF NEW.accepted_at IS NOT NULL OR NEW.rejected_at IS NOT NULL THEN
                    RAISE EXCEPTION 'Review start cannot decide Evidence';
                END IF;
            ELSIF OLD.status = 'UNDER_REVIEW' AND NEW.status = 'ACCEPTED' THEN
                required_review := 'ACCEPT';
                IF NEW.accepted_at IS NULL OR NEW.rejected_at IS NOT NULL
                    OR OLD.accepted_at IS NOT NULL OR OLD.rejected_at IS NOT NULL THEN
                    RAISE EXCEPTION 'Accepted Evidence timestamps invalid';
                END IF;
            ELSIF OLD.status = 'UNDER_REVIEW' AND NEW.status = 'REJECTED' THEN
                required_review := 'REJECT';
                IF NEW.rejected_at IS NULL OR NEW.accepted_at IS NOT NULL
                    OR OLD.accepted_at IS NOT NULL OR OLD.rejected_at IS NOT NULL THEN
                    RAISE EXCEPTION 'Rejected Evidence timestamps invalid';
                END IF;
            ELSE
                RAISE EXCEPTION 'Unsupported classroom Evidence state transition';
            END IF;

            IF NOT EXISTS (
                SELECT 1
                FROM evidence.classroom_final_evidence_review_mandates m
                JOIN evidence.classroom_final_evidence_mandate_revisions a
                  ON a.mandate_id = m.id AND a.action = 'ISSUE'
                 AND a.actor_person_id = m.issued_by_person_id
                JOIN evidence.evidence_reviews r
                  ON r.evidence_case_id = m.evidence_case_id
                 AND r.reviewer_id = m.reviewer_person_id
                 AND r.decision = required_review
                WHERE m.evidence_case_id = OLD.id
                  AND m.organization_context_id = OLD.organization_context_id
                  AND m.revoked_at IS NULL AND m.starts_at <= clock_timestamp()
                  AND clock_timestamp() < m.ends_at
                  AND r.created_at >= OLD.updated_at
                  AND r.created_at <= NEW.updated_at
            ) THEN
                RAISE EXCEPTION 'Live accountable final reviewer decision required';
            END IF;
            IF required_review IN ('ACCEPT', 'REJECT') AND NOT EXISTS (
                SELECT 1
                FROM evidence.evidence_reviews prior
                JOIN evidence.classroom_final_evidence_review_mandates m
                  ON m.evidence_case_id = prior.evidence_case_id
                 AND m.reviewer_person_id = prior.reviewer_id
                WHERE prior.evidence_case_id = OLD.id
                  AND prior.decision = 'REVIEW_STARTED'
            ) THEN
                RAISE EXCEPTION 'Independent Evidence review must have started';
            END IF;
            RETURN NEW;
        END;
        $$
    """))
    op.execute(sa.text("""
        CREATE OR REPLACE FUNCTION evidence.guard_classroom_case_complete_lineage()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF OLD.source_context = 'CLASSROOM_OBSERVATION' AND (
                (to_jsonb(NEW) - 'status' - 'version' - 'updated_at'
                 - 'accepted_at' - 'rejected_at')
                IS DISTINCT FROM
                (to_jsonb(OLD) - 'status' - 'version' - 'updated_at'
                 - 'accepted_at' - 'rejected_at')
            ) THEN
                RAISE EXCEPTION 'Classroom Evidence immutable fields changed';
            END IF;
            RETURN NEW;
        END;
        $$
    """))
    op.execute(sa.text("""
        CREATE FUNCTION evidence.reject_classroom_evidence_review_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM evidence.evidence_cases c
                WHERE c.id = OLD.evidence_case_id
                  AND c.source_context = 'CLASSROOM_OBSERVATION'
            ) THEN
                RAISE EXCEPTION 'Human classroom Evidence decisions are immutable';
            END IF;
            RETURN OLD;
        END;
        $$
    """))
    op.execute(sa.text("""
        CREATE TRIGGER trg_classroom_evidence_review_immutable
        BEFORE UPDATE OR DELETE ON evidence.evidence_reviews
        FOR EACH ROW EXECUTE FUNCTION evidence.reject_classroom_evidence_review_mutation()
    """))


def downgrade() -> None:
    # Downgrade restores stricter fail-closed barrier, never unrestricted review.
    op.execute(sa.text(
        "DROP TRIGGER IF EXISTS trg_classroom_evidence_review_immutable "
        "ON evidence.evidence_reviews"
    ))
    op.execute(sa.text(
        "DROP FUNCTION IF EXISTS evidence.reject_classroom_evidence_review_mutation()"
    ))
    # Recreate the historical 0035 blocker for all submitted cases.
    op.execute(sa.text("""
        CREATE OR REPLACE FUNCTION evidence.guard_classroom_case_transition()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                IF OLD.source_context = 'CLASSROOM_OBSERVATION' THEN
                    RAISE EXCEPTION 'Private classroom Evidence cannot be deleted';
                END IF;
                RETURN OLD;
            END IF;
            IF TG_OP = 'UPDATE' AND OLD.source_context = 'CLASSROOM_OBSERVATION' THEN
                IF OLD.status <> 'DRAFT' OR NEW.status <> 'SUBMITTED'
                    OR NEW.version <> OLD.version + 1 THEN
                    RAISE EXCEPTION 'Formal review disabled after downgrade';
                END IF;
            ELSIF TG_OP = 'UPDATE' AND NEW.source_context = 'CLASSROOM_OBSERVATION' THEN
                RAISE EXCEPTION 'Cannot relabel Evidence';
            END IF;
            IF NEW.source_context = 'CLASSROOM_OBSERVATION'
                AND (NEW.status NOT IN ('DRAFT', 'SUBMITTED')
                     OR NEW.candidate_visible IS DISTINCT FROM FALSE
                     OR NEW.accepted_at IS NOT NULL OR NEW.rejected_at IS NOT NULL) THEN
                RAISE EXCEPTION 'Final decisions disabled after downgrade';
            END IF;
            RETURN NEW;
        END;
        $$
    """))
    op.execute(sa.text("""
        CREATE OR REPLACE FUNCTION evidence.guard_classroom_case_complete_lineage()
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
