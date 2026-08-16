from __future__ import annotations

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
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


class ManufacturerStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"


class KeyStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    ROTATED = "ROTATED"
    REVOKED = "REVOKED"
    COMPROMISED = "COMPROMISED"


TRUSTED_KEY_STATUSES = frozenset({KeyStatus.ACTIVE, KeyStatus.ROTATED})


class ProductStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"


class BatchStatus(str, enum.Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class LifecycleState(str, enum.Enum):
    RESERVED = "RESERVED"
    SIGNED = "SIGNED"
    PRINTED = "PRINTED"
    PRINT_VERIFIED = "PRINT_VERIFIED"
    RECONCILED = "RECONCILED"
    ACTIVATED = "ACTIVATED"
    PRINT_REJECTED = "PRINT_REJECTED"


class IdentityEventType(str, enum.Enum):
    RESERVED = "RESERVED"
    SIGNED = "SIGNED"
    PRINTED = "PRINTED"
    PRINT_VERIFIED = "PRINT_VERIFIED"
    RECONCILED = "RECONCILED"
    ACTIVATED = "ACTIVATED"
    PRINT_REJECTED = "PRINT_REJECTED"


class Manufacturer(Base):
    __tablename__ = "identity_manufacturer"

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[ManufacturerStatus] = mapped_column(
        _enum_column(ManufacturerStatus), nullable=False, default=ManufacturerStatus.ACTIVE
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    keys: Mapped[list[ManufacturerKey]] = relationship(
        back_populates="manufacturer", cascade="all, delete-orphan"
    )
    products: Mapped[list[Product]] = relationship(
        back_populates="manufacturer", cascade="all, delete-orphan"
    )


class ManufacturerKey(Base):
    __tablename__ = "identity_manufacturer_key"
    __table_args__ = (
        UniqueConstraint("manufacturer_id", "key_version", name="uq_manufacturer_key_version"),
        UniqueConstraint("id", "manufacturer_id", name="uq_manufacturer_key_id_manufacturer"),
        Index("ix_manufacturer_key_manufacturer_id", "manufacturer_id"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    manufacturer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity_manufacturer.id"), nullable=False
    )
    key_version: Mapped[int] = mapped_column(Integer, nullable=False)
    public_key: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    status: Mapped[KeyStatus] = mapped_column(
        _enum_column(KeyStatus), nullable=False, default=KeyStatus.ACTIVE
    )
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    manufacturer: Mapped[Manufacturer] = relationship(back_populates="keys")


class Product(Base):
    __tablename__ = "identity_product"
    __table_args__ = (
        UniqueConstraint("manufacturer_id", "product_ref", name="uq_product_manufacturer_ref"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    manufacturer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity_manufacturer.id"), nullable=False
    )
    product_ref: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[ProductStatus] = mapped_column(
        _enum_column(ProductStatus), nullable=False, default=ProductStatus.ACTIVE
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    manufacturer: Mapped[Manufacturer] = relationship(back_populates="products")
    batches: Mapped[list[Batch]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )


class Batch(Base):
    __tablename__ = "identity_batch"
    __table_args__ = (UniqueConstraint("product_id", "batch_ref", name="uq_batch_product_ref"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity_product.id"), nullable=False
    )
    batch_ref: Mapped[str] = mapped_column(String(64), nullable=False)
    manufacturing_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[BatchStatus] = mapped_column(
        _enum_column(BatchStatus), nullable=False, default=BatchStatus.OPEN
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    product: Mapped[Product] = relationship(back_populates="batches")
    identities: Mapped[list[ProductIdentity]] = relationship(
        back_populates="batch", cascade="all, delete-orphan"
    )


class ProductIdentity(Base):
    __tablename__ = "identity_product_identity"
    __table_args__ = (
        UniqueConstraint("serial", name="uq_identity_serial"),
        Index("ix_identity_batch_id", "batch_id"),
        Index("ix_identity_manufacturer_key_id", "manufacturer_key_id"),
        Index("ix_identity_manufacturer_id", "manufacturer_id"),
        CheckConstraint(
            "lifecycle_state IN ("
            "'RESERVED','SIGNED','PRINTED','PRINT_VERIFIED','RECONCILED','ACTIVATED','PRINT_REJECTED'"
            ")",
            name="ck_identity_lifecycle_state",
        ),
        ForeignKeyConstraint(
            ["manufacturer_key_id", "manufacturer_id"],
            ["identity_manufacturer_key.id", "identity_manufacturer_key.manufacturer_id"],
            name="fk_identity_key_belongs_to_identity_manufacturer",
        ),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity_batch.id"), nullable=False
    )
    serial: Mapped[str] = mapped_column(String(64), nullable=False)

    manufacturer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity_manufacturer.id"), nullable=False
    )

    manufacturer_key_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    physical_security_reference_hash: Mapped[bytes | None] = mapped_column(
        LargeBinary, nullable=True
    )

    canonical_payload: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    signature: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)

    lifecycle_state: Mapped[LifecycleState] = mapped_column(
        _enum_column(LifecycleState), nullable=False, default=LifecycleState.RESERVED
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    batch: Mapped[Batch] = relationship(back_populates="identities")
    manufacturer_key: Mapped[ManufacturerKey | None] = relationship()
    events: Mapped[list[IdentityIssuanceEvent]] = relationship(
        back_populates="identity",
        cascade="all, delete-orphan",
        order_by="IdentityIssuanceEvent.sequence",
    )


class IdentityIssuanceEvent(Base):
    __tablename__ = "identity_issuance_event"
    __table_args__ = (
        UniqueConstraint("identity_id", "sequence", name="uq_event_identity_sequence"),
        Index("ix_event_identity_id", "identity_id"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    identity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity_product_identity.id"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[IdentityEventType] = mapped_column(
        _enum_column(IdentityEventType), nullable=False
    )
    previous_state: Mapped[LifecycleState | None] = mapped_column(
        _enum_column(LifecycleState), nullable=True
    )
    new_state: Mapped[LifecycleState] = mapped_column(
        _enum_column(LifecycleState), nullable=False
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    actor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    event_metadata: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    identity: Mapped[ProductIdentity] = relationship(back_populates="events")
