from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.domains.identity.authorization import ActorContext, Capability, SigningNotAuthorizedError
from app.domains.identity.canonical import SignedPayloadFields, build_canonical_payload
from app.domains.identity.lifecycle import assert_legal_transition
from app.domains.identity.models import (
    TRUSTED_KEY_STATUSES,
    Batch,
    BatchStatus,
    IdentityEventType,
    IdentityIssuanceEvent,
    KeyStatus,
    LifecycleState,
    Manufacturer,
    ManufacturerKey,
    ManufacturerStatus,
    Product,
    ProductIdentity,
    ProductStatus,
)
from app.domains.identity.signer import Signer

_EVENT_TYPE_FOR_STATE: dict[LifecycleState, IdentityEventType] = {
    LifecycleState.RESERVED: IdentityEventType.RESERVED,
    LifecycleState.SIGNED: IdentityEventType.SIGNED,
    LifecycleState.PRINTED: IdentityEventType.PRINTED,
    LifecycleState.PRINT_VERIFIED: IdentityEventType.PRINT_VERIFIED,
    LifecycleState.RECONCILED: IdentityEventType.RECONCILED,
    LifecycleState.ACTIVATED: IdentityEventType.ACTIVATED,
    LifecycleState.PRINT_REJECTED: IdentityEventType.PRINT_REJECTED,
}


@dataclass(frozen=True)
class AuthenticityResult:
    is_valid: bool
    reason: str
    signature_valid: bool
    key_status: KeyStatus | None


class CrossManufacturerKeyMismatchError(ValueError):
    def __init__(self, identity_manufacturer_id, key_manufacturer_id) -> None:  # noqa: ANN001
        self.identity_manufacturer_id = identity_manufacturer_id
        self.key_manufacturer_id = key_manufacturer_id
        super().__init__(
            f"ManufacturerKey belongs to manufacturer {key_manufacturer_id!r}, "
            f"but this ProductIdentity belongs to manufacturer "
            f"{identity_manufacturer_id!r}. A manufacturer's products can only "
            f"ever be signed by that same manufacturer's own key."
        )


def _record_event(
    db: Session,
    identity: ProductIdentity,
    *,
    previous_state: LifecycleState | None,
    new_state: LifecycleState,
    actor: str | None = None,
    event_metadata: str | None = None,
) -> IdentityIssuanceEvent:
    next_sequence = len(identity.events) + 1
    event = IdentityIssuanceEvent(
        identity_id=identity.id,
        sequence=next_sequence,
        event_type=_EVENT_TYPE_FOR_STATE[new_state],
        previous_state=previous_state,
        new_state=new_state,
        actor=actor,
        event_metadata=event_metadata,
    )
    identity.events.append(event)
    return event


def register_manufacturer(db: Session, *, name: str) -> Manufacturer:
    manufacturer = Manufacturer(name=name, status=ManufacturerStatus.ACTIVE)
    db.add(manufacturer)
    db.flush()
    return manufacturer


@dataclass(frozen=True)
class IssuedKey:
    manufacturer_key: ManufacturerKey
    key_handle: str


def issue_manufacturer_key(
    db: Session, *, manufacturer_id: uuid.UUID, signer: Signer, key_version: int
) -> IssuedKey:
    generated = signer.generate_key()
    key = ManufacturerKey(
        manufacturer_id=manufacturer_id,
        key_version=key_version,
        public_key=generated.public_key,
        status=KeyStatus.ACTIVE,
    )
    db.add(key)
    db.flush()
    return IssuedKey(manufacturer_key=key, key_handle=generated.key_handle)


def register_product(
    db: Session, *, manufacturer_id: uuid.UUID, product_ref: str, name: str
) -> Product:
    product = Product(
        manufacturer_id=manufacturer_id,
        product_ref=product_ref,
        name=name,
        status=ProductStatus.ACTIVE,
    )
    db.add(product)
    db.flush()
    return product


def open_batch(
    db: Session,
    *,
    product_id: uuid.UUID,
    batch_ref: str,
    manufacturing_date: date | None = None,
    expiry_date: date | None = None,
) -> Batch:
    batch = Batch(
        product_id=product_id,
        batch_ref=batch_ref,
        manufacturing_date=manufacturing_date,
        expiry_date=expiry_date,
        status=BatchStatus.OPEN,
    )
    db.add(batch)
    db.flush()
    return batch


