"""Class mandates are time- and organization-scoped; no global Assessor access."""

from datetime import UTC, datetime
from dataclasses import dataclass


@dataclass(frozen=True)
class GrantWindow:
    starts_at: datetime
    ends_at: datetime
    revoked_at: datetime | None


def active_class_grant(
    grant: GrantWindow,
    *,
    now: datetime,
    class_status: str,
    cohort_status: str,
) -> bool:
    """Only ACTIVE classes/cohorts and live, non-revoked intervals authorize reads."""
    return (
        now.tzinfo is not None
        and grant.starts_at.tzinfo is not None
        and grant.ends_at.tzinfo is not None
        and class_status == "ACTIVE"
        and cohort_status == "ACTIVE"
        and grant.revoked_at is None
        and grant.starts_at <= now < grant.ends_at
    )


def current_utc() -> datetime:
    return datetime.now(UTC)
