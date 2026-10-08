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


class AttendanceStatus(StrEnum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"


def attendance_resulting_version(
    *,
    current_status: str | None,
    current_version: int,
    requested_status: str,
) -> int:
    if requested_status not in {item.value for item in AttendanceStatus}:
        raise ValueError("unsupported attendance status")
    if current_status is None:
        if current_version != 0:
            raise ValueError("missing attendance record must use version 0")
        return 1
    if current_version < 1:
        raise ValueError("existing attendance record must have positive version")
    if requested_status == current_status:
        return current_version
    return current_version + 1
