from __future__ import annotations

import enum
import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import (
    CheckConstraint,
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


class ParticipantRole(str, enum.Enum):
    DEPOT = "DEPOT"
    DISTRIBUTOR = "DISTRIBUTOR"
    RETAILER = "RETAILER"


class SupplyChainEventType(str, enum.Enum):
    DISPATCH = "DISPATCH"
    RECEIPT = "RECEIPT"
    TRANSFER = "TRANSFER"
    RETURN = "RETURN"
    REALLOCATION = "REALLOCATION"
    RETAIL_PLACEMENT = "RETAIL_PLACEMENT"
    CUSTODY_ADJUSTMENT = "CUSTODY_ADJUSTMENT"


class SupplyChainParticipant(Base):
    __tablename__ = "supply_chain_participant"
    __table_args__ = (
        UniqueConstraint(
            "manufacturer_id", "participant_ref", name="uq_participant_manufacturer_ref"
        ),
        UniqueConstraint("id", "manufacturer_id", name="uq_participant_id_manufacturer"),
        Index("ix_participant_manufacturer_id", "manufacturer_id"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    manufacturer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity_manufacturer.id"), nullable=False
    )
    participant_ref: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[ParticipantRole] = mapped_column(_enum_column(ParticipantRole), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Territory(Base):
    __tablename__ = "supply_chain_territory"
    __table_args__ = (
        UniqueConstraint(
            "manufacturer_id", "territory_ref", name="uq_territory_manufacturer_ref"
        ),
        UniqueConstraint("id", "manufacturer_id", name="uq_territory_id_manufacturer"),
        Index("ix_territory_manufacturer_id", "manufacturer_id"),
        CheckConstraint("ST_IsValid(boundary)", name="ck_territory_boundary_valid"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    manufacturer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity_manufacturer.id"), nullable=False
    )
    territory_ref: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    boundary: Mapped[str] = mapped_column(
        Geometry(geometry_type="MULTIPOLYGON", srid=4326, spatial_index=False),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ChannelAuthorization(Base):
    __tablename__ = "supply_chain_channel_authorization"
    __table_args__ = (
        ForeignKeyConstraint(
            ["participant_id", "manufacturer_id"],
            ["supply_chain_participant.id", "supply_chain_participant.manufacturer_id"],
            name="fk_authorization_participant_belongs_to_manufacturer",
        ),
        ForeignKeyConstraint(
            ["territory_id", "manufacturer_id"],
            ["supply_chain_territory.id", "supply_chain_territory.manufacturer_id"],
            name="fk_authorization_territory_belongs_to_manufacturer",
        ),
        CheckConstraint(
            "valid_until IS NULL OR valid_until > valid_from",
            name="ck_authorization_valid_range",
        ),
        Index("ix_authorization_manufacturer_id", "manufacturer_id"),
        Index("ix_authorization_participant_id", "participant_id"),
        Index("ix_authorization_territory_id", "territory_id"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    manufacturer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity_manufacturer.id"), nullable=False
    )
    participant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    territory_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SupplyChainEvent(Base):
    __tablename__ = "supply_chain_event"
    __table_args__ = (
        UniqueConstraint("id", "manufacturer_id", name="uq_event_id_manufacturer"),
        UniqueConstraint("identity_id", "sequence", name="uq_supply_chain_event_sequence"),
        UniqueConstraint("event_hash", name="uq_supply_chain_event_hash"),
        ForeignKeyConstraint(
            ["identity_id", "manufacturer_id"],
            ["identity_product_identity.id", "identity_product_identity.manufacturer_id"],
            name="fk_event_identity_belongs_to_manufacturer",
        ),
        ForeignKeyConstraint(
            ["related_identity_id", "manufacturer_id"],
            ["identity_product_identity.id", "identity_product_identity.manufacturer_id"],
            name="fk_event_related_identity_belongs_to_manufacturer",
        ),
        ForeignKeyConstraint(
            ["source_participant_id", "manufacturer_id"],
            ["supply_chain_participant.id", "supply_chain_participant.manufacturer_id"],
            name="fk_event_source_participant_belongs_to_manufacturer",
        ),
        ForeignKeyConstraint(
            ["destination_participant_id", "manufacturer_id"],
            ["supply_chain_participant.id", "supply_chain_participant.manufacturer_id"],
            name="fk_event_destination_participant_belongs_to_manufacturer",
        ),
        ForeignKeyConstraint(
            ["related_event_id", "manufacturer_id"],
            ["supply_chain_event.id", "supply_chain_event.manufacturer_id"],
            name="fk_event_related_event_belongs_to_manufacturer",
        ),
        Index("ix_supply_chain_event_manufacturer_id", "manufacturer_id"),
        Index("ix_supply_chain_event_identity_id", "identity_id"),
        Index("ix_supply_chain_event_occurred_at", "occurred_at"),
        Index("ix_supply_chain_event_event_type", "event_type"),
        Index("ix_supply_chain_event_source_participant_id", "source_participant_id"),
        Index(
            "ix_supply_chain_event_destination_participant_id", "destination_participant_id"
        ),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    manufacturer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity_manufacturer.id"), nullable=False
    )
    identity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[SupplyChainEventType] = mapped_column(
        _enum_column(SupplyChainEventType), nullable=False
    )
    source_participant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    destination_participant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    related_event_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    related_identity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    previous_event_hash: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    event_hash: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
