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
from app.domains.detection.signals import FraudFamily, SignalType


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def _enum_column(enum_cls: type[enum.Enum], length: int = 48):
    return SAEnum(
        enum_cls,
        native_enum=False,
        length=length,
        values_callable=lambda e: [member.value for member in e],
    )


class DetectionEvidence(Base):
    __tablename__ = "detection_evidence"
    __table_args__ = (
        UniqueConstraint("identity_id", "sequence", name="uq_detection_evidence_sequence"),
        UniqueConstraint("event_hash", name="uq_detection_evidence_hash"),
        UniqueConstraint(
            "identity_id", "signal_fingerprint", name="uq_detection_evidence_fingerprint"
        ),
        ForeignKeyConstraint(
            ["identity_id", "manufacturer_id"],
            ["identity_product_identity.id", "identity_product_identity.manufacturer_id"],
            name="fk_detection_evidence_identity_belongs_to_manufacturer",
        ),
        CheckConstraint("window_end >= window_start", name="ck_detection_evidence_window"),
        Index("ix_detection_evidence_manufacturer_id", "manufacturer_id"),
        Index("ix_detection_evidence_identity_id", "identity_id"),
        Index("ix_detection_evidence_signal_type", "signal_type"),
        Index("ix_detection_evidence_generated_at", "generated_at"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    manufacturer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity_manufacturer.id"), nullable=False
    )
    identity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)

    detector_id: Mapped[str] = mapped_column(String(64), nullable=False)
    detector_version: Mapped[int] = mapped_column(Integer, nullable=False)
    signal_type: Mapped[SignalType] = mapped_column(_enum_column(SignalType), nullable=False)
    fraud_family: Mapped[FraudFamily] = mapped_column(
        _enum_column(FraudFamily), nullable=False
    )
    log_likelihood_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    explanation: Mapped[str] = mapped_column(String(2000), nullable=False)
    signal_fingerprint: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    previous_event_hash: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    event_hash: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

    sources: Mapped[list[DetectionEvidenceSource]] = relationship(
        back_populates="evidence", cascade="all, delete-orphan"
    )


class DetectionEvidenceSource(Base):
    __tablename__ = "detection_evidence_source"
    __table_args__ = (
        CheckConstraint(
            "(verification_event_id IS NOT NULL)::int "
            "+ (supply_chain_event_id IS NOT NULL)::int "
            "+ (identity_issuance_event_id IS NOT NULL)::int = 1",
            name="ck_detection_evidence_source_exactly_one",
        ),
        Index("ix_detection_evidence_source_evidence_id", "evidence_id"),
        Index("ix_detection_evidence_source_manufacturer_id", "manufacturer_id"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("detection_evidence.id"), nullable=False
    )
    manufacturer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity_manufacturer.id"), nullable=False
    )
    verification_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("verification_event.id"), nullable=True
    )
    supply_chain_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("supply_chain_event.id"), nullable=True
    )
    identity_issuance_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity_issuance_event.id"), nullable=True
    )

    evidence: Mapped[DetectionEvidence] = relationship(back_populates="sources")
