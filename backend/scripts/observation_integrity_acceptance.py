"""CI-only real PostgreSQL invariants for Classroom Observation.

Runs after the live OIDC browser test: verifies one Observation and one event,
immutability at the DB engine, and that private note text is absent from Outbox.
"""
from __future__ import annotations

import asyncio
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.exc import DBAPIError

from app.academy.models import ClassAssessorObservation
from app.db import SessionFactory, engine
from app.evidence.contracts import load_accepted_evidence_snapshots
from app.evidence.models import (
    ClassroomFinalEvidenceMandateRevision,
    ClassroomFinalEvidenceReviewMandate,
    ClassroomObservationSourceReview,
    EvidenceCase,
    EvidenceInterpretation,
    EvidenceLink,
    EvidenceReview,
)
from app.platform.models import DomainEvent, OutboxEvent

ORG_ID = UUID("00000000-0000-0000-0000-000000000001")
CLASS_ID = UUID("00000000-0000-0000-0000-000000000220")
SESSION_ID = UUID("00000000-0000-0000-0000-000000000243")
ASSESSOR_ID = UUID("00000000-0000-0000-0000-000000000104")
REVIEWER_ID = UUID("00000000-0000-0000-0000-000000000105")


async def main() -> None:
    async with SessionFactory() as db:
        items = (
            await db.execute(
                select(ClassAssessorObservation).where(
                    ClassAssessorObservation.organization_context_id == ORG_ID,
                    ClassAssessorObservation.class_offering_id == CLASS_ID,
                    ClassAssessorObservation.session_id == SESSION_ID,
                    ClassAssessorObservation.observer_person_id == ASSESSOR_ID,
                    ClassAssessorObservation.observed_fact
                    == "CI factual classroom observation: learner separated evidence from interpretation.",
                )
            )
        ).scalars().all()
        assert len(items) == 1, "Concurrent requests must produce exactly one source row"
        item = items[0]
        assert item.recorded_at >= item.observed_at
        review_rows = (
            await db.execute(select(ClassroomObservationSourceReview).where(
                ClassroomObservationSourceReview.organization_context_id == ORG_ID,
                ClassroomObservationSourceReview.source_observation_id == item.id,
            ))
        ).scalars().all()
        assert len(review_rows) == 1, "Concurrent reviewers must produce one decision"
        review = review_rows[0]
        assert review.reviewer_person_id == REVIEWER_ID
        assert review.observer_person_id == ASSESSOR_ID
        assert review.decision == "VERIFIED"
        assert review.source_sha256 and len(review.source_sha256) == 64
        cases = (
            await db.execute(select(EvidenceCase).where(
                EvidenceCase.source_observation_id == item.id,
                EvidenceCase.organization_context_id == ORG_ID,
            ))
        ).scalars().all()
        assert len(cases) == 1, "Explicit concurrent human Draft must create exactly one case"
        draft = cases[0]
        assert draft.source_context == "CLASSROOM_OBSERVATION"
        assert draft.status == "ACCEPTED"
        assert draft.version == 4
        assert draft.integrity_state == "SOURCE_REVIEWED"
        assert draft.candidate_visible is False
        assert draft.source_runtime_event_id is None
        assert draft.provenance["source_review_id"] == str(review.id)
        assert draft.provenance["source_sha256"] == review.source_sha256
        assert draft.provenance["created_by_person_id"] == str(REVIEWER_ID)
        assert draft.observed_fact == item.observed_fact
        assert draft.candidate_visible_payload == {}
        final_reviews = (await db.execute(select(EvidenceReview).where(
            EvidenceReview.evidence_case_id == draft.id,
        ).order_by(EvidenceReview.created_at, EvidenceReview.id))).scalars().all()
        assert len(final_reviews) == 2
        assert {x.decision for x in final_reviews} == {"REVIEW_STARTED", "ACCEPT"}
        assert final_reviews[0].reviewer_id == final_reviews[1].reviewer_id
        assert final_reviews[0].reviewer_id == UUID(
            "00000000-0000-0000-0000-000000000106"
        )
        mandate_rows = (await db.execute(select(ClassroomFinalEvidenceReviewMandate).where(
            ClassroomFinalEvidenceReviewMandate.evidence_case_id == draft.id,
        ))).scalars().all()
        assert len(mandate_rows) == 1
        history = (await db.execute(select(ClassroomFinalEvidenceMandateRevision).where(
            ClassroomFinalEvidenceMandateRevision.mandate_id == mandate_rows[0].id,
        ).order_by(ClassroomFinalEvidenceMandateRevision.resulting_version))).scalars().all()
        assert [x.action for x in history] == ["ISSUE", "REVOKE"]
        assert [x.resulting_version for x in history] == [1, 2]
        human_accept_events = (await db.execute(select(DomainEvent).where(
            DomainEvent.aggregate_id == draft.id,
            DomainEvent.event_type == "evidence.classroom_accepted.v1",
        ))).scalars().all()
        assert len(human_accept_events) == 1
        assert draft.observed_fact not in str(human_accept_events[0].payload)
        assert human_accept_events[0].payload["formal_evidence_accepted"] is True
        human_accept_outbox = (await db.execute(select(OutboxEvent).where(
            OutboxEvent.event_id == human_accept_events[0].event_id,
        ))).scalar_one()
        assert draft.observed_fact not in str(human_accept_outbox.payload)
        # The two new isolated OIDC cases preserve separate final outcomes:
        # a human REJECTED case and an UNDER_REVIEW case whose final
        # appointment was revoked. Neither is formal Accepted Evidence.
        extra_observations = (await db.execute(select(ClassAssessorObservation).where(
            ClassAssessorObservation.organization_context_id == ORG_ID,
            ClassAssessorObservation.class_offering_id == CLASS_ID,
            ClassAssessorObservation.session_id == SESSION_ID,
            ClassAssessorObservation.observed_fact.like("CI_FINAL_%_SOURCE:%"),
        ))).scalars().all()
        assert len(extra_observations) == 2
        extras_by_fact = {o.observed_fact: o for o in extra_observations}
        for prefix, expected_state, expected_decision, mandate_revoked in (
            ("CI_FINAL_REJECTION_SOURCE:", "REJECTED", "REJECT", False),
            ("CI_FINAL_REVOKED_SOURCE:", "UNDER_REVIEW", None, True),
        ):
            matched = [o for text, o in extras_by_fact.items() if text.startswith(prefix)]
            assert len(matched) == 1
            source = matched[0]
            other = (await db.execute(select(EvidenceCase).where(
                EvidenceCase.source_observation_id == source.id,
                EvidenceCase.organization_context_id == ORG_ID,
            ))).scalars().all()
            assert len(other) == 1
            case = other[0]
            assert case.status == expected_state
            assert case.version == (4 if expected_decision else 3)
            assert case.candidate_visible is False
            assert case.accepted_at is None
            assert (case.rejected_at is not None) == (expected_decision == "REJECT")
            human_reviews = (await db.execute(select(EvidenceReview).where(
                EvidenceReview.evidence_case_id == case.id,
            ))).scalars().all()
            assert {r.decision for r in human_reviews} == (
                {"REVIEW_STARTED", expected_decision}
                if expected_decision else {"REVIEW_STARTED"}
            )
            assert all(r.reviewer_id == UUID(
                "00000000-0000-0000-0000-000000000106",
            ) for r in human_reviews)
            one_mandate = (await db.execute(select(ClassroomFinalEvidenceReviewMandate).where(
                ClassroomFinalEvidenceReviewMandate.evidence_case_id == case.id,
            ))).scalars().all()
            assert len(one_mandate) == 1
            assert (one_mandate[0].revoked_at is not None) == mandate_revoked
            assert one_mandate[0].version == (2 if mandate_revoked else 1)
            # No rejected or revoked case may be accepted downstream.
            assert await load_accepted_evidence_snapshots(
                db, organization_context_id=ORG_ID,
                subject_person_id=source.candidate_person_id,
                evidence_case_ids=(case.id,),
            ) == []

        interpretations = (
            await db.execute(select(EvidenceInterpretation).where(
                EvidenceInterpretation.evidence_case_id == draft.id,
            ))
        ).scalars().all()
        assert len(interpretations) == 1
        assert interpretations[0].created_by == REVIEWER_ID
        assert interpretations[0].version_number == 1
        assert interpretations[0].ai_contribution == "NONE"
        links = (
            await db.execute(select(EvidenceLink).where(
                EvidenceLink.interpretation_id == interpretations[0].id,
            ))
        ).scalars().all()
        assert len(links) == 1
        assert links[0].target_type == "CAPABILITY"
        assert links[0].target_ref == "CI_UNAPPROVED_OPAQUE_REFERENCE"
        submission_events = (
            await db.execute(select(DomainEvent).where(
                DomainEvent.aggregate_id == draft.id,
                DomainEvent.event_type == "evidence.interpretation_submitted.v1",
                DomainEvent.organization_context_id == ORG_ID,
            ))
        ).scalars().all()
        assert len(submission_events) == 1
        assert submission_events[0].actor == {"type": "PERSON", "id": str(REVIEWER_ID)}
        submission_outbox = (
            await db.execute(select(OutboxEvent).where(
                OutboxEvent.event_id == submission_events[0].event_id,
            ))
        ).scalar_one()
        for payload in (submission_events[0].payload, submission_outbox.payload):
            assert draft.observed_fact not in str(payload)
            assert interpretations[0].rationale not in str(payload)
        draft_events = (
            await db.execute(select(DomainEvent).where(
                DomainEvent.aggregate_id == draft.id,
                DomainEvent.event_type == "evidence.classroom_draft_created.v1",
                DomainEvent.organization_context_id == ORG_ID,
            ))
        ).scalars().all()
        assert len(draft_events) == 1
        assert draft_events[0].actor == {"type": "PERSON", "id": str(REVIEWER_ID)}
        draft_outbox = (
            await db.execute(select(OutboxEvent).where(
                OutboxEvent.event_id == draft_events[0].event_id
            ))
        ).scalar_one()
        for public_data in (draft_events[0].payload, draft_outbox.payload):
            assert item.observed_fact not in str(public_data)
            assert draft.provenance["submission_reason"] not in str(public_data)
        reviews = (
            await db.execute(select(DomainEvent).where(
                DomainEvent.aggregate_id == review.id,
                DomainEvent.event_type == "evidence.classroom_source_reviewed.v1",
                DomainEvent.organization_context_id == ORG_ID,
            ))
        ).scalars().all()
        assert len(reviews) == 1
        assert reviews[0].actor == {"type": "PERSON", "id": str(REVIEWER_ID)}
        assert item.observed_fact not in str(reviews[0].payload)
        review_outbox = (
            await db.execute(select(OutboxEvent).where(
                OutboxEvent.event_id == reviews[0].event_id
            ))
        ).scalar_one()
        assert item.observed_fact not in str(review_outbox.payload)
        assert review.rationale not in str(review_outbox.payload)
        events = (
            await db.execute(
                select(DomainEvent).where(
                    DomainEvent.aggregate_id == item.id,
                    DomainEvent.event_type == "academy.class_observation_recorded.v1",
                    DomainEvent.organization_context_id == ORG_ID,
                )
            )
        ).scalars().all()
        assert len(events) == 1, "Replay must not create another audit event"
        event = events[0]
        assert event.actor == {"type": "PERSON", "id": str(ASSESSOR_ID)}
        assert item.observed_fact not in str(event.payload), "Private note exposed in DomainEvent"
        outbox = (
            await db.execute(
                select(OutboxEvent).where(OutboxEvent.event_id == event.event_id)
            )
        ).scalar_one()
        assert item.observed_fact not in str(outbox.payload), "Private note exposed in Outbox"

    # Even privileged SQL connections must not be able to edit or delete history.
    async with engine.connect() as conn:
        trans = await conn.begin()
        for command in (
            update(ClassAssessorObservation)
            .where(ClassAssessorObservation.id == item.id)
            .values(observed_fact="Tampered after review"),
            delete(ClassAssessorObservation).where(
                ClassAssessorObservation.id == item.id
            ),
            update(ClassroomObservationSourceReview)
            .where(ClassroomObservationSourceReview.id == review.id)
            .values(decision="REJECTED"),
            delete(ClassroomObservationSourceReview)
            .where(ClassroomObservationSourceReview.id == review.id),
            # Even a final human decision must not be replayed by direct SQL
            # after its committed and irreversible transition.
            update(EvidenceCase)
            .where(EvidenceCase.id == draft.id)
            .values(status="UNDER_REVIEW", version=3),
            update(EvidenceCase)
            .where(EvidenceCase.id == draft.id)
            .values(status="ACCEPTED", version=3, accepted_at=item.recorded_at),
            update(EvidenceCase)
            .where(EvidenceCase.id == draft.id)
            .values(status="REJECTED", version=3, rejected_at=item.recorded_at),
            update(EvidenceCase)
            .where(EvidenceCase.id == draft.id)
            .values(candidate_visible=True),
            update(EvidenceCase)
            .where(EvidenceCase.id == draft.id)
            .values(provenance={"forged": "review authorization"}),
            update(EvidenceCase)
            .where(EvidenceCase.id == draft.id)
            .values(source_independence_group="FORGED_INDEPENDENCE"),
            update(EvidenceCase)
            .where(EvidenceCase.id == draft.id)
            .values(source_runtime_event_id=UUID(int=8394)),
            update(EvidenceCase)
            .where(EvidenceCase.id == draft.id)
            .values(observation_type="FORGED_SOURCE_TYPE"),
            update(EvidenceCase)
            .where(EvidenceCase.id == draft.id)
            .values(context_request="FORGED_PRIVATE_CONTEXT"),
            update(EvidenceCase)
            .where(EvidenceCase.id == draft.id)
            .values(created_at=item.recorded_at),
            delete(EvidenceCase).where(EvidenceCase.id == draft.id),
            update(EvidenceInterpretation)
            .where(EvidenceInterpretation.id == interpretations[0].id)
            .values(rationale="Tampered interpretation"),
            delete(EvidenceInterpretation)
            .where(EvidenceInterpretation.id == interpretations[0].id),
            update(EvidenceLink)
            .where(EvidenceLink.id == links[0].id)
            .values(target_ref="tampered"),
            delete(EvidenceLink).where(EvidenceLink.id == links[0].id),
            update(EvidenceReview)
            .where(EvidenceReview.evidence_case_id == draft.id)
            .values(decision="REJECT"),
            delete(EvidenceReview)
            .where(EvidenceReview.evidence_case_id == draft.id),
            update(ClassroomFinalEvidenceReviewMandate)
            .where(ClassroomFinalEvidenceReviewMandate.id == mandate_rows[0].id)
            .values(revoked_at=None, version=3),
            update(ClassroomFinalEvidenceReviewMandate)
            .where(ClassroomFinalEvidenceReviewMandate.id == mandate_rows[0].id)
            .values(reviewer_person_id=ASSESSOR_ID),
            delete(ClassroomFinalEvidenceReviewMandate)
            .where(ClassroomFinalEvidenceReviewMandate.id == mandate_rows[0].id),
            update(ClassroomFinalEvidenceMandateRevision)
            .where(ClassroomFinalEvidenceMandateRevision.id == history[0].id)
            .values(reason="Forged issuance history"),
            delete(ClassroomFinalEvidenceMandateRevision)
            .where(ClassroomFinalEvidenceMandateRevision.id == history[0].id),
        ):
            savepoint = await conn.begin_nested()
            try:
                await conn.execute(command)
            except DBAPIError:
                await savepoint.rollback()
            else:
                await savepoint.rollback()
                raise AssertionError("PostgreSQL must reject private classroom history mutation")
        await trans.rollback()

    async with SessionFactory() as db:
        restored = (
            await db.execute(
                select(ClassAssessorObservation).where(
                    ClassAssessorObservation.id == item.id
                )
            )
        ).scalar_one()
        assert restored.observed_fact == item.observed_fact
        persisted_review = (await db.execute(select(ClassroomObservationSourceReview).where(
            ClassroomObservationSourceReview.id == review.id
        ))).scalar_one()
        assert persisted_review.decision == "VERIFIED"
        preserved_case = (await db.execute(select(EvidenceCase).where(
            EvidenceCase.id == draft.id,
        ))).scalar_one()
        assert preserved_case.status == "ACCEPTED"
        assert preserved_case.version == 4
        assert preserved_case.accepted_at is not None and preserved_case.rejected_at is None
        assert preserved_case.candidate_visible is False
        assert preserved_case.provenance == draft.provenance
        preserved_interpretation = (await db.execute(select(EvidenceInterpretation).where(
            EvidenceInterpretation.id == interpretations[0].id,
        ))).scalar_one()
        assert preserved_interpretation.rationale == interpretations[0].rationale
        preserved_link = (await db.execute(select(EvidenceLink).where(
            EvidenceLink.id == links[0].id,
        ))).scalar_one()
        assert preserved_link.target_ref == "CI_UNAPPROVED_OPAQUE_REFERENCE"
        # This technical schema must never seed or implicitly appoint reviewers.
        mandates = (await db.execute(select(ClassroomFinalEvidenceReviewMandate).where(
            ClassroomFinalEvidenceReviewMandate.evidence_case_id == draft.id,
        ))).scalars().all()
        assert len(mandates) == 1
        assert mandates[0].version == 2 and mandates[0].revoked_at is not None
        assert mandates[0].reviewer_person_id == UUID(
            "00000000-0000-0000-0000-000000000106"
        )
        original_reviews = (await db.execute(select(EvidenceReview).where(
            EvidenceReview.evidence_case_id == draft.id,
        ))).scalars().all()
        assert len(original_reviews) == 2
        assert {r.decision for r in original_reviews} == {"REVIEW_STARTED", "ACCEPT"}
        # Even after attacker-style SQL attempts, ordinary Accepted Evidence
        # projection cannot create Pattern, Profile or Gate input from this case.
        assert await load_accepted_evidence_snapshots(
            db, organization_context_id=ORG_ID,
            subject_person_id=item.candidate_person_id,
            evidence_case_ids=(draft.id,),
        ) == []


if __name__ == "__main__":
    asyncio.run(main())
