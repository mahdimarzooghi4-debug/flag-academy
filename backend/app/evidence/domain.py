from enum import StrEnum
from typing import Any


class EvidenceCaseStatus(StrEnum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    NEEDS_CONTEXT = "NEEDS_CONTEXT"


class EvidenceSignal(StrEnum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    CRITICAL = "CRITICAL"
    NEUTRAL = "NEUTRAL"


class InterpretationStatus(StrEnum):
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"


ALLOWED_CASE_TRANSITIONS: dict[EvidenceCaseStatus, frozenset[EvidenceCaseStatus]] = {
    EvidenceCaseStatus.DRAFT: frozenset({EvidenceCaseStatus.SUBMITTED}),
    EvidenceCaseStatus.SUBMITTED: frozenset({EvidenceCaseStatus.UNDER_REVIEW}),
    EvidenceCaseStatus.UNDER_REVIEW: frozenset(
        {
            EvidenceCaseStatus.ACCEPTED,
            EvidenceCaseStatus.REJECTED,
            EvidenceCaseStatus.NEEDS_CONTEXT,
        }
    ),
    EvidenceCaseStatus.NEEDS_CONTEXT: frozenset({EvidenceCaseStatus.UNDER_REVIEW}),
    EvidenceCaseStatus.ACCEPTED: frozenset(),
    EvidenceCaseStatus.REJECTED: frozenset(),
}

TARGET_TYPES = frozenset({"CAPABILITY", "COMPETENCY", "GATE"})
QUALITATIVE_LEVELS = frozenset({"LOW", "MEDIUM", "HIGH"})


def case_transition_allowed(current: str, target: str) -> bool:
    return EvidenceCaseStatus(target) in ALLOWED_CASE_TRANSITIONS[EvidenceCaseStatus(current)]


def interpretation_contract_valid(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    required_text = {
        "behaviour_code",
        "behaviour_description",
        "scope",
        "context_difficulty",
        "prompt_contamination",
        "ai_contribution",
        "mode",
        "rationale",
    }
    if any(not isinstance(value.get(key), str) or not value[key].strip() for key in required_text):
        return False
    if value.get("signal") not in {item.value for item in EvidenceSignal}:
        return False
    if value.get("confidence") not in QUALITATIVE_LEVELS:
        return False
    links = value.get("links")
    if not isinstance(links, list) or not links:
        return False
    for link in links:
        if not isinstance(link, dict):
            return False
        if link.get("target_type") not in TARGET_TYPES:
            return False
        if not isinstance(link.get("target_ref"), str) or not link["target_ref"].strip():
            return False
        if link.get("signal") not in {item.value for item in EvidenceSignal}:
            return False
        if not isinstance(link.get("scope"), str) or not link["scope"].strip():
            return False
        if link.get("relevance") not in QUALITATIVE_LEVELS:
            return False
        if link.get("confidence") not in QUALITATIVE_LEVELS:
            return False
    return True
