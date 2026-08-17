from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.domains.identity import (
    ActorContext,
    Batch,
    Capability,
    IssuedKey,
    Manufacturer,
    ManufacturerKey,
    Product,
    ProductIdentity,
    Signer,
    issue_manufacturer_key,
    open_batch,
    register_manufacturer,
    register_product,
    reserve_identity,
    sign_identity,
)
from app.domains.identity.signer import DevelopmentOnlySigner
from tests.tenancy_helpers import scope_to

FULLY_AUTHORIZED_TEST_ACTOR = ActorContext(
    actor_id="synthetic-test-actor",
    capabilities=frozenset(Capability),
)

SIGNING_ONLY_TEST_ACTOR = ActorContext(
    actor_id="synthetic-signing-only-actor",
    capabilities=frozenset({Capability.AUTHORIZE_SIGNING}),
)


def make_manufacturer(db: Session, name: str = "Synthetic Test Manufacturer") -> Manufacturer:
    manufacturer = register_manufacturer(db, name=name)
    scope_to(db, manufacturer.id)
    return manufacturer


def make_key(
    db: Session,
    manufacturer: Manufacturer,
    signer: Signer,
    key_version: int = 1,
    actor: ActorContext | None = None,
) -> IssuedKey:
    return issue_manufacturer_key(
        db,
        manufacturer_id=manufacturer.id,
        signer=signer,
        key_version=key_version,
        actor=actor or FULLY_AUTHORIZED_TEST_ACTOR,
    )


def make_product(
    db: Session,
    manufacturer: Manufacturer,
    product_ref: str = "SYN-PRODUCT-001",
    gtin: str | None = "09520123456788",
) -> Product:
    return register_product(
        db,
        manufacturer_id=manufacturer.id,
        product_ref=product_ref,
        name="Synthetic Test Product",
        gtin=gtin,
    )


def make_batch(db: Session, product: Product, batch_ref: str = "SYN-BATCH-001") -> Batch:
    return open_batch(
        db,
        product_id=product.id,
        batch_ref=batch_ref,
        manufacturing_date=date(2026, 1, 1),
        expiry_date=date(2028, 1, 1),
    )


def make_reserved_identity(
    db: Session, batch: Batch, serial: str | None = None
) -> ProductIdentity:
    return reserve_identity(db, batch_id=batch.id, serial=serial)


def make_signed_identity(
    db: Session,
    batch: Batch,
    manufacturer_key: ManufacturerKey,
    signer: Signer,
    key_handle: str,
    serial: str | None = None,
    actor: ActorContext | None = None,
) -> ProductIdentity:
    identity = make_reserved_identity(db, batch, serial=serial)
    return sign_identity(
        db,
        identity=identity,
        manufacturer_key=manufacturer_key,
        signer=signer,
        key_handle=key_handle,
        actor=actor or FULLY_AUTHORIZED_TEST_ACTOR,
    )


def full_signed_fixture(db: Session, signer: DevelopmentOnlySigner | None = None):
    signer = signer or DevelopmentOnlySigner()
    manufacturer = make_manufacturer(db)
    issued = make_key(db, manufacturer, signer)
    product = make_product(db, manufacturer)
    batch = make_batch(db, product)
    identity = make_signed_identity(db, batch, issued.manufacturer_key, signer, issued.key_handle)
    db.commit()
    return {
        "signer": signer,
        "manufacturer": manufacturer,
        "issued_key": issued,
        "product": product,
        "batch": batch,
        "identity": identity,
    }
