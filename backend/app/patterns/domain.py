from enum import StrEnum
from typing import Any


class PatternStatus(StrEnum):
    EMERGING = "EMERGING"
    REPEATED = "REPEATED"
    STABLE = "STABLE"
    CONTRADICTED = "CONTRADICTED"
    REGRESSED = "REGRESSED"
    RECOVERING = "RECOVERING"


class PatternEvidenceRelationship(StrEnum):
    SUPPORTING = "SUPPORTING"
    CONTRADICTORY = "CONTRADICTORY"


EVIDENCE_SIGNALS = frozenset({"POSITIVE", "NEGATIVE", "CRITICAL", "NEUTRAL"})
QUALITATIVE_LEVELS = frozenset({"LOW", "MEDIUM", "HIGH"})
TARGET_TYPES = frozenset({"CAPABILITY", "COMPETENCY", "GATE"})


def _non_empty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _uuid_text(value: Any) -> bool:
    if not _non_empty_text(value):
        return False
    try:
        from uuid import UUID

        UUID(value)
    except (ValueError, TypeError, AttributeError):
        return False
    return True


def _target_links_valid(value: Any) -> bool:
    if not isinstance(value, list) or not value:
        return False
    for link in value:
        if not isinstance(link, dict):
            return False
        if link.get("target_type") not in TARGET_TYPES:
            return False
        if not _non_empty_text(link.get("target_ref")):
            return False
        if link.get("signal") not in EVIDENCE_SIGNALS:
            return False
        if not _non_empty_text(link.get("scope")):
            return False
        if link.get("relevance") not in QUALITATIVE_LEVELS:
            return False
        if link.get("confidence") not in QUALITATIVE_LEVELS:
            return False
    return True


def evidence_set_contract_valid(value: Any) -> bool:
    if not isinstance(value, dict):
        return False

    if not _uuid_text(value.get("organization_context_id")):
        return False
    if not _uuid_text(value.get("subject_person_id")):
        return False

    members = value.get("members")
    if not isinstance(members, list) or not members:
        return False

    seen_evidence_cases: set[str] = set()
    for member in members:
        if not isinstance(member, dict):
            return False

        evidence_case_id = member.get("evidence_case_id")
        if not _uuid_text(evidence_case_id) or evidence_case_id in seen_evidence_cases:
            return False
        seen_evidence_cases.add(evidence_case_id)

        if not _uuid_text(member.get("interpretation_id")):
            return False
        if not isinstance(member.get("interpretation_version"), int):
            return False
        if member["interpretation_version"] < 1:
            return False
        if not _non_empty_text(member.get("behaviour_code")):
            return False
        if member.get("signal") not in EVIDENCE_SIGNALS:
            return False
        if not _non_empty_text(member.get("scope")):
            return False
        if member.get("confidence") not in QUALITATIVE_LEVELS:
            return False
        if not _non_empty_text(member.get("context_difficulty")):
            return False
        if not _non_empty_text(member.get("prompt_contamination")):
            return False
        if not _non_empty_text(member.get("source_independence_group")):
            return False
        if not _non_empty_text(member.get("accepted_at")):
            return False
        if not _target_links_valid(member.get("target_links")):
            return False

        lineage = member.get("source_lineage")
        if not isinstance(lineage, dict):
            return False
        for key in (
            "source_observation_id",
            "source_context",
            "source_reference",
            "observation_type",
        ):
            if not _non_empty_text(lineage.get(key)):
                return False

    return True


def pattern_candidate_contract_valid(value: Any) -> bool:
    if not isinstance(value, dict):
        return False

    for key in (
        "behaviour_code",
        "behaviour_description",
        "scope",
        "rationale",
    ):
        if not _non_empty_text(value.get(key)):
            return False

    if value.get("proposed_pattern_status") not in {item.value for item in PatternStatus}:
        return False

    evidence = value.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        return False

    seen_member_ids: set[str] = set()
    supporting_seen = False
    for item in evidence:
        if not isinstance(item, dict):
            return False
        member_id = item.get("evidence_set_member_id")
        if not _uuid_text(member_id) or member_id in seen_member_ids:
            return False
        seen_member_ids.add(member_id)

        relationship = item.get("relationship")
        if relationship not in {entry.value for entry in PatternEvidenceRelationship}:
            return False
        if relationship == PatternEvidenceRelationship.SUPPORTING.value:
            supporting_seen = True

    return supporting_seen
