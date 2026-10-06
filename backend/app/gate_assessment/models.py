from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class GateDefinition(Base):
    __tablename__ = "gate_definitions"
    __table_args__ = {"schema": "gate_assessment"}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(8), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class GateDefinitionVersion(Base):
    __tablename__ = "gate_definition_versions"
    __table_args__ = (
        UniqueConstraint(
            "gate_definition_id",
            "version_number",
            name="uq_gate_definition_version",
        ),
        {"schema": "gate_assessment"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    gate_definition_id: Mapped[UUID] = mapped_column(
        ForeignKey("gate_assessment.gate_definitions.id")
    )
    version_number: Mapped[int] = mapped_column(Integer)
    decision_question: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class GateDefinitionRequirement(Base):
    __tablename__ = "gate_definition_requirements"
    __table_args__ = (
        UniqueConstraint(
            "gate_definition_version_id",
            "position",
            name="uq_gate_definition_requirement_position",
        ),
        {"schema": "gate_assessment"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    gate_definition_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("gate_assessment.gate_definition_versions.id")
    )
    position: Mapped[int] = mapped_column(Integer)
    requirement_text: Mapped[str] = mapped_column(Text)


class GateDefinitionOutcome(Base):
    __tablename__ = "gate_definition_outcomes"
    __table_args__ = (
        UniqueConstraint(
            "gate_definition_version_id",
            "position",
            name="uq_gate_definition_outcome_position",
        ),
        {"schema": "gate_assessment"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    gate_definition_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("gate_assessment.gate_definition_versions.id")
    )
    position: Mapped[int] = mapped_column(Integer)
    outcome_text: Mapped[str] = mapped_column(Text)
