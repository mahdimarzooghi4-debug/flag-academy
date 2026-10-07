from dataclasses import fields
from pathlib import Path

from app.ai_control_plane.models import AIModelPromotionDecision
from app.ai_control_plane.promotion import RecordHumanPromotionDecision


def test_human_promotion_command_has_only_explicit_human_review_inputs() -> None:
    names = {field.name for field in fields(RecordHumanPromotionDecision)}
    assert names == {
        "organization_context_id",
        "model_version_id",
        "evaluation_run_id",
        "reviewer_id",
        "rationale",
        "decision",
        "target_environment",
        "prior_active_model_version_id",
        "trace_id",
    }
    for forbidden in (
        "actor_type",
        "system_actor",
        "automatic",
        "threshold",
        "score",
        "runtime",
    ):
        assert forbidden not in names


def test_promotion_decision_schema_pins_exact_review_lineage() -> None:
    columns = set(AIModelPromotionDecision.__table__.c.keys())
    assert {
        "model_version_id",
        "evaluation_run_id",
        "reviewer_id",
        "rationale",
        "decision",
        "target_environment",
        "prior_active_model_version_id",
        "decided_at",
    }.issubset(columns)


def test_promotion_requires_successful_evaluation_and_result() -> None:
    source = Path("app/ai_control_plane/promotion.py").read_text()

    assert "run.model_version_id != model_version_id" in source
    assert "EvaluationRunState.SUCCEEDED.value" in source
    assert "AIEvaluationResult.id" in source
    assert "AI_PROMOTION_EVALUATION_NOT_SUCCEEDED" in source
    assert "AI_PROMOTION_EVALUATION_RESULT_MISSING" in source


def test_promotion_is_human_only_and_records_person_actor() -> None:
    source = Path("app/ai_control_plane/promotion.py").read_text()

    assert 'actor={"type": "PERSON", "id": str(command.reviewer_id)}' in source
    assert "GovernanceActorType.SYSTEM" not in source
    assert "requested_by_type" not in source
    assert "actor_type" not in source


def test_promotion_is_idempotent_per_evaluation_and_target() -> None:
    source = Path("app/ai_control_plane/promotion.py").read_text()
    migration = Path(
        "alembic/versions/0024_ai_control_plane_foundation.py"
    ).read_text()

    assert "pg_advisory_xact_lock" in source
    assert "AI_PROMOTION_DECISION_CONFLICT" in source
    assert "existing.evaluation_run_id" not in source
    assert "existing.model_version_id == command.model_version_id" in source
    assert "existing.reviewer_id == command.reviewer_id" in source
    assert "existing.rationale == rationale" in source
    assert "existing.decision == decision_value" in source
    assert "uq_ai_model_promotion_eval_target" in migration
    assert "await db.commit()" not in source


def test_promotion_database_independently_enforces_lineage() -> None:
    migration = Path(
        "alembic/versions/0029_human_model_promotion_governance.py"
    ).read_text()

    assert "require_valid_human_promotion_lineage" in migration
    assert "promotion Model Version must match Evaluation Run" in migration
    assert "promotion requires SUCCEEDED Evaluation Run" in migration
    assert "promotion requires immutable Evaluation Result" in migration
    assert "prior active Model Version organization mismatch" in migration
    assert (
        "cannot harden Human Promotion with existing Promotion Decisions"
        in migration
    )


def test_approved_is_authorization_only_not_runtime_activation() -> None:
    source = Path("app/ai_control_plane/promotion.py").read_text().lower()

    assert '"authorization_only": true' in source
    assert '"runtime_activation": false' in source
    for forbidden in (
        "is_active =",
        "activated_at =",
        "activate_runtime(",
        "routing_policy",
        "production_route",
        "runtime_model",
        "current_model",
    ):
        assert forbidden not in source


def test_promotion_emits_single_auditable_decision_event() -> None:
    source = Path("app/ai_control_plane/promotion.py").read_text()

    assert "ai.model_promotion_decision_recorded.v1" in source
    assert "record_event(" in source
    assert '"reviewer_id": str(promotion.reviewer_id)' in source
    assert '"decision": promotion.decision' in source
    assert '"target_environment": promotion.target_environment' in source


def test_promotion_has_no_external_ai_provider_or_consequential_mutation() -> None:
    source = Path("app/ai_control_plane/promotion.py").read_text().lower()

    for forbidden in (
        "openai",
        "anthropic",
        "httpx",
        "requests.",
        "provider_token",
        "api_key",
        "endpoint_url",
        "gateassessment",
        "capabilityclaim",
        "responsibilityrecommendation",
        "appointment",
    ):
        assert forbidden not in source
