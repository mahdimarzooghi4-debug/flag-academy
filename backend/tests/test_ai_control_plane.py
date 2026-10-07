from pathlib import Path

from app.ai_control_plane.domain import (
    EvaluationRunState,
    GovernanceActorType,
    PromotionDecisionState,
    TrainingRunState,
)
from app.ai_control_plane.models import (
    AIDataset,
    AIDatasetItem,
    AIDatasetVersion,
    AIEvaluationResult,
    AIEvaluationRun,
    AIEvaluationRunState,
    AIModelArtifact,
    AIModelPromotionDecision,
    AIModelVersion,
    AITrainingRun,
    AITrainingRunState,
)


def test_ai_control_plane_vocabulary_is_exact() -> None:
    assert {item.value for item in TrainingRunState} == {
        "REQUESTED",
        "RUNNING",
        "SUCCEEDED",
        "FAILED",
    }
    assert {item.value for item in EvaluationRunState} == {
        "REQUESTED",
        "RUNNING",
        "SUCCEEDED",
        "FAILED",
    }
    assert {item.value for item in PromotionDecisionState} == {
        "APPROVED",
        "REJECTED",
    }
    assert {item.value for item in GovernanceActorType} == {
        "PERSON",
        "SYSTEM",
    }


def test_ai_control_plane_tables_are_context_local() -> None:
    tables = (
        AIDataset.__table__,
        AIDatasetVersion.__table__,
        AIDatasetItem.__table__,
        AITrainingRun.__table__,
        AITrainingRunState.__table__,
        AIModelArtifact.__table__,
        AIModelVersion.__table__,
        AIEvaluationRun.__table__,
        AIEvaluationRunState.__table__,
        AIEvaluationResult.__table__,
        AIModelPromotionDecision.__table__,
    )

    assert all(table.schema == "ai_control_plane" for table in tables)

    foreign_keys = {
        fk.target_fullname
        for table in tables
        for fk in table.foreign_keys
    }
    assert foreign_keys
    assert all(
        target.startswith("ai_control_plane.")
        for target in foreign_keys
    )


def test_ai_dataset_version_preserves_governed_provenance() -> None:
    version_columns = set(AIDatasetVersion.__table__.c.keys())
    item_columns = set(AIDatasetItem.__table__.c.keys())

    assert {
        "dataset_id",
        "version_number",
        "source_policy_key",
        "source_policy_version",
        "dataset_digest",
        "created_at",
    }.issubset(version_columns)

    assert {
        "dataset_version_id",
        "position",
        "source_type",
        "source_reference",
        "source_version",
        "approval_reference",
        "data_classification",
        "provenance_digest",
    }.issubset(item_columns)


def test_ai_training_pins_dataset_and_uses_append_only_state_history() -> None:
    run_columns = set(AITrainingRun.__table__.c.keys())
    state_columns = set(AITrainingRunState.__table__.c.keys())

    assert {
        "dataset_version_id",
        "model_family",
        "training_recipe_digest",
        "requested_by_type",
        "requested_by_reference",
        "requested_at",
    }.issubset(run_columns)
    assert {
        "training_run_id",
        "sequence",
        "state",
        "changed_at",
        "failure_code",
    }.issubset(state_columns)

    models_source = Path("app/ai_control_plane/models.py").read_text()
    assert "state: Mapped[str]" not in models_source.split(
        "class AITrainingRun(Base):", 1
    )[1].split("class AITrainingRunState(Base):", 1)[0]


def test_ai_model_version_has_internal_lineage_only() -> None:
    columns = set(AIModelVersion.__table__.c.keys())
    assert {
        "model_artifact_id",
        "training_run_id",
        "dataset_version_id",
        "model_family",
        "semantic_version",
        "created_at",
    }.issubset(columns)

    source = Path("app/ai_control_plane/models.py").read_text().lower()
    for forbidden in (
        "openai",
        "anthropic",
        "provider_token",
        "api_token",
        "api_key",
        "endpoint_url",
        "inference_endpoint",
        "training_endpoint",
        "base_url",
    ):
        assert forbidden not in source


def test_ai_evaluation_pins_exact_model_and_dataset_without_threshold() -> None:
    run_columns = set(AIEvaluationRun.__table__.c.keys())
    assert {
        "model_version_id",
        "evaluation_dataset_version_id",
        "evaluation_policy_key",
        "evaluation_policy_version",
        "requested_by_type",
        "requested_by_reference",
        "requested_at",
    }.issubset(run_columns)

    source = Path("app/ai_control_plane/models.py").read_text().lower()
    for forbidden in (
        "passing_score",
        "pass_threshold",
        "quality_threshold",
        "fairness_threshold",
        "weighted_score",
        "overall_score",
        "winner",
    ):
        assert forbidden not in source


def test_ai_promotion_is_human_audited_but_not_runtime_activation() -> None:
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

    source = Path("app/ai_control_plane/models.py").read_text()
    promotion_source = source.split(
        "class AIModelPromotionDecision(Base):", 1
    )[1]

    for forbidden in (
        "active_model",
        "runtime_activation",
        "activate_runtime",
        "production_route",
        "routing_policy",
    ):
        assert forbidden not in promotion_source.lower()


def test_ai_control_plane_records_are_database_immutable() -> None:
    migration_source = Path(
        "alembic/versions/0024_ai_control_plane_foundation.py"
    ).read_text()

    assert "reject_history_mutation" in migration_source
    assert "BEFORE UPDATE OR DELETE" in migration_source

    for table_name in (
        "datasets",
        "dataset_versions",
        "dataset_items",
        "training_runs",
        "training_run_states",
        "model_artifacts",
        "model_versions",
        "evaluation_runs",
        "evaluation_run_states",
        "evaluation_results",
        "model_promotion_decisions",
    ):
        assert f'"{table_name}"' in migration_source


def test_ai_control_plane_has_no_jsonb_or_cross_context_fk() -> None:
    migration_source = Path(
        "alembic/versions/0024_ai_control_plane_foundation.py"
    ).read_text()
    models_source = Path("app/ai_control_plane/models.py").read_text()

    assert "JSONB" not in migration_source
    assert "JSONB" not in models_source

    for forbidden in (
        "flag_profile.",
        "gate_assessment.",
        "patterns.",
        "evidence.",
        "mission_runtime.",
        "learning.",
    ):
        assert forbidden not in migration_source


def test_ai_foundation_adds_no_runtime_training_or_inference_api() -> None:
    root = Path("app/ai_control_plane")
    source = "\n".join(
        path.read_text()
        for path in sorted(root.glob("*.py"))
    ).lower()

    for forbidden in (
        "fastapi",
        "apirouter",
        "transformers",
        "torch",
        "peft",
        "safetensors",
        "generate(",
        "forward(",
        "optimizer",
        "backward(",
        "openai",
        "anthropic",
    ):
        assert forbidden not in source
