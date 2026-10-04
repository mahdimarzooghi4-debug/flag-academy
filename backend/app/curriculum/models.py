from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Capability(Base):
    __tablename__ = "capabilities"
    __table_args__ = {"schema": "curriculum"}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(128), unique=True)


class CapabilityVersion(Base):
    __tablename__ = "capability_versions"
    __table_args__ = (
        UniqueConstraint("definition_id", "version_number"),
        {"schema": "curriculum"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    definition_id: Mapped[UUID] = mapped_column(ForeignKey("curriculum.capabilities.id"))
    version_number: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(255))
    definition: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32))


class Curriculum(Base):
    __tablename__ = "curricula"
    __table_args__ = (
        UniqueConstraint("code", "version_number"),
        {"schema": "curriculum"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(128))
    version_number: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32))


class CurriculumWave(Base):
    __tablename__ = "curriculum_waves"
    __table_args__ = (
        UniqueConstraint("curriculum_id", "code"),
        {"schema": "curriculum"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    curriculum_id: Mapped[UUID] = mapped_column(ForeignKey("curriculum.curricula.id"))
    code: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(255))
    position: Mapped[int] = mapped_column(Integer)


class WaveCapability(Base):
    __tablename__ = "wave_capabilities"
    __table_args__ = (
        UniqueConstraint("wave_id", "capability_version_id"),
        {"schema": "curriculum"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    wave_id: Mapped[UUID] = mapped_column(ForeignKey("curriculum.curriculum_waves.id"))
    capability_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("curriculum.capability_versions.id")
    )
    position: Mapped[int] = mapped_column(Integer)
