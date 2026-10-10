"""P23 Evidence review: defensive contract, not authorization to decide."""
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import cast
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.academy.models import ClassAssessorObservation
from app.evidence.classroom_review_safety import classroom_review_lineage_independent
from app.evidence.contracts import load_accepted_evidence_snapshots
from app.evidence.models import (
    ClassroomObservationSourceReview,
    EvidenceCase,
    EvidenceInterpretation,
)

ORG = UUID(int=81001)
SOURCE_ID = UUID(int=81002)
CASE_ID = UUID(int=81003)
OBSERVER = UUID(int=81004)
REVIEWER = UUID(int=81005)
SUBJECT = UUID(int=81006)
FINAL = UUID(int=81007)
NOW = datetime(2026, 10, 10, tzinfo=UTC)


def lineage():
    source = SimpleNamespace(
        id=SOURCE_ID, organization_context_id=ORG,
        observer_person_id=OBSERVER, candidate_person_id=SUBJECT,
        class_offering_id=UUID(int=81008), session_id=UUID(int=81009),
        observed_fact="Sensitive factual observation",
        observed_at=NOW - timedelta(hours=2),
        grant_id=UUID(int=81010), grant_version=2,
    )
    review = SimpleNamespace(
        id=UUID(int=81011), organization_context_id=ORG,
        reviewer_person_id=REVIEWER, observer_person_id=OBSERVER,
        subject_person_id=SUBJECT, source_observation_id=SOURCE_ID,
        class_offering_id=source.class_offering_id, session_id=source.session_id,
        source_sha256="a" * 64, reviewer_grant_id=UUID(int=81012),
        reviewer_grant_version=3, decision="VERIFIED",
    )
    case = SimpleNamespace(
        id=CASE_ID, version=2, status="SUBMITTED",
        source_context="CLASSROOM_OBSERVATION", integrity_state="SOURCE_REVIEWED",
        candidate_visible=False, accepted_at=None, rejected_at=None,
        organization_context_id=ORG, source_observation_id=SOURCE_ID,
        subject_person_id=SUBJECT, observed_fact=source.observed_fact,
        occurred_at=source.observed_at,
        provenance={
            "created_by_person_id": str(REVIEWER),
            "source_review_id": str(review.id), "source_sha256": review.source_sha256,
            "class_offering_id": str(source.class_offering_id),
            "session_id": str(source.session_id),
            "source_grant_id": str(source.grant_id), "source_grant_version": 2,
            "reviewer_grant_id": str(review.reviewer_grant_id),
            "reviewer_grant_version": 3,
        },
    )
    interpretation = SimpleNamespace(
        evidence_case_id=CASE_ID, version_number=1, status="ACTIVE",
        ai_contribution="NONE", created_by=REVIEWER,
    )
    return case, source, review, interpretation


def eligible(*, final=FINAL, expected_version=2, digest="a" * 64,
             fixture=None) -> bool:
    case, source, review, interpretation = fixture or lineage()
    return classroom_review_lineage_independent(
        case=cast(EvidenceCase, case), source=cast(ClassAssessorObservation, source),
        source_review=cast(ClassroomObservationSourceReview, review),
        interpretation=cast(EvidenceInterpretation, interpretation), final_reviewer_id=final,
        expected_version=expected_version, current_source_sha256=digest,
    )


def test_necessary_independence_never_grants_final_reviewer_appointment() -> None:
    assert eligible()  # necessary condition ONLY, never an authorization
    for same_person in (OBSERVER, REVIEWER, SUBJECT):
        assert not eligible(final=same_person)
    assert not eligible(expected_version=1)
    assert not eligible(digest="0" * 64)


@pytest.mark.parametrize(
    ("owner", "field", "value"), [
        ("case", "status", "UNDER_REVIEW"),
        ("case", "status", "ACCEPTED"),
        ("case", "candidate_visible", True),
        ("case", "accepted_at", NOW),
        ("case", "organization_context_id", UUID(int=2)),
        ("case", "observed_fact", "tampered"),
        ("case", "source_context", "MISSION_RUNTIME"),
        ("review", "decision", "REJECTED"),
        ("review", "reviewer_person_id", OBSERVER),
        ("review", "source_sha256", "0" * 64),
        ("interpretation", "created_by", OBSERVER),
        ("interpretation", "ai_contribution", "MODEL"),
        ("interpretation", "version_number", 2),
        ("interpretation", "status", "SUPERSEDED"),
    ],
)
def test_review_readiness_rejects_stale_or_modified_lineage(owner, field, value) -> None:
    case, source, review, interpretation = lineage()
    target = {"case": case, "source": source, "review": review,
              "interpretation": interpretation}[owner]
    setattr(target, field, value)
    assert not eligible(fixture=(case, source, review, interpretation))


def test_review_readiness_rejects_wrong_interpretation_creator_or_provenance() -> None:
    case, source, review, interpretation = lineage()
    case.provenance["created_by_person_id"] = str(OBSERVER)
    assert not eligible(fixture=(case, source, review, interpretation))
    case, source, review, interpretation = lineage()
    case.provenance["source_grant_version"] = 999
    assert not eligible(fixture=(case, source, review, interpretation))


class Rows:
    def __init__(self, value):
        self.value = value

    def scalars(self):
        return self

    def all(self):
        return self.value


class FakeDB:
    def __init__(self, value):
        self.value = value
        self.statements = []

    async def execute(self, statement):
        self.statements.append(statement)
        return Rows(self.value)


@pytest.mark.asyncio
async def test_accepted_evidence_snapshot_filters_out_classroom_before_downstream() -> None:
    # Even a corrupt/pre-existing ACCEPTED classroom row cannot become a
    # Pattern/Profile/Gate input through the ordinary accepted reader.
    case = EvidenceCase(
        id=CASE_ID, source_context="CLASSROOM_OBSERVATION",
        accepted_at=NOW, status="ACCEPTED",
    )
    db = FakeDB([case])
    result = await load_accepted_evidence_snapshots(
        cast(AsyncSession, db), organization_context_id=ORG,
        subject_person_id=SUBJECT, evidence_case_ids=(CASE_ID,),
    )
    assert result == []
    assert len(db.statements) == 1
    compiled = db.statements[0].compile()
    assert "source_context !=" in str(compiled)
    assert "CLASSROOM_OBSERVATION" in compiled.params.values()


def test_decision_barrier_migration_is_explicit_and_no_reviewer_route_is_published() -> None:
    migration = (
        Path(__file__).resolve().parents[1]
        / "alembic/versions/0035_classroom_evidence_decision_barrier.py"
    ).read_text(encoding="utf-8")
    assert 'down_revision = "0034"' in migration
    for protected in (
        "trg_classroom_case_decision_barrier",
        "trg_classroom_interpretation_immutable",
        "trg_classroom_link_immutable",
        "UNDER_REVIEW",
        "accepted_at",
        "candidate_visible",
    ):
        if protected == "UNDER_REVIEW":
            # All non-DRAFT/SUBMITTED decisions are denied by the SQL gate.
            assert "NEW.status NOT IN ('DRAFT', 'SUBMITTED')" in migration
        else:
            assert protected in migration

    from app.main import app

    paths = app.openapi()["paths"]
    assert "/api/v1/classroom-evidence-cases/{case_id}/reviews" not in paths
    assert "post" in paths["/api/v1/classroom-evidence-cases/{case_id}/accept"]
    assert "post" in paths["/api/v1/classroom-evidence-cases/{case_id}/reject"]
