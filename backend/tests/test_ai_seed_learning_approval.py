from dataclasses import fields
from pathlib import Path
from uuid import UUID

from app.ai_control_plane.seed_learning import (
    APPROVED_INPUT_EVENT,
    ApproveDecisionSeedLearning,
    load_decision_seed_artifact,
    seed_approval_aggregate_id,
)
from app.main import app


def test_runtime_seed_matches_documented_seed_exactly() -> None:
    runtime = Path(
        "app/ai_control_plane/seeds/decision-making-v1.jsonl"
    ).read_bytes()
    documented = Path(
        "../docs/ai/seed/decision-making-v1.jsonl"
    ).read_bytes()

    assert runtime == documented


def test_decision_seed_artifact_is_valid_source_linked_synthetic_data() -> None:
    artifact = load_decision_seed_artifact()

    assert artifact.key == "decision-making-v1"
    assert artifact.source_version == "1"
    assert artifact.record_count == 24
    assert len(artifact.source_payload_digest) == 64
    assert artifact.dataset_name == "parcham-decision-making"
    assert artifact.purpose == "MODEL_TRAINING"
    assert artifact.source_type == "CURATED_SYNTHETIC_SEED"
    assert artifact.data_classification == "INTERNAL"


def test_seed_learning_command_does_not_accept_arbitrary_dataset_or_source() -> None:
    names = {field.name for field in fields(ApproveDecisionSeedLearning)}

    assert names == {
        "organization_context_id",
        "reviewer_id",
        "expected_source_payload_digest",
        "approval_reference",
        "trace_id",
    }
    for forbidden in (
        "dataset_name",
        "purpose",
        "source_reference",
        "source_type",
        "source_payload",
        "records",
        "content",
        "actor_type",
    ):
        assert forbidden not in names


def test_seed_approval_identity_is_deterministic_and_tenant_scoped() -> None:
    first_org = UUID("10000000-0000-0000-0000-000000000001")
    second_org = UUID("10000000-0000-0000-0000-000000000002")

    assert seed_approval_aggregate_id(
        first_org
    ) == seed_approval_aggregate_id(first_org)
    assert seed_approval_aggregate_id(
        first_org
    ) != seed_approval_aggregate_id(second_org)


def test_seed_bridge_emits_existing_governed_learning_approval_event_only() -> None:
    source = Path(
        "app/ai_control_plane/seed_learning.py"
    ).read_text()

    assert APPROVED_INPUT_EVENT == "ai.learning_input_approved.v1"
    assert 'actor={"type": "PERSON"' in source
    assert "record_event(db, envelope)" in source
    assert "pg_advisory_xact_lock" in source
    assert "expected_source_payload_digest" in source
    assert "AI_SEED_DIGEST_MISMATCH" in source
    assert "AI_SEED_LEARNING_APPROVAL_CONFLICT" in source

    for forbidden in (
        "ingest_approved_learning_input",
        "AIDataset(",
        "AIDatasetVersion(",
        "AIDatasetItem(",
        "AITrainingRun(",
        "train(",
        "runtime_activation",
    ):
        assert forbidden not in source


def test_seed_learning_http_contract_is_admin_only_and_digest_pinned() -> None:
    paths = app.openapi()["paths"]
    preview = "/api/v1/admin/ai/seed-learning/decision-making-v1"
    approve = (
        "/api/v1/admin/ai/seed-learning/"
        "decision-making-v1/approve"
    )

    assert preview in paths
    assert set(paths[preview]) == {"get"}
    assert approve in paths
    assert set(paths[approve]) == {"post"}

    schemas = app.openapi()["components"]["schemas"]
    request = schemas["SeedLearningApprovalRequest"]
    assert set(request["required"]) == {
        "expected_source_payload_digest",
        "approval_reference",
    }

    source = Path("app/ai_governance_api.py").read_text()
    seed_routes = source.split(
        '@router.get(\n    "/seed-learning/decision-making-v1"',
        1,
    )[1]
    assert 'require_role("ACADEMY_ADMIN")' in seed_routes
    assert "actor.person_id" in seed_routes
    assert "await db.commit()" in seed_routes


def test_seed_approval_does_not_start_training_or_activate_runtime() -> None:
    source = (
        Path("app/ai_control_plane/seed_learning.py").read_text()
        + Path("app/ai_governance_api.py").read_text()
    ).lower()

    for forbidden in (
        "start_training",
        "request_training",
        "run_training",
        "activate_runtime",
        "production_route",
        "current_model =",
        "openai",
        "anthropic",
    ):
        assert forbidden not in source
