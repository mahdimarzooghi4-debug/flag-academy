from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class LearningUnit(Base):
    __tablename__ = "learning_units"
    __table_args__ = {"schema": "learning"}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    class_offering_id: Mapped[UUID]
    capability_version_id: Mapped[UUID]
    unit_type: Mapped[str] = mapped_column(String(32))
    phase: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    resource_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    position: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class LearningUnitProgress(Base):
    __tablename__ = "learning_unit_progress"
    __table_args__ = (
        UniqueConstraint("learning_unit_id", "candidate_id"),
        {"schema": "learning"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    version: Mapped[int] = mapped_column(BigInteger, default=1)
    learning_unit_id: Mapped[UUID] = mapped_column(
        ForeignKey("learning.learning_units.id")
    )
    candidate_id: Mapped[UUID]
    state: Mapped[str] = mapped_column(String(32))
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Assignment(Base):
    __tablename__ = "assignments"
    __table_args__ = {"schema": "learning"}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    version: Mapped[int] = mapped_column(BigInteger, default=1)
    class_offering_id: Mapped[UUID]
    capability_version_id: Mapped[UUID]
    title: Mapped[str] = mapped_column(String(255))
    instructions: Mapped[str] = mapped_column(Text)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Submission(Base):
    __tablename__ = "submissions"
    __table_args__ = (
        UniqueConstraint("assignment_id", "candidate_id"),
        {"schema": "learning"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    version: Mapped[int] = mapped_column(BigInteger, default=1)
    assignment_id: Mapped[UUID] = mapped_column(ForeignKey("learning.assignments.id"))
    candidate_id: Mapped[UUID]
    content_text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32))
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class InstructorFeedback(Base):
    __tablename__ = "instructor_feedback"
    __table_args__ = {"schema": "learning"}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    submission_id: Mapped[UUID] = mapped_column(ForeignKey("learning.submissions.id"))
    instructor_id: Mapped[UUID]
    feedback_text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
