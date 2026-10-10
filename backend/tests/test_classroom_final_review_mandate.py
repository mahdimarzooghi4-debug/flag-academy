"""Inert final Evidence mandate prerequisites: never automatic permission."""
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest

from app.academy.models import AssessorClassGrant, ClassAssessorObservation
from app.evidence.classroom_final_review_mandate import final_review_mandate_prerequisites
from app.evidence.models import (
    ClassroomFinalEvidenceReviewMandate,
    ClassroomObservationSourceReview,
    EvidenceCase,
    EvidenceInterpretation,
)
from app.identity.auth import ActorContext
from app.main import app

NOW = datetime(2026, 10, 10, 12, tzinfo=UTC)
ORG, CLASS, CASE, SOURCE = (UUID(int=x) for x in (72001, 72002, 72003, 72004))
OBSERVER, SOURCE_REVIEWER, FINAL, LEARNER = (
    UUID(int=x) for x in (72005, 72006, 72007, 72008)
)
DIGEST = "a" * 64


def example() -> dict[str, Any]:
    source = ClassAssessorObservation(
        id=SOURCE, organization_context_id=ORG,
        class_offering_id=CLASS, session_id=UUID(int=72009),
        candidate_person_id=LEARNER, observer_person_id=OBSERVER,
        grant_id=UUID(int=72010), grant_version=2,
        observed_at=NOW - timedelta(hours=2),
        observed_fact="Private human-observed class facts",
    )
    source_review = ClassroomObservationSourceReview(
        id=UUID(int=72011), organization_context_id=ORG,
        source_observation_id=SOURCE, class_offering_id=CLASS,
        session_id=source.session_id, subject_person_id=LEARNER,
        observer_person_id=OBSERVER, reviewer_person_id=SOURCE_REVIEWER,
        reviewer_grant_id=UUID(int=72012), reviewer_grant_version=1,
        source_sha256=DIGEST, decision="VERIFIED",
    )
    case = EvidenceCase(
        id=CASE, version=2, organization_context_id=ORG,
        source_observation_id=SOURCE, subject_person_id=LEARNER,
        source_context="CLASSROOM_OBSERVATION", status="SUBMITTED",
        integrity_state="SOURCE_REVIEWED", candidate_visible=False,
        accepted_at=None, rejected_at=None,
        observed_fact=source.observed_fact, occurred_at=source.observed_at,
        provenance={
            "source_review_id": str(source_review.id),
            "source_sha256": DIGEST,
            "created_by_person_id": str(SOURCE_REVIEWER),
            "class_offering_id": str(CLASS),
            "session_id": str(source.session_id),
            "source_grant_id": str(source.grant_id),
            "source_grant_version": 2,
            "reviewer_grant_id": str(source_review.reviewer_grant_id),
            "reviewer_grant_version": 1,
        },
    )
    interpretation = EvidenceInterpretation(
        evidence_case_id=CASE, status="ACTIVE", version_number=1,
        ai_contribution="NONE", created_by=SOURCE_REVIEWER,
    )
    mandate = ClassroomFinalEvidenceReviewMandate(
        id=UUID(int=72013), version=1, organization_context_id=ORG,
        evidence_case_id=CASE, class_offering_id=CLASS,
        reviewer_person_id=FINAL, issued_by_person_id=UUID(int=72014),
        issued_at=NOW - timedelta(hours=1),
        starts_at=NOW - timedelta(minutes=30),
        ends_at=NOW + timedelta(hours=1), revoked_at=None,
    )
    grant = AssessorClassGrant(
        organization_context_id=ORG,
        class_offering_id=CLASS, assessor_person_id=FINAL,
        starts_at=NOW - timedelta(hours=1),
        ends_at=NOW + timedelta(hours=1), revoked_at=None,
    )
    actor = ActorContext(
        actor_id=str(FINAL), person_id=FINAL,
        organization_context_id=ORG, roles=frozenset({"ASSESSOR"}),
    )
    return dict(actor=actor, mandate=mandate, case=case, source=source,
                source_review=source_review, interpretation=interpretation,
                current_class_grant=grant, now=NOW,
                current_org_assessor_membership_confirmed=True,
                class_status="ACTIVE", cohort_status="ACTIVE",
                current_source_sha256=DIGEST, expected_case_version=2)


