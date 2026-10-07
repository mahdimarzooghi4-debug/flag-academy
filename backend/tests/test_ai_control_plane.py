from dataclasses import fields
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest

from app.ai_control_plane import consumer as ai_consumer
from app.ai_control_plane.dataset_builder import (
    ApprovedLearningInput,
    approval_provenance_digest,
    dataset_version_digest,
)
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
    AILearningSourceApproval,
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
        AILearningSourceApproval.__table__,
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
        "parent_dataset_version_id",
        "version_number",
        "source_policy_key",
        "source_policy_version",
        "dataset_digest",
        "created_at",
    }.issubset(version_columns)

    assert {
        "dataset_version_id",
        "learning_source_approval_id",
        "position",
        "source_type",
        "source_reference",
        "source_version",
        "approval_reference",
        "data_classification",
        "source_payload_digest",
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
        "is_active",
        "activated_at",
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



def _approved_input(
    *,
    approval_reference: str = "approval-001",
    approved_by_reference: str = "reviewer-001",
    approved_at: datetime | None = None,
) -> ApprovedLearningInput:
    return ApprovedLearningInput(
        organization_context_id=UUID(
            "00000000-0000-0000-0000-000000000001"
        ),
        dataset_name="parcham-reviewed-learning",
        purpose="MODEL_TRAINING",
        source_policy_key="ai-learning-policy",
        source_policy_version="v1",
        source_type="REVIEWED_PATTERN",
        source_reference="pattern:123",
        source_version="7",
        source_payload_digest="a" * 64,
        approval_reference=approval_reference,
        approval_event_id=UUID(
            "40000000-0000-0000-0000-000000000001"
        ),
        data_classification="CONFIDENTIAL",
        approved_by_type="PERSON",
        approved_by_reference=approved_by_reference,
        approved_at=approved_at
        or datetime(2026, 10, 7, 10, 0, tzinfo=UTC),
        trace_id="trace-ai-dataset-001",
    )


def test_ai_dataset_root_is_tenant_scoped() -> None:
    assert "organization_context_id" in AIDataset.__table__.c
    source = Path("app/ai_control_plane/models.py").read_text()
    assert 'name="uq_ai_dataset_scope_name_purpose"' in source


def test_ai_learning_approval_is_explicit_and_immutable_lineage() -> None:
    columns = set(AILearningSourceApproval.__table__.c.keys())
    assert {
        "dataset_id",
        "source_policy_key",
        "source_policy_version",
        "source_type",
        "source_reference",
        "source_version",
        "source_payload_digest",
        "approval_reference",
        "data_classification",
        "provenance_digest",
        "approved_by_type",
        "approved_by_reference",
        "approved_at",
        "created_at",
    }.issubset(columns)

    migration_source = Path(
        "alembic/versions/0025_governed_ai_dataset_builder.py"
    ).read_text()
    assert "learning_source_approvals" in migration_source
    assert "trg_learning_source_approvals_immutable" in migration_source
    assert "BEFORE UPDATE OR DELETE" in migration_source


def test_ai_dataset_builder_input_has_no_raw_payload_or_manual_record_list() -> None:
    names = {field.name for field in fields(ApprovedLearningInput)}
    assert names == {
        "organization_context_id",
        "dataset_name",
        "purpose",
        "source_policy_key",
        "source_policy_version",
        "source_type",
        "source_reference",
        "source_version",
        "source_payload_digest",
        "approval_reference",
        "approval_event_id",
        "data_classification",
        "approved_by_type",
        "approved_by_reference",
        "approved_at",
        "trace_id",
    }
    assert "payload" not in names
    assert "content" not in names
    assert "record_ids" not in names


def test_ai_dataset_provenance_digest_is_deterministic_and_deduplicates_reapproval() -> None:
    first = _approved_input()
    second = _approved_input(
        approval_reference="approval-replayed-under-new-reference",
        approved_by_reference="reviewer-002",
        approved_at=first.approved_at + timedelta(minutes=5),
    )

    assert approval_provenance_digest(first) == approval_provenance_digest(
        second
    )


def test_ai_dataset_version_digest_pins_parent_chain() -> None:
    organization_context_id = UUID(
        "00000000-0000-0000-0000-000000000001"
    )
    first = dataset_version_digest(
        organization_context_id=organization_context_id,
        dataset_name="parcham-reviewed-learning",
        purpose="MODEL_TRAINING",
        parent_dataset_digest=None,
        provenance_digest="b" * 64,
    )
    second = dataset_version_digest(
        organization_context_id=organization_context_id,
        dataset_name="parcham-reviewed-learning",
        purpose="MODEL_TRAINING",
        parent_dataset_digest=first,
        provenance_digest="c" * 64,
    )

    assert first != second
    assert len(first) == 64
    assert len(second) == 64


def test_ai_dataset_builder_is_multi_replica_serialized_and_caller_transactional() -> None:
    source = Path(
        "app/ai_control_plane/dataset_builder.py"
    ).read_text()
    ingest_source = source.split(
        "async def ingest_approved_learning_input", 1
    )[1]

    assert "pg_advisory_xact_lock" in ingest_source
    assert "await db.commit()" not in ingest_source
    assert 'event_type="ai.dataset_version_created.v1"' in ingest_source
    assert "causation_id=normalized.approval_event_id" in ingest_source
    assert "record_event(" in ingest_source


def test_ai_dataset_builder_has_no_operational_domain_imports() -> None:
    source = Path(
        "app/ai_control_plane/dataset_builder.py"
    ).read_text()

    for forbidden in (
        "app.evidence",
        "app.patterns",
        "app.flag_profile",
        "app.gate_assessment",
        "CapabilityClaim",
        "BehaviourPattern",
        "EvidenceCase",
        "GateAssessment",
    ):
        assert forbidden not in source


@pytest.mark.asyncio
async def test_ai_dataset_consumer_ignores_review_events_without_ai_learning_approval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[ApprovedLearningInput] = []

    async def fake_ingest(db, *, command: ApprovedLearningInput):
        calls.append(command)
        return None

    monkeypatch.setattr(
        ai_consumer,
        "ingest_approved_learning_input",
        fake_ingest,
    )

    from app.platform.events import new_event

    for event_type in (
        "evidence.accepted.v1",
        "pattern.updated.v1",
        "profile.claim_changed.v1",
        "gate.review_completed.v1",
    ):
        envelope = new_event(
            event_type=event_type,
            aggregate_type="Any",
            aggregate_id=UUID(
                "10000000-0000-0000-0000-000000000001"
            ),
            aggregate_version=1,
            actor={"type": "PERSON", "id": "reviewer"},
            organization_context_id=UUID(
                "00000000-0000-0000-0000-000000000001"
            ),
            data_classification="CONFIDENTIAL",
            payload={},
            trace_id="trace-ignore",
        )
        await ai_consumer.apply_event(envelope, object())

    assert calls == []


@pytest.mark.asyncio
async def test_ai_dataset_consumer_accepts_only_explicit_learning_approval_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[ApprovedLearningInput] = []

    async def fake_ingest(db, *, command: ApprovedLearningInput):
        calls.append(command)
        return None

    monkeypatch.setattr(
        ai_consumer,
        "ingest_approved_learning_input",
        fake_ingest,
    )

    from app.platform.events import new_event

    organization_context_id = UUID(
        "00000000-0000-0000-0000-000000000001"
    )
    envelope = new_event(
        event_type="ai.learning_input_approved.v1",
        aggregate_type="AILearningApproval",
        aggregate_id=UUID(
            "20000000-0000-0000-0000-000000000001"
        ),
        aggregate_version=1,
        actor={"type": "PERSON", "id": "reviewer-001"},
        organization_context_id=organization_context_id,
        data_classification="CONFIDENTIAL",
        payload={
            "dataset_name": "parcham-reviewed-learning",
            "purpose": "MODEL_TRAINING",
            "source_policy_key": "ai-learning-policy",
            "source_policy_version": "v1",
            "source_type": "REVIEWED_PATTERN",
            "source_reference": "pattern:123",
            "source_version": "7",
            "source_payload_digest": "a" * 64,
            "approval_reference": "approval-001",
        },
        trace_id="trace-approved",
    )

    await ai_consumer.apply_event(envelope, object())

    assert len(calls) == 1
    command = calls[0]
    assert command.organization_context_id == organization_context_id
    assert command.approval_reference == "approval-001"
    assert command.approval_event_id == envelope.event_id
    assert command.approved_by_type == "PERSON"
    assert command.approved_by_reference == "reviewer-001"
    assert command.approved_at == envelope.occurred_at


def test_ai_dataset_consumer_uses_explicit_subject_only() -> None:
    source = Path("app/ai_control_plane/consumer.py").read_text()

    assert 'APPROVED_INPUT_EVENT = "ai.learning_input_approved.v1"' in source
    assert '"parcham.events.ai.learning_input_approved.v1"' in source
    for forbidden in (
        "parcham.events.evidence.",
        "parcham.events.pattern.",
        "parcham.events.profile.",
        "parcham.events.gate.",
    ):
        assert forbidden not in source


def test_governed_dataset_builder_migration_preserves_local_fk_boundary() -> None:
    source = Path(
        "alembic/versions/0025_governed_ai_dataset_builder.py"
    ).read_text()

    for forbidden in (
        "evidence.",
        "patterns.",
        "flag_profile.",
        "gate_assessment.",
        "learning.",
        "mission_runtime.",
    ):
        assert forbidden not in source

    assert "parent_dataset_version_id" in source
    assert "learning_source_approval_id" in source
    assert "source_payload_digest" in source
    assert "uq_ai_dataset_scope_name_purpose" in source
