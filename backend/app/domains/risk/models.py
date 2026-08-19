from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    LargeBinary,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domains.risk.correlation import ConfidenceLevel


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def _enum_column(enum_cls: type[enum.Enum], length: int = 32):
    return SAEnum(
        enum_cls,
        native_enum=False,
        length=length,
        values_callable=lambda e: [member.value for member in e],
    )


class RiskAssessment(Base):
    __tablename__ = "risk_assessment"
    __table_args__ = (
        UniqueConstraint("identity_id", "sequence", name="uq_risk_assessment_sequence"),
        UniqueConstraint("event_hash", name="uq_risk_assessment_hash"),
        CheckConstraint("window_end >= window_start", name="ck_risk_assessment_window"),
        ForeignKeyConstraint(
            ["identity_id", "manufacturer_id"],
            ["identity_product_identity.id", "identity_product_identity.manufacturer_id"],
            name="fk_risk_assessment_identity_belongs_to_manufacturer",
        ),
        Index("ix_risk_assessment_manufacturer_id", "manufacturer_id"),
        Index("ix_risk_assessment_identity_id", "identity_id"),
        Index("ix_risk_assessment_confidence", "confidence"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    manufacturer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity_manufacturer.id"), nullable=False
    )
    identity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)

    ruleset_version: Mapped[int] = mapped_column(Integer, nullable=False)
    prior_log_odds: Mapped[float] = mapped_column(Float, nullable=False)
    posterior_log_odds: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[ConfidenceLevel] = mapped_column(
        _enum_column(ConfidenceLevel), nullable=False
    )

    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    previous_event_hash: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    event_hash: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

    contributions: Mapped[list[RiskAssessmentContribution]] = relationship(
        back_populates="assessment",
        cascade="all, delete-orphan",
        order_by="RiskAssessmentContribution.contributed_log_odds.desc()",
    )


class RiskAssessmentContribution(Base):
    __tablename__ = "risk_assessment_contribution"
    __table_args__ = (
        UniqueConstraint(
            "assessment_id", "evidence_id", name="uq_risk_contribution_assessment_evidence"
        ),
        Index("ix_risk_contribution_assessment_id", "assessment_id"),
        Index("ix_risk_contribution_manufacturer_id", "manufacturer_id"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("risk_assessment.id"), nullable=False
    )
    manufacturer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity_manufacturer.id"), nullable=False
    )
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("detection_evidence.id"), nullable=False
    )
    weight: Mapped[float] = mapped_column(Float, nullable=False)
    contributed_log_odds: Mapped[float] = mapped_column(Float, nullable=False)
    benign_explanation: Mapped[str] = mapped_column(String(500), nullable=False)

    assessment: Mapped[RiskAssessment] = relationship(back_populates="contributions")
