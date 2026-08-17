from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
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


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def _enum_column(enum_cls: type[enum.Enum], length: int = 32):
    return SAEnum(
        enum_cls,
        native_enum=False,
        length=length,
        values_callable=lambda e: [member.value for member in e],
    )


class IncidentStatus(str, enum.Enum):
    OPEN = "OPEN"
    UNDER_REVIEW = "UNDER_REVIEW"
    SUBSTANTIATED = "SUBSTANTIATED"
    DISMISSED = "DISMISSED"


class FraudIncident(Base):
    __tablename__ = "investigation_fraud_incident"
    __table_args__ = (
        ForeignKeyConstraint(
            ["identity_id", "manufacturer_id"],
            ["identity_product_identity.id", "identity_product_identity.manufacturer_id"],
            name="fk_incident_identity_belongs_to_manufacturer",
        ),
        UniqueConstraint("id", "manufacturer_id", name="uq_incident_id_manufacturer"),
        Index("ix_incident_manufacturer_id", "manufacturer_id"),
        Index("ix_incident_identity_id", "identity_id"),
        Index("ix_incident_status", "status"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    manufacturer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity_manufacturer.id"), nullable=False
    )
    identity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    risk_assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("risk_assessment.id"), nullable=False
    )

    status: Mapped[IncidentStatus] = mapped_column(
        _enum_column(IncidentStatus), nullable=False, default=IncidentStatus.OPEN
    )
    summary: Mapped[str] = mapped_column(String(1000), nullable=False)
    opened_by: Mapped[str] = mapped_column(String(255), nullable=False)
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    citations: Mapped[list[IncidentEvidenceCitation]] = relationship(
        back_populates="incident", cascade="all, delete-orphan"
    )
    events: Mapped[list[IncidentEvent]] = relationship(
        back_populates="incident",
        cascade="all, delete-orphan",
        order_by="IncidentEvent.sequence",
        foreign_keys="IncidentEvent.incident_id",
    )


class IncidentEvidenceCitation(Base):
    __tablename__ = "investigation_incident_evidence"
    __table_args__ = (
        UniqueConstraint("incident_id", "evidence_id", name="uq_incident_evidence"),
        Index("ix_incident_evidence_incident_id", "incident_id"),
        Index("ix_incident_evidence_manufacturer_id", "manufacturer_id"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("investigation_fraud_incident.id"), nullable=False
    )
    manufacturer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity_manufacturer.id"), nullable=False
    )
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("detection_evidence.id"), nullable=False
    )

    incident: Mapped[FraudIncident] = relationship(back_populates="citations")


class IncidentEvent(Base):
    __tablename__ = "investigation_incident_event"
    __table_args__ = (
        UniqueConstraint("incident_id", "sequence", name="uq_incident_event_sequence"),
        UniqueConstraint("event_hash", name="uq_incident_event_hash"),
        ForeignKeyConstraint(
            ["incident_id", "manufacturer_id"],
            [
                "investigation_fraud_incident.id",
                "investigation_fraud_incident.manufacturer_id",
            ],
            name="fk_incident_event_incident_belongs_to_manufacturer",
        ),
        Index("ix_incident_event_incident_id", "incident_id"),
        Index("ix_incident_event_manufacturer_id", "manufacturer_id"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("investigation_fraud_incident.id"), nullable=False
    )
    manufacturer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity_manufacturer.id"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    previous_status: Mapped[IncidentStatus | None] = mapped_column(
        _enum_column(IncidentStatus), nullable=True
    )
    new_status: Mapped[IncidentStatus] = mapped_column(
        _enum_column(IncidentStatus), nullable=False
    )
    note: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    previous_event_hash: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    event_hash: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

    incident: Mapped[FraudIncident] = relationship(
        back_populates="events", foreign_keys="IncidentEvent.incident_id"
    )
