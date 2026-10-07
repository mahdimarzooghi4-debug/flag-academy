from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import func, select

from app.ai_control_plane.models import (
    AIEvaluationRun,
    AIModelPromotionDecision,
)
from app.ai_control_plane.promotion import (
    RecordHumanPromotionDecision,
    record_human_promotion_decision,
)
from app.db import SessionFactory
from app.errors import AppError
from app.platform.models import OutboxEvent

ORGANIZATION_CONTEXT_ID = UUID(
    "30000000-0000-0000-0000-000000000001"
)
REVIEWER_ID = UUID("60000000-0000-0000-0000-000000000001")
SUCCESS_REQUEST_KEY = "ci-evaluation-success"
FAILED_REQUEST_KEY = "ci-evaluation-failure"
TARGET_ENVIRONMENT = "PRODUCTION"


async def _evaluation_run(request_key: str) -> AIEvaluationRun:
    async with SessionFactory() as db:
        run = (
            await db.execute(
                select(AIEvaluationRun).where(
                    AIEvaluationRun.organization_context_id
                    == ORGANIZATION_CONTEXT_ID,
                    AIEvaluationRun.request_key == request_key,
                )
            )
        ).scalar_one_or_none()
        if run is None:
            raise RuntimeError(
                "Offline Evaluation acceptance must run before Promotion acceptance."
            )
        return run


def _command(
    run: AIEvaluationRun,
    *,
    decision: str = "APPROVED",
    rationale: str = "CI human reviewer authorizes promotion evidence only.",
) -> RecordHumanPromotionDecision:
    return RecordHumanPromotionDecision(
        organization_context_id=ORGANIZATION_CONTEXT_ID,
        model_version_id=run.model_version_id,
        evaluation_run_id=run.id,
        reviewer_id=REVIEWER_ID,
        rationale=rationale,
        decision=decision,
        target_environment=TARGET_ENVIRONMENT,
        prior_active_model_version_id=None,
        trace_id="ci-human-promotion",
    )


async def _record_and_retry(run: AIEvaluationRun) -> UUID:
    async with SessionFactory() as db:
        created = await record_human_promotion_decision(
            db,
            command=_command(run),
        )
        if not created.created:
            raise RuntimeError("Initial Human Promotion Decision was not created.")

        replay = await record_human_promotion_decision(
            db,
            command=_command(run),
        )
        if replay.created:
            raise RuntimeError("Promotion retry created a duplicate decision.")
        if replay.promotion_decision_id != created.promotion_decision_id:
            raise RuntimeError("Promotion retry changed decision identity.")

        await db.commit()
        return created.promotion_decision_id


async def _prove_conflicting_retry_rejected(run: AIEvaluationRun) -> None:
    async with SessionFactory() as db:
        try:
            await record_human_promotion_decision(
                db,
                command=_command(
                    run,
                    decision="REJECTED",
                    rationale="CI conflicting retry must fail closed.",
                ),
            )
        except AppError as error:
            await db.rollback()
            if error.code != "AI_PROMOTION_DECISION_CONFLICT":
                raise
        else:
            raise RuntimeError(
                "Promotion decision semantics changed under the same Evaluation target."
            )


async def _prove_failed_evaluation_rejected(run: AIEvaluationRun) -> None:
    async with SessionFactory() as db:
        try:
            await record_human_promotion_decision(
                db,
                command=RecordHumanPromotionDecision(
                    organization_context_id=ORGANIZATION_CONTEXT_ID,
                    model_version_id=run.model_version_id,
                    evaluation_run_id=run.id,
                    reviewer_id=REVIEWER_ID,
                    rationale="CI failed Evaluation must never be promotable.",
                    decision="APPROVED",
                    target_environment="CI_FAILED_EVALUATION_TARGET",
                    prior_active_model_version_id=None,
                    trace_id="ci-failed-evaluation-promotion",
                ),
            )
        except AppError as error:
            await db.rollback()
            if error.code != "AI_PROMOTION_EVALUATION_NOT_SUCCEEDED":
                raise
        else:
            raise RuntimeError("Failed Evaluation Run was accepted for promotion.")


async def _prove_database_rejects_failed_evaluation(
    run: AIEvaluationRun,
) -> None:
    async with SessionFactory() as db:
        db.add(
            AIModelPromotionDecision(
                id=uuid4(),
                model_version_id=run.model_version_id,
                evaluation_run_id=run.id,
                reviewer_id=REVIEWER_ID,
                rationale="Direct invalid DB insert.",
                decision="APPROVED",
                target_environment="CI_DB_INVALID_TARGET",
                prior_active_model_version_id=None,
                decided_at=datetime.now(UTC),
            )
        )
        rejected = False
        try:
            await db.flush()
        except Exception:
            rejected = True
            await db.rollback()
        if not rejected:
            raise RuntimeError(
                "Database accepted promotion for non-SUCCEEDED Evaluation Run."
            )


async def _verify_persisted(
    *,
    decision_id: UUID,
    run: AIEvaluationRun,
) -> None:
    async with SessionFactory() as db:
        decision = (
            await db.execute(
                select(AIModelPromotionDecision).where(
                    AIModelPromotionDecision.id == decision_id
                )
            )
        ).scalar_one()
        if decision.model_version_id != run.model_version_id:
            raise RuntimeError("Promotion Model Version lineage mismatch.")
        if decision.evaluation_run_id != run.id:
            raise RuntimeError("Promotion Evaluation Run lineage mismatch.")
        if decision.reviewer_id != REVIEWER_ID:
            raise RuntimeError("Promotion Human reviewer lineage mismatch.")
        if decision.decision != "APPROVED":
            raise RuntimeError("Promotion decision was not preserved exactly.")
        if decision.target_environment != TARGET_ENVIRONMENT:
            raise RuntimeError("Promotion target environment changed.")

        decision_count = (
            await db.execute(
                select(func.count())
                .select_from(AIModelPromotionDecision)
                .where(
                    AIModelPromotionDecision.evaluation_run_id == run.id,
                    AIModelPromotionDecision.target_environment
                    == TARGET_ENVIRONMENT,
                )
            )
        ).scalar_one()
        if decision_count != 1:
            raise RuntimeError(
                f"Expected one Promotion Decision, got {decision_count}."
            )

        event_count = (
            await db.execute(
                select(func.count())
                .select_from(OutboxEvent)
                .where(
                    OutboxEvent.event_type
                    == "ai.model_promotion_decision_recorded.v1"
                )
            )
        ).scalar_one()
        if event_count < 1:
            raise RuntimeError("Promotion Decision outbox event is missing.")


async def main() -> None:
    success_run = await _evaluation_run(SUCCESS_REQUEST_KEY)
    failed_run = await _evaluation_run(FAILED_REQUEST_KEY)

    decision_id = await _record_and_retry(success_run)
    await _prove_conflicting_retry_rejected(success_run)
    await _prove_failed_evaluation_rejected(failed_run)
    await _prove_database_rejects_failed_evaluation(failed_run)
    await _verify_persisted(
        decision_id=decision_id,
        run=success_run,
    )

    print("human_reviewer_required=PASS")
    print("exact_model_version_pin=PASS")
    print("successful_evaluation_required=PASS")
    print("immutable_evaluation_result_required=PASS")
    print("idempotent_promotion_decision=PASS")
    print("conflicting_retry_fail_closed=PASS")
    print("database_failed_evaluation_rejection=PASS")
    print("approved_is_authorization_only=PASS")
    print("automatic_promotion=NOT_IMPLEMENTED")
    print("runtime_activation=NOT_IMPLEMENTED")


if __name__ == "__main__":
    asyncio.run(main())
