from __future__ import annotations

import asyncio
from dataclasses import asdict
from uuid import UUID

from app.ai_control_plane.read_models import load_ai_governance_read
from app.db import SessionFactory

ORGANIZATION_CONTEXT_ID = UUID(
    "30000000-0000-0000-0000-000000000001"
)


async def main() -> None:
    async with SessionFactory() as db:
        read = await load_ai_governance_read(
            db,
            organization_context_id=ORGANIZATION_CONTEXT_ID,
        )

    if not read.dataset_versions:
        raise RuntimeError("AI Governance read model has no Dataset Versions.")
    if not read.training_runs:
        raise RuntimeError("AI Governance read model has no Training Runs.")
    if not read.model_versions:
        raise RuntimeError("AI Governance read model has no Model Versions.")
    if not read.evaluation_runs:
        raise RuntimeError("AI Governance read model has no Evaluation Runs.")
    if not read.promotion_decisions:
        raise RuntimeError("AI Governance read model has no Human Promotion Decisions.")

    training_by_id = {item.id: item for item in read.training_runs}
    model_by_id = {item.id: item for item in read.model_versions}
    evaluation_by_id = {item.id: item for item in read.evaluation_runs}

    for model in read.model_versions:
        training = training_by_id.get(model.training_run_id)
        if training is None:
            raise RuntimeError("Model Version lost Training Run lineage.")
        if training.dataset_version_id != model.dataset_version_id:
            raise RuntimeError("Model Version Dataset lineage mismatch.")

    for evaluation in read.evaluation_runs:
        if evaluation.model_version_id not in model_by_id:
            raise RuntimeError("Evaluation lost Model Version lineage.")
        if evaluation.state == "SUCCEEDED" and evaluation.result_digest is None:
            raise RuntimeError(
                "SUCCEEDED Evaluation is missing immutable result evidence."
            )

    for decision in read.promotion_decisions:
        evaluation = evaluation_by_id.get(decision.evaluation_run_id)
        if evaluation is None:
            raise RuntimeError("Promotion Decision lost Evaluation lineage.")
        if evaluation.model_version_id != decision.model_version_id:
            raise RuntimeError("Promotion Decision Model lineage mismatch.")
        if evaluation.state != "SUCCEEDED":
            raise RuntimeError(
                "Promotion Decision references a non-SUCCEEDED Evaluation."
            )

    serialized = str(asdict(read)).lower()
    for forbidden in (
        "artifact_reference",
        "metrics_artifact_reference",
        "provider_token",
        "api_key",
        "endpoint_url",
        "credential",
        "secret",
    ):
        if forbidden in serialized:
            raise RuntimeError(
                f"Admin AI Governance read model exposes forbidden field: {forbidden}"
            )

    print("admin_ai_governance_tenant_scope=PASS")
    print("dataset_to_training_lineage=PASS")
    print("training_to_model_lineage=PASS")
    print("model_to_evaluation_lineage=PASS")
    print("evaluation_to_human_promotion_lineage=PASS")
    print("secret_provider_surface=ABSENT")
    print("runtime_activation_controls=NOT_IMPLEMENTED")


if __name__ == "__main__":
    asyncio.run(main())
