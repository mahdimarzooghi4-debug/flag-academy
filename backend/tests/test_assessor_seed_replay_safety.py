"""Development data reset must not fail after human class-grant tests."""

from pathlib import Path


def test_dev_seed_drops_assessor_grant_history_before_parent_class():
    source = Path("app/seed.py").read_text()
    cleanup = source[source.index("for model in ("):source.index("):", source.index("for model in ("))]
    assert cleanup.index("AssessorClassGrantRevision,") < cleanup.index("AssessorClassGrant,")
    assert cleanup.index("AssessorClassGrant,") < cleanup.index("ClassOffering,")


def test_seed_source_never_authorizes_or_creates_fake_class_grants():
    source = Path("app/seed.py").read_text()
    assert "AssessorClassGrant(" not in source
    assert "AssessorClassGrantRevision(" not in source
