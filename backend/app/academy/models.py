from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Cohort(Base):
    __tablename__ = "cohorts"
    __table_args__ = (
        UniqueConstraint("organization_context_id", "code"),
        {"schema": "academy"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    version: Mapped[int] = mapped_column(BigInteger, default=1)
    organization_context_id: Mapped[UUID]
    code: Mapped[str] = mapped_column(String(128))
    name: Mapped[str] = mapped_column(String(255))
    track_code: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32))
    starts_on: Mapped[date] = mapped_column(Date)
    ends_on: Mapped[date | None] = mapped_column(Date, nullable=True)


class CohortMembership(Base):
    __tablename__ = "cohort_memberships"
    __table_args__ = (
        UniqueConstraint("cohort_id", "person_id", "member_type"),
        {"schema": "academy"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    cohort_id: Mapped[UUID] = mapped_column(ForeignKey("academy.cohorts.id"))
    person_id: Mapped[UUID]
    member_type: Mapped[str] = mapped_column(String(32))


class ClassOffering(Base):
    __tablename__ = "class_offerings"
    __table_args__ = {"schema": "academy"}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    cohort_id: Mapped[UUID] = mapped_column(ForeignKey("academy.cohorts.id"))
    title: Mapped[str] = mapped_column(String(255))
    primary_capability_version_id: Mapped[UUID]
    status: Mapped[str] = mapped_column(String(32))


class Session(Base):
    __tablename__ = "sessions"
    __table_args__ = {"schema": "academy"}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    class_offering_id: Mapped[UUID] = mapped_column(ForeignKey("academy.class_offerings.id"))
    title: Mapped[str] = mapped_column(String(255))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    delivery_mode: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32))


class InstructorAssignment(Base):
    __tablename__ = "instructor_assignments"
    __table_args__ = (
        UniqueConstraint("class_offering_id", "person_id"),
        {"schema": "academy"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    class_offering_id: Mapped[UUID] = mapped_column(ForeignKey("academy.class_offerings.id"))
    person_id: Mapped[UUID]



class AttendanceRecord(Base):
    __tablename__ = "attendance_records"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PRESENT', 'ABSENT')",
            name="ck_attendance_record_status",
        ),
        UniqueConstraint(
            "session_id",
            "person_id",
            name="uq_attendance_record_session_person",
        ),
        {"schema": "academy"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    version: Mapped[int] = mapped_column(BigInteger, default=1)
    organization_context_id: Mapped[UUID]
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("academy.sessions.id")
    )
    person_id: Mapped[UUID]
    status: Mapped[str] = mapped_column(String(16))
    created_by: Mapped[UUID]
    updated_by: Mapped[UUID]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AttendanceRevision(Base):
    __tablename__ = "attendance_revisions"
    __table_args__ = (
        CheckConstraint(
            "prior_status IS NULL OR prior_status IN ('PRESENT', 'ABSENT')",
            name="ck_attendance_revision_prior_status",
        ),
        CheckConstraint(
            "resulting_status IN ('PRESENT', 'ABSENT')",
            name="ck_attendance_revision_resulting_status",
        ),
        CheckConstraint(
            "expected_version >= 0",
            name="ck_attendance_revision_expected_version",
        ),
        CheckConstraint(
            "resulting_version >= 1",
            name="ck_attendance_revision_resulting_version",
        ),
        UniqueConstraint(
            "organization_context_id",
            "changed_by",
            "idempotency_key",
            name="uq_attendance_revision_idempotency",
        ),
        {"schema": "academy"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    attendance_record_id: Mapped[UUID] = mapped_column(
        ForeignKey("academy.attendance_records.id")
    )
    organization_context_id: Mapped[UUID]
    session_id: Mapped[UUID]
    person_id: Mapped[UUID]
    expected_version: Mapped[int] = mapped_column(BigInteger)
    prior_version: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    prior_status: Mapped[str | None] = mapped_column(
        String(16), nullable=True
    )
    resulting_version: Mapped[int] = mapped_column(BigInteger)
    resulting_status: Mapped[str] = mapped_column(String(16))
    changed_by: Mapped[UUID]
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    idempotency_key: Mapped[str] = mapped_column(String(160))
