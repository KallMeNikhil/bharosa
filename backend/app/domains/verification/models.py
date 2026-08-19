from __future__ import annotations

import enum
import uuid
from datetime import date, datetime

from geoalchemy2 import Geometry
from sqlalchemy import (
    Date,
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
from sqlalchemy.orm import Mapped, mapped_column

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


class VerificationState(str, enum.Enum):
    GENUINE = "GENUINE"
    CAUTION = "CAUTION"
    INVALID = "INVALID"
    ALREADY_REPORTED = "ALREADY_REPORTED"
    UNAVAILABLE = "UNAVAILABLE"


class VerificationChannel(str, enum.Enum):
    WEB = "WEB"
    API = "API"
    RETAILER_APP = "RETAILER_APP"
    FIELD_INVESTIGATOR = "FIELD_INVESTIGATOR"


class PhysicalCheckResult(str, enum.Enum):
    NOT_PRESENTED = "NOT_PRESENTED"
    MATCHED = "MATCHED"
    MISMATCHED = "MISMATCHED"
    UNREADABLE = "UNREADABLE"


class VerificationEvent(Base):
    __tablename__ = "verification_event"
    __table_args__ = (
        UniqueConstraint("identity_id", "sequence", name="uq_verification_event_sequence"),
        UniqueConstraint("event_hash", name="uq_verification_event_hash"),
        ForeignKeyConstraint(
            ["identity_id", "manufacturer_id"],
            ["identity_product_identity.id", "identity_product_identity.manufacturer_id"],
            name="fk_verification_event_identity_belongs_to_manufacturer",
        ),
        Index("ix_verification_event_manufacturer_id", "manufacturer_id"),
        Index("ix_verification_event_identity_id", "identity_id"),
        Index("ix_verification_event_occurred_at", "occurred_at"),
        Index("ix_verification_event_client_reference_hash", "client_reference_hash"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    manufacturer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity_manufacturer.id"), nullable=False
    )
    identity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)

    state: Mapped[VerificationState] = mapped_column(
        _enum_column(VerificationState), nullable=False
    )
    channel: Mapped[VerificationChannel] = mapped_column(
        _enum_column(VerificationChannel), nullable=False
    )
    signature_valid: Mapped[bool] = mapped_column(nullable=False)
    key_status_at_scan: Mapped[str | None] = mapped_column(String(32), nullable=True)
    lifecycle_state_at_scan: Mapped[str] = mapped_column(String(32), nullable=False)
    physical_check_result: Mapped[PhysicalCheckResult] = mapped_column(
        _enum_column(PhysicalCheckResult),
        nullable=False,
        default=PhysicalCheckResult.NOT_PRESENTED,
    )

    location: Mapped[str | None] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=True
    )
    coarse_cell: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reported_accuracy_m: Mapped[int | None] = mapped_column(Integer, nullable=True)

    client_reference_hash: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)

    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    previous_event_hash: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    event_hash: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)


class UnresolvedScanTally(Base):
    __tablename__ = "verification_unresolved_scan_tally"
    __table_args__ = (
        UniqueConstraint("scan_date", "coarse_cell", name="uq_unresolved_scan_day_cell"),
        Index("ix_unresolved_scan_tally_scan_date", "scan_date"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    scan_date: Mapped[date] = mapped_column(Date, nullable=False)
    coarse_cell: Mapped[str] = mapped_column(String(32), nullable=False)
    scan_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
