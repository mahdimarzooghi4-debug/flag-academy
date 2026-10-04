from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class CandidateJourney(Base):
    __tablename__ = "candidate_journeys"
    __table_args__ = (
        UniqueConstraint("person_id", "organization_context_id", "track_code"),
        {"schema": "journey"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    version: Mapped[int] = mapped_column(BigInteger, default=1)
    person_id: Mapped[UUID]
    organization_context_id: Mapped[UUID]
    cohort_id: Mapped[UUID]
    track_code: Mapped[str] = mapped_column(String(128))
    curriculum_version_id: Mapped[UUID]
    state: Mapped[str] = mapped_column(String(32))
    current_wave: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
