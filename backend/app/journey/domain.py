from enum import StrEnum


class CandidateJourneyState(StrEnum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    WITHDRAWN = "WITHDRAWN"
