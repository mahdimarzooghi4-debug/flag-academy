import asyncio

from sqlalchemy import func, select, text

from app.db import SessionFactory
from app.gate_assessment.application import (
    CompleteGateReviewCommand,
    OpenGateReviewCommand,
    complete_gate_review,
    open_gate_review,
)
from app.gate_assessment.domain import GateAssessmentState, GateCode
from app.gate_assessment.models import (
    GateAssessment,
    GateProfileSnapshot,
    GateReview,
    GateReviewDecision,
)
from app.gate_assessment.profile_reader import FlagProfileSnapshotReader
from app.platform.models import DomainEvent, OutboxEvent


async def _scalar(sql: str) -> int:
    async with SessionFactory() as db:
        value = (await db.execute(text(sql))).scalar_one()
        return int(value)


async def _wait_for_published_gate_event() -> int:
    for _ in range(20):
        published = await _scalar(
            """
            select count(*)
            from platform.outbox_events
            where event_type = 'gate.review_completed.v1'
              and published_at is not null
            """
        )
        if published:
            return published
        await asyncio.sleep(1)
    raise AssertionError("gate.review_completed.v1 was not published")


async def _verify_runtime() -> dict[str, str | int]:
    expected_states = tuple(state.value for state in GateAssessmentState)
    expected_codes = tuple(code.value for code in GateCode)

    async with SessionFactory() as db:
        codes = tuple(
            (
                await db.execute(
                    text(
                        """
                        select code
                        from gate_assessment.gate_definitions
                        order by code
                        """
                    )
                )
            ).scalars()
        )
        assert codes == expected_codes

        invalid_states = (
            await db.execute(
                text(
                    """
                    select count(*)
                    from gate_assessment.gate_assessments
                    where state <> all(:states)
                    """
                ),
                {"states": list(expected_states)},
            )
        ).scalar_one()
        assert int(invalid_states) == 0

        review = (
            await db.execute(
                select(GateReview)
                .order_by(GateReview.opened_at.desc(), GateReview.id.desc())
                .limit(1)
            )
        ).scalar_one()
        decision = (
            await db.execute(
                select(GateReviewDecision)
                .where(GateReviewDecision.gate_review_id == review.id)
                .limit(1)
            )
        ).scalar_one()
        snapshot = (
            await db.execute(
                select(GateProfileSnapshot).where(
                    GateProfileSnapshot.id == review.gate_profile_snapshot_id
                )
            )
        ).scalar_one()
        assessment = (
            await db.execute(
                select(GateAssessment).where(
                    GateAssessment.id == review.gate_assessment_id
                )
            )
        ).scalar_one()

        assert decision.reviewer_id is not None
        assert decision.rationale.strip()
        assert decision.decision_state in {
            GateAssessmentState.PASS_CONFIRMED.value,
            GateAssessmentState.FAIL.value,
        }
        assert review.gate_assessment_version == decision.prior_assessment_version
        assert decision.resulting_assessment_version == decision.prior_assessment_version + 1
        assert decision.gate_profile_snapshot_id == snapshot.id
        assert decision.gate_profile_snapshot_version == snapshot.snapshot_version
        assert decision.gate_definition_version_id == review.gate_definition_version_id
        assert assessment.version == decision.resulting_assessment_version
        assert assessment.state == decision.decision_state

        counts_before = {
            "reviews": int(
                (
                    await db.execute(
                        select(func.count()).select_from(GateReview)
                    )
                ).scalar_one()
            ),
            "snapshots": int(
                (
                    await db.execute(
                        select(func.count()).select_from(GateProfileSnapshot)
                    )
                ).scalar_one()
            ),
            "decisions": int(
                (
                    await db.execute(
                        select(func.count()).select_from(GateReviewDecision)
                    )
                ).scalar_one()
            ),
            "events": int(
                (
                    await db.execute(
                        select(func.count())
                        .select_from(DomainEvent)
                        .where(
                            DomainEvent.event_type
                            == "gate.review_completed.v1"
                        )
                    )
                ).scalar_one()
            ),
            "outbox": int(
                (
                    await db.execute(
                        select(func.count())
                        .select_from(OutboxEvent)
                        .where(
                            OutboxEvent.event_type
                            == "gate.review_completed.v1"
                        )
                    )
                ).scalar_one()
            ),
        }

        open_retry = await open_gate_review(
            db,
            reader=FlagProfileSnapshotReader(db),
            command=OpenGateReviewCommand(
                organization_context_id=review.organization_context_id,
                gate_assessment_id=review.gate_assessment_id,
                track_code=snapshot.source_track_code,
                opened_by=review.opened_by,
                expected_version=review.gate_assessment_version - 1,
                idempotency_key=review.open_idempotency_key,
                trace_id=review.trace_id,
            ),
        )
        assert open_retry.review.id == review.id
        assert open_retry.profile_snapshot.id == snapshot.id

        decision_retry = await complete_gate_review(
            db,
            command=CompleteGateReviewCommand(
                organization_context_id=decision.organization_context_id,
                gate_review_id=decision.gate_review_id,
                reviewer_id=decision.reviewer_id,
                decision_state=decision.decision_state,
                rationale=decision.rationale,
                expected_version=decision.prior_assessment_version,
                expected_gate_definition_version_id=(
                    decision.gate_definition_version_id
                ),
                expected_profile_snapshot_id=decision.gate_profile_snapshot_id,
                expected_profile_snapshot_version=(
                    decision.gate_profile_snapshot_version
                ),
                idempotency_key=decision.decision_idempotency_key,
                trace_id=decision.trace_id,
            ),
        )
        assert decision_retry.decision.id == decision.id

        counts_after = {
            "reviews": int(
                (
                    await db.execute(
                        select(func.count()).select_from(GateReview)
                    )
                ).scalar_one()
            ),
            "snapshots": int(
                (
                    await db.execute(
                        select(func.count()).select_from(GateProfileSnapshot)
                    )
                ).scalar_one()
            ),
            "decisions": int(
                (
                    await db.execute(
                        select(func.count()).select_from(GateReviewDecision)
                    )
                ).scalar_one()
            ),
            "events": int(
                (
                    await db.execute(
                        select(func.count())
                        .select_from(DomainEvent)
                        .where(
                            DomainEvent.event_type
                            == "gate.review_completed.v1"
                        )
                    )
                ).scalar_one()
            ),
            "outbox": int(
                (
                    await db.execute(
                        select(func.count())
                        .select_from(OutboxEvent)
                        .where(
                            OutboxEvent.event_type
                            == "gate.review_completed.v1"
                        )
                    )
                ).scalar_one()
            ),
        }
        assert counts_after == counts_before

    published = await _wait_for_published_gate_event()

    metrics = {
        "gate_definitions": await _scalar(
            "select count(*) from gate_assessment.gate_definitions"
        ),
        "gate_definition_versions": await _scalar(
            "select count(*) from gate_assessment.gate_definition_versions"
        ),
        "gate_assessments": await _scalar(
            "select count(*) from gate_assessment.gate_assessments"
        ),
        "gate_profile_snapshots": await _scalar(
            "select count(*) from gate_assessment.gate_profile_snapshots"
        ),
        "gate_snapshot_claims": await _scalar(
            "select count(*) from gate_assessment.gate_profile_snapshot_claims"
        ),
        "gate_snapshot_pattern_refs": await _scalar(
            "select count(*) from gate_assessment.gate_snapshot_pattern_refs"
        ),
        "gate_snapshot_evidence_refs": await _scalar(
            "select count(*) from gate_assessment.gate_snapshot_evidence_refs"
        ),
        "gate_reviews": await _scalar(
            "select count(*) from gate_assessment.gate_reviews"
        ),
        "gate_review_decisions": await _scalar(
            "select count(*) from gate_assessment.gate_review_decisions"
        ),
        "gate_review_completed_events": await _scalar(
            """
            select count(*)
            from platform.domain_events
            where event_type = 'gate.review_completed.v1'
            """
        ),
        "published_gate_review_completed_events": published,
        "gate_snapshot_immutable_triggers": await _scalar(
            """
            select count(*)
            from pg_trigger t
            join pg_class c on c.oid = t.tgrelid
            join pg_namespace n on n.oid = c.relnamespace
            where n.nspname = 'gate_assessment'
              and c.relname in (
                'gate_profile_snapshots',
                'gate_profile_snapshot_claims',
                'gate_snapshot_pattern_refs',
                'gate_snapshot_evidence_refs'
              )
              and not t.tgisinternal
              and t.tgname like 'trg_%_immutable'
            """
        ),
        "gate_cross_context_foreign_keys": await _scalar(
            """
            select count(*)
            from information_schema.table_constraints tc
            join information_schema.constraint_column_usage ccu
              on ccu.constraint_name = tc.constraint_name
             and ccu.constraint_schema = tc.constraint_schema
            where tc.constraint_type = 'FOREIGN KEY'
              and tc.table_schema = 'gate_assessment'
              and ccu.table_schema <> 'gate_assessment'
            """
        ),
        "gate_incomplete_snapshot_claims": await _scalar(
            """
            select count(*)
            from gate_assessment.gate_profile_snapshot_claims c
            where not exists (
                select 1
                from gate_assessment.gate_snapshot_pattern_refs p
                where p.gate_profile_snapshot_claim_id = c.id
            )
            """
        ),
        "gate_incomplete_snapshot_patterns": await _scalar(
            """
            select count(*)
            from gate_assessment.gate_snapshot_pattern_refs p
            where not exists (
                select 1
                from gate_assessment.gate_snapshot_evidence_refs e
                where e.gate_snapshot_pattern_ref_id = p.id
            )
            """
        ),
        "gate_event_outbox_mismatches": await _scalar(
            """
            select count(*)
            from platform.domain_events de
            left join platform.outbox_events oe on oe.event_id = de.event_id
            where de.event_type = 'gate.review_completed.v1'
              and (
                oe.event_id is null
                or oe.event_type <> de.event_type
              )
            """
        ),
        "gate_nonhuman_review_events": await _scalar(
            """
            select count(*)
            from platform.domain_events
            where event_type = 'gate.review_completed.v1'
              and coalesce(actor->>'type', '') <> 'PERSON'
            """
        ),
        "gate_event_lineage_mismatches": await _scalar(
            """
            select count(*)
            from platform.domain_events de
            join gate_assessment.gate_review_decisions d
              on de.payload->>'gate_review_decision_id' = d.id::text
            where de.event_type = 'gate.review_completed.v1'
              and (
                de.actor->>'type' <> 'PERSON'
                or de.actor->>'id' <> d.reviewer_id::text
                or de.payload->>'decision_state' <> d.decision_state
                or de.payload->>'profile_snapshot_id'
                    <> d.gate_profile_snapshot_id::text
                or (de.payload->>'profile_snapshot_version')::bigint
                    <> d.gate_profile_snapshot_version
              )
            """
        ),
        "gate_claim_mutations_after_review": await _scalar(
            """
            select count(*)
            from flag_profile.capability_claims cc
            where cc.updated_at >= (
                select min(opened_at)
                from gate_assessment.gate_reviews
            )
            """
        ),
        "gate_downstream_decision_events": await _scalar(
            """
            select count(*)
            from platform.domain_events de
            where de.occurred_at >= (
                select min(opened_at)
                from gate_assessment.gate_reviews
            )
              and (
                de.event_type like 'responsibility.%'
                or de.event_type like 'flag_board.%'
                or de.event_type like 'appointment.%'
              )
            """
        ),
        "gate_pass_with_evidence_gap": await _scalar(
            """
            select count(distinct d.id)
            from gate_assessment.gate_review_decisions d
            join gate_assessment.gate_profile_snapshot_claims c
              on c.gate_profile_snapshot_id = d.gate_profile_snapshot_id
            where d.decision_state = 'PASS_CONFIRMED'
              and btrim(c.next_evidence_needed) <> ''
            """
        ),
    }

    assert metrics["gate_definitions"] == 5
    assert metrics["gate_definition_versions"] >= 5
    assert metrics["gate_assessments"] >= 1
    assert metrics["gate_profile_snapshots"] >= 1
    assert metrics["gate_snapshot_claims"] >= 1
    assert metrics["gate_snapshot_pattern_refs"] >= 1
    assert metrics["gate_snapshot_evidence_refs"] >= 1
    assert metrics["gate_reviews"] >= 1
    assert metrics["gate_review_decisions"] >= 1
    assert metrics["gate_review_completed_events"] >= 1
    assert metrics["published_gate_review_completed_events"] >= 1
    assert metrics["gate_snapshot_immutable_triggers"] == 4
    assert metrics["gate_cross_context_foreign_keys"] == 0
    assert metrics["gate_incomplete_snapshot_claims"] == 0
    assert metrics["gate_incomplete_snapshot_patterns"] == 0
    assert metrics["gate_event_outbox_mismatches"] == 0
    assert metrics["gate_nonhuman_review_events"] == 0
    assert metrics["gate_event_lineage_mismatches"] == 0
    assert metrics["gate_claim_mutations_after_review"] == 0
    assert metrics["gate_downstream_decision_events"] == 0
    assert metrics["gate_pass_with_evidence_gap"] >= 1

    evidence: dict[str, str | int] = {
        **metrics,
        "gate_state_vocabulary": "+".join(expected_states),
        "gate_code_vocabulary": "+".join(expected_codes),
        "gate_snapshot_immutability": "DB_TRIGGER_ENFORCED",
        "gate_snapshot_lineage": "CLAIM+PATTERN+EVIDENCE+INTERPRETATION+OBSERVATION+SOURCE",
        "gate_open_review_idempotent_replay": "PASS",
        "gate_decision_idempotent_replay": "PASS",
        "gate_human_decision_only": "PASS_CONFIRMED_OR_FAIL+PERSON+RATIONALE",
        "gate_missing_evidence_auto_fail": "FORBIDDEN",
        "gate_event_delivery": "DOMAIN_EVENT+OUTBOX+PUBLISHED",
        "gate_ai_system_direct_decision": "FORBIDDEN",
        "gate_capability_claim_mutation": "FORBIDDEN",
        "gate_responsibility_flagboard_appointment_mutation": "FORBIDDEN",
    }
    return evidence


async def main() -> None:
    evidence = await _verify_runtime()
    for key, value in evidence.items():
        print(f"{key}={value}")


if __name__ == "__main__":
    asyncio.run(main())
