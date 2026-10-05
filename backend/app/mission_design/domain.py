from enum import StrEnum


class MissionVersionStatus(StrEnum):
    DRAFT = "DRAFT"
    PILOT = "PILOT"
    VALIDATED = "VALIDATED"
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"


class MissionMode(StrEnum):
    LEARN = "LEARN"
    PRACTICE = "PRACTICE"
    ASSESSMENT = "ASSESSMENT"
    REAL_PROJECT = "REAL_PROJECT"


class MissionDifficulty(StrEnum):
    D1 = "D1"
    D2 = "D2"
    D3 = "D3"
    D4 = "D4"
    D5 = "D5"


ALLOWED_TRANSITIONS: dict[MissionVersionStatus, frozenset[MissionVersionStatus]] = {
    MissionVersionStatus.DRAFT: frozenset({MissionVersionStatus.PILOT}),
    MissionVersionStatus.PILOT: frozenset({MissionVersionStatus.VALIDATED}),
    MissionVersionStatus.VALIDATED: frozenset({MissionVersionStatus.ACTIVE}),
    MissionVersionStatus.ACTIVE: frozenset({MissionVersionStatus.RETIRED}),
    MissionVersionStatus.RETIRED: frozenset(),
}


def transition_allowed(current: str, target: str) -> bool:
    current_status = MissionVersionStatus(current)
    target_status = MissionVersionStatus(target)
    return target_status in ALLOWED_TRANSITIONS[current_status]
