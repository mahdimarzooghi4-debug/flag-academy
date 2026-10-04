from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Person(Base):
    __tablename__ = "people"
    __table_args__ = {"schema": "identity"}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    version: Mapped[int] = mapped_column(BigInteger, default=1)
    external_subject: Mapped[str] = mapped_column(String(255), unique=True)
    display_name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Organization(Base):
    __tablename__ = "organizations"
    __table_args__ = {"schema": "identity"}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    version: Mapped[int] = mapped_column(BigInteger, default=1)
    name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class OrganizationMembership(Base):
    __tablename__ = "organization_memberships"
    __table_args__ = (
        UniqueConstraint("person_id", "organization_id", "membership_role"),
        {"schema": "identity"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    person_id: Mapped[UUID] = mapped_column(ForeignKey("identity.people.id"))
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("identity.organizations.id"))
    membership_role: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
