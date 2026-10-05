from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class MissionTemplate(Base):
    __tablename__ = "mission_templates"
    __table_args__ = (
        UniqueConstraint(
            "organization_context_id",
            "code",
            name="uq_mission_template_org_code",
        ),
        {"schema": "mission_design"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    version: Mapped[int] = mapped_column(BigInteger, default=1)
    organization_context_id: Mapped[UUID]
    code: Mapped[str] = mapped_column(String(128))
    name: Mapped[str] = mapped_column(String(255))
    created_by: Mapped[UUID]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class MissionVersion(Base):
    __tablename__ = "mission_versions"
    __table_args__ = (
        UniqueConstraint(
            "template_id",
            "version_number",
            name="uq_mission_version_template_number",
        ),
        {"schema": "mission_design"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    aggregate_version: Mapped[int] = mapped_column(BigInteger, default=1)
    template_id: Mapped[UUID] = mapped_column(
        ForeignKey("mission_design.mission_templates.id")
    )
    version_number: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(255))
    purpose: Mapped[str] = mapped_column(Text)
    objective: Mapped[str] = mapped_column(Text)
    primary_capability_version_id: Mapped[UUID]
    mission_mode: Mapped[str] = mapped_column(String(32))
    difficulty: Mapped[str] = mapped_column(String(8))
    world_context: Mapped[dict] = mapped_column(JSONB)
    actors: Mapped[list] = mapped_column(JSONB)
    information_items: Mapped[list] = mapped_column(JSONB)
    constraints: Mapped[list] = mapped_column(JSONB)
    decision_points: Mapped[list] = mapped_column(JSONB)
    consequence_rules: Mapped[list] = mapped_column(JSONB)
    evidence_opportunities: Mapped[list] = mapped_column(JSONB)
    replay_policy: Mapped[dict] = mapped_column(JSONB)
    safety_policy: Mapped[dict] = mapped_column(JSONB)
    created_by: Mapped[UUID]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    validated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    activated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    retired_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
