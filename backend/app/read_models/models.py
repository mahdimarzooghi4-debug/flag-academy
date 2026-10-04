from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class CandidateHomeProjection(Base):
    __tablename__ = "candidate_home"
    __table_args__ = {"schema": "readmodel"}

    person_id: Mapped[UUID] = mapped_column(primary_key=True)
    organization_context_id: Mapped[UUID] = mapped_column(primary_key=True)
    payload: Mapped[dict] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class InstructorHomeProjection(Base):
    __tablename__ = "instructor_home"
    __table_args__ = {"schema": "readmodel"}

    person_id: Mapped[UUID] = mapped_column(primary_key=True)
    organization_context_id: Mapped[UUID] = mapped_column(primary_key=True)
    payload: Mapped[dict] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