def reserve_identity(db: Session, *, batch_id: uuid.UUID, serial: str) -> ProductIdentity:
    batch = db.get(Batch, batch_id)
    if batch is None:
        raise ValueError(f"No Batch found for batch_id={batch_id!r}")

    identity = ProductIdentity(
        batch_id=batch_id,
        serial=serial,
        manufacturer_id=batch.product.manufacturer_id,
        lifecycle_state=LifecycleState.RESERVED,
    )
    db.add(identity)
    db.flush()
    _record_event(
        db, identity, previous_state=None, new_state=LifecycleState.RESERVED
    )
    db.flush()
    return identity


def sign_identity(
    db: Session,
    *,
    identity: ProductIdentity,
    manufacturer_key: ManufacturerKey,
    signer: Signer,
    key_handle: str,
    actor: ActorContext,
    physical_security_reference_hash: bytes | None = None,
) -> ProductIdentity:
    if not actor.has(Capability.AUTHORIZE_SIGNING):
        raise SigningNotAuthorizedError(actor.actor_id)

    assert_legal_transition(identity.lifecycle_state, LifecycleState.SIGNED)

    if manufacturer_key.manufacturer_id != identity.manufacturer_id:
        raise CrossManufacturerKeyMismatchError(
            identity_manufacturer_id=identity.manufacturer_id,
            key_manufacturer_id=manufacturer_key.manufacturer_id,
        )

    product: Product = identity.batch.product
    fields = SignedPayloadFields(
        product_ref=product.product_ref,
        serial=identity.serial,
        batch_ref=identity.batch.batch_ref,
        manufacturing_date=identity.batch.manufacturing_date,
        expiry_date=identity.batch.expiry_date,
        key_version=manufacturer_key.key_version,
        physical_security_reference_hash=physical_security_reference_hash,
    )
    canonical_payload = build_canonical_payload(fields)
    signature = signer.sign(key_handle, canonical_payload)

    previous_state = identity.lifecycle_state
    identity.manufacturer_key_id = manufacturer_key.id
    identity.physical_security_reference_hash = physical_security_reference_hash
    identity.canonical_payload = canonical_payload
    identity.signature = signature
    identity.lifecycle_state = LifecycleState.SIGNED
    identity.signed_at = datetime.now(UTC)

    _record_event(
        db,
        identity,
        previous_state=previous_state,
        new_state=LifecycleState.SIGNED,
        actor=actor.actor_id,
    )
    db.flush()
    return identity


def transition_identity(
    db: Session,
    *,
    identity: ProductIdentity,
    new_state: LifecycleState,
    actor: str | None = None,
    event_metadata: str | None = None,
) -> ProductIdentity:
    assert_legal_transition(identity.lifecycle_state, new_state)

    previous_state = identity.lifecycle_state
    identity.lifecycle_state = new_state
    if new_state == LifecycleState.ACTIVATED:
        identity.activated_at = datetime.now(UTC)

    _record_event(
        db,
        identity,
        previous_state=previous_state,
        new_state=new_state,
        actor=actor,
        event_metadata=event_metadata,
    )
    db.flush()
    return identity


def revoke_manufacturer_key(db: Session, *, key: ManufacturerKey) -> ManufacturerKey:
    key.status = KeyStatus.REVOKED
    db.flush()
    return key


def mark_manufacturer_key_compromised(db: Session, *, key: ManufacturerKey) -> ManufacturerKey:
    key.status = KeyStatus.COMPROMISED
    db.flush()
    return key


def verify_cryptographic_authenticity(identity: ProductIdentity) -> AuthenticityResult:
    if identity.canonical_payload is None or identity.signature is None:
        return AuthenticityResult(
            is_valid=False,
            reason="identity has not been signed",
            signature_valid=False,
            key_status=None,
        )
    if identity.manufacturer_key is None:
        return AuthenticityResult(
            is_valid=False,
            reason="identity has no referenced signing key",
            signature_valid=False,
            key_status=None,
        )

    signature_valid = Signer.verify(
        public_key=identity.manufacturer_key.public_key,
        payload=identity.canonical_payload,
        signature=identity.signature,
    )
    key_status = identity.manufacturer_key.status

    if not signature_valid:
        return AuthenticityResult(
            is_valid=False,
            reason="signature invalid for referenced public key",
            signature_valid=False,
            key_status=key_status,
        )

    if key_status not in TRUSTED_KEY_STATUSES:
        return AuthenticityResult(
            is_valid=False,
            reason=(
                f"signature is mathematically valid, but signing key status is "
                f"{key_status.value} and is not currently trusted"
            ),
            signature_valid=True,
            key_status=key_status,
        )

    return AuthenticityResult(
        is_valid=True,
        reason=f"signature valid; signing key currently trusted (status={key_status.value})",
        signature_valid=True,
        key_status=key_status,
    )
