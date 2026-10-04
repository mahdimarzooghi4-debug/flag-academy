from enum import StrEnum


class CohortStatus(StrEnum):
    PLANNED = "PLANNED"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class DeliveryMode(StrEnum):
    IN_PERSON = "IN_PERSON"
    ONLINE = "ONLINE"
    HYBRID = "HYBRID"