def necessary_only(**updates):
    values = example()
    values.update(updates)
    return final_review_mandate_prerequisites(**values)


def test_structural_case_never_grants_authority_without_admin_mandate() -> None:
    assert necessary_only()
    paths = app.openapi()["paths"]
    assert "post" in paths["/api/v1/admin/academy/classroom-evidence-cases/{case_id}/final-review-mandate"]
    assert "post" in paths["/api/v1/admin/academy/final-review-mandates/{mandate_id}/revoke"]
    assert "post" in paths["/api/v1/classroom-evidence-cases/{case_id}/review-start"]
    assert "post" in paths["/api/v1/classroom-evidence-cases/{case_id}/accept"]
    assert "post" in paths["/api/v1/classroom-evidence-cases/{case_id}/reject"]


@pytest.mark.parametrize("field,value", [
    ("revoked_at", NOW),
    ("evidence_case_id", UUID(int=99)),
    ("organization_context_id", UUID(int=99)),
    ("class_offering_id", UUID(int=99)),
    ("reviewer_person_id", OBSERVER),
    ("reviewer_person_id", SOURCE_REVIEWER),
    ("reviewer_person_id", LEARNER),
    ("starts_at", NOW + timedelta(seconds=1)),
    ("ends_at", NOW),
    ("issued_at", NOW + timedelta(seconds=1)),
    ("version", 0),
])
def test_invalid_scope_time_or_revoked_mandate_never_qualifies(field, value) -> None:
    args = example()
    setattr(args["mandate"], field, value)
    assert not final_review_mandate_prerequisites(**args)


@pytest.mark.parametrize("field,value", [
    ("organization_context_id", UUID(int=99)),
    ("class_offering_id", UUID(int=99)),
    ("assessor_person_id", OBSERVER),
    ("revoked_at", NOW),
    ("ends_at", NOW),
])
def test_invalid_current_class_grant_never_qualifies(field, value) -> None:
    args = example()
    setattr(args["current_class_grant"], field, value)
    assert not final_review_mandate_prerequisites(**args)


def test_organization_membership_status_digest_and_case_version_are_distinct_gates() -> None:
    args = example()
    args["current_org_assessor_membership_confirmed"] = False
    assert not final_review_mandate_prerequisites(**args)
    assert not necessary_only(class_status="INACTIVE")
    assert not necessary_only(cohort_status="INACTIVE")
    assert not necessary_only(current_source_sha256="0" * 64)
    assert not necessary_only(expected_case_version=1)
    assert not necessary_only(now=NOW + timedelta(days=2))
    args = example()
    args["actor"] = ActorContext(
        actor_id=str(FINAL), person_id=FINAL, organization_context_id=ORG,
        roles=frozenset({"ACADEMY_ADMIN"}),
    )
    assert not final_review_mandate_prerequisites(**args)


def test_actual_human_interpretation_author_cannot_become_final_reviewer() -> None:
    args = example()
    args["actor"] = ActorContext(
        actor_id=str(SOURCE_REVIEWER), person_id=SOURCE_REVIEWER,
        organization_context_id=ORG, roles=frozenset({"ASSESSOR"}),
    )
    args["mandate"].reviewer_person_id = SOURCE_REVIEWER
    args["current_class_grant"].assessor_person_id = SOURCE_REVIEWER
    assert not final_review_mandate_prerequisites(**args)


def test_migration_is_inert_and_full_lineage_protection_is_separate() -> None:
    path = (
        Path(__file__).resolve().parents[1]
        / "alembic/versions/0036_classroom_final_review_mandate_foundation.py"
    )
    migration = path.read_text(encoding="utf-8")
    assert 'down_revision = "0035"' in migration
    assert "classroom_final_evidence_review_mandates" in migration
    assert "trg_classroom_case_complete_lineage" in migration
    assert "to_jsonb(NEW) - 'status' - 'version' - 'updated_at'" in migration
    assert "Evidence reviewer" not in migration  # no policy is established by SQL
