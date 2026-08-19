from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.core.authorization import ActorContext, Capability
from app.core.event_chain import compute_event_hash, next_chain_link
from app.domains.identity.authorization import SigningNotAuthorizedError
from app.domains.identity.canonical import SignedPayloadFields, build_canonical_payload
from app.domains.identity.lifecycle import assert_legal_transition
from app.domains.identity.models import (
    TRUSTED_KEY_STATUSES,
    Batch,
    BatchStatus,
    IdentityEventType,
    IdentityIssuanceEvent,
    KeyEventType,
    KeyStatus,
    LifecycleState,
    Manufacturer,
    ManufacturerKey,
    ManufacturerKeyEvent,
    ManufacturerStatus,
    Product,
    ProductIdentity,
    ProductStatus,
)
from app.domains.identity.serial import assert_well_formed_serial, generate_serial
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

_CAPABILITY_FOR_STATE: dict[LifecycleState, Capability] = {
    LifecycleState.PRINTED: Capability.AUTHORIZE_PRINT,
    LifecycleState.PRINT_VERIFIED: Capability.AUTHORIZE_PRINT,
    LifecycleState.PRINT_REJECTED: Capability.AUTHORIZE_PRINT,
    LifecycleState.RECONCILED: Capability.AUTHORIZE_PRINT,
    LifecycleState.ACTIVATED: Capability.CREATE_PRODUCTION_ORDER,
}

_STATUS_FOR_KEY_EVENT: dict[KeyEventType, KeyStatus] = {
    KeyEventType.ISSUED: KeyStatus.ACTIVE,
    KeyEventType.ROTATED: KeyStatus.ROTATED,
    KeyEventType.REVOKED: KeyStatus.REVOKED,
    KeyEventType.COMPROMISED: KeyStatus.COMPROMISED,
}


@dataclass(frozen=True)
class AuthenticityResult:
    is_valid: bool
    reason: str
    signature_valid: bool
    key_status: KeyStatus | None


@dataclass(frozen=True)
class IssuedKey:
    manufacturer_key: ManufacturerKey
    key_handle: str


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


class KeyNotEligibleForSigningError(ValueError):
    def __init__(self, key_version: int, status: KeyStatus) -> None:
        self.key_version = key_version
        self.status = status
        super().__init__(
            f"Key version {key_version} has status {status.value} and may no "
            f"longer be used for signing. Retired, revoked and compromised key "
            f"versions remain available for verification only."
        )


class UndatedBatchError(ValueError):
    def __init__(self, batch_ref: str) -> None:
        self.batch_ref = batch_ref
        super().__init__(
            f"Batch {batch_ref!r} has no manufacturing_date. manufactured_at is a "
            f"required BHIP1 signed field and cannot be omitted at signing time."
        )


def _record_identity_event(
    db: Session,
    identity: ProductIdentity,
    *,
    previous_state: LifecycleState | None,
    new_state: LifecycleState,
    actor: str | None = None,
    event_metadata: str | None = None,
) -> IdentityIssuanceEvent:
    sequence, previous_event_hash = next_chain_link(
        db,
        sequence_column=IdentityIssuanceEvent.sequence,
        event_hash_column=IdentityIssuanceEvent.event_hash,
        scope_clause=IdentityIssuanceEvent.identity_id == identity.id,
    )
    event_type = _EVENT_TYPE_FOR_STATE[new_state]
    event_hash = compute_event_hash(
        previous_event_hash=previous_event_hash,
        event_kind="identity_issuance_event",
        fields=[
            str(identity.manufacturer_id),
            str(identity.id),
            str(sequence),
            event_type.value,
            previous_state.value if previous_state else None,
            new_state.value,
            actor,
            event_metadata,
        ],
    )
    event = IdentityIssuanceEvent(
        manufacturer_id=identity.manufacturer_id,
        identity_id=identity.id,
        sequence=sequence,
        event_type=event_type,
        previous_state=previous_state,
        new_state=new_state,
        actor=actor,
        event_metadata=event_metadata,
        previous_event_hash=previous_event_hash,
        event_hash=event_hash,
    )
    db.add(event)
    db.flush()
    return event


def _record_key_event(
    db: Session,
    key: ManufacturerKey,
    *,
    event_type: KeyEventType,
    previous_status: KeyStatus | None,
    actor: str | None = None,
    reason: str | None = None,
) -> ManufacturerKeyEvent:
    sequence, previous_event_hash = next_chain_link(
        db,
        sequence_column=ManufacturerKeyEvent.sequence,
        event_hash_column=ManufacturerKeyEvent.event_hash,
        scope_clause=ManufacturerKeyEvent.key_id == key.id,
    )
    new_status = _STATUS_FOR_KEY_EVENT[event_type]
    event_hash = compute_event_hash(
        previous_event_hash=previous_event_hash,
        event_kind="identity_manufacturer_key_event",
        fields=[
            str(key.manufacturer_id),
            str(key.id),
            str(key.key_version),
            str(sequence),
            event_type.value,
            previous_status.value if previous_status else None,
            new_status.value,
            actor,
            reason,
        ],
    )
    event = ManufacturerKeyEvent(
        manufacturer_id=key.manufacturer_id,
        key_id=key.id,
        sequence=sequence,
        event_type=event_type,
        previous_status=previous_status,
        new_status=new_status,
        actor=actor,
        reason=reason,
        previous_event_hash=previous_event_hash,
        event_hash=event_hash,
    )
    db.add(event)
    db.flush()
    return event


def register_manufacturer(
    db: Session, *, name: str, manufacturer_id: uuid.UUID | None = None
) -> Manufacturer:
    """Onboard a manufacturer.

    The identifier is accepted rather than generated so that the caller can
    establish the tenant scope before the row exists. Row-level security
    filters the row a RETURNING clause reads back, so a session that inserts a
    manufacturer it is not scoped to cannot read back even the row it just
    wrote.
    """
    manufacturer = Manufacturer(
        id=manufacturer_id or uuid.uuid4(),
        name=name,
        status=ManufacturerStatus.ACTIVE,
    )
    db.add(manufacturer)
    db.flush()
    return manufacturer


def issue_manufacturer_key(
    db: Session,
    *,
    manufacturer_id: uuid.UUID,
    signer: Signer,
    key_version: int,
    actor: ActorContext,
) -> IssuedKey:
    actor.require(Capability.MANAGE_KEYS)

    generated = signer.generate_key()
    key = ManufacturerKey(
        manufacturer_id=manufacturer_id,
        key_version=key_version,
        public_key=generated.public_key,
        status=KeyStatus.ACTIVE,
    )
    db.add(key)
    db.flush()
    _record_key_event(
        db, key, event_type=KeyEventType.ISSUED, previous_status=None, actor=actor.actor_id
    )
    return IssuedKey(manufacturer_key=key, key_handle=generated.key_handle)


def _change_key_status(
    db: Session,
    *,
    key: ManufacturerKey,
    event_type: KeyEventType,
    actor: ActorContext,
    reason: str | None,
) -> ManufacturerKey:
    actor.require(Capability.MANAGE_KEYS)

    previous_status = key.status
    key.status = _STATUS_FOR_KEY_EVENT[event_type]
    if key.valid_to is None:
        key.valid_to = datetime.now(UTC)
    db.flush()
    _record_key_event(
        db,
        key,
        event_type=event_type,
        previous_status=previous_status,
        actor=actor.actor_id,
        reason=reason,
    )
    return key


def rotate_manufacturer_key(
    db: Session,
    *,
    key: ManufacturerKey,
    signer: Signer,
    actor: ActorContext,
    reason: str | None = None,
) -> IssuedKey:
    _change_key_status(db, key=key, event_type=KeyEventType.ROTATED, actor=actor, reason=reason)
    return issue_manufacturer_key(
        db,
        manufacturer_id=key.manufacturer_id,
        signer=signer,
        key_version=key.key_version + 1,
        actor=actor,
    )


def revoke_manufacturer_key(
    db: Session, *, key: ManufacturerKey, actor: ActorContext, reason: str | None = None
) -> ManufacturerKey:
    return _change_key_status(
        db, key=key, event_type=KeyEventType.REVOKED, actor=actor, reason=reason
    )


def mark_manufacturer_key_compromised(
    db: Session, *, key: ManufacturerKey, actor: ActorContext, reason: str | None = None
) -> ManufacturerKey:
    return _change_key_status(
        db, key=key, event_type=KeyEventType.COMPROMISED, actor=actor, reason=reason
    )


def register_product(
    db: Session,
    *,
    manufacturer_id: uuid.UUID,
    product_ref: str,
    name: str,
    gtin: str | None = None,
) -> Product:
    product = Product(
        manufacturer_id=manufacturer_id,
        product_ref=product_ref,
        name=name,
        gtin=gtin,
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
    product = db.get(Product, product_id)
    if product is None:
        raise ValueError(f"No Product found for product_id={product_id!r}")

    batch = Batch(
        manufacturer_id=product.manufacturer_id,
        product_id=product_id,
        batch_ref=batch_ref,
        manufacturing_date=manufacturing_date,
        expiry_date=expiry_date,
        status=BatchStatus.OPEN,
    )
    db.add(batch)
    db.flush()
    return batch


def reserve_identity(
    db: Session, *, batch_id: uuid.UUID, serial: str | None = None
) -> ProductIdentity:
    batch = db.get(Batch, batch_id)
    if batch is None:
        raise ValueError(f"No Batch found for batch_id={batch_id!r}")

    resolved_serial = generate_serial() if serial is None else assert_well_formed_serial(serial)

    identity = ProductIdentity(
        batch_id=batch_id,
        serial=resolved_serial,
        manufacturer_id=batch.manufacturer_id,
        lifecycle_state=LifecycleState.RESERVED,
    )
    db.add(identity)
    db.flush()
    _record_identity_event(
        db, identity, previous_state=None, new_state=LifecycleState.RESERVED
    )
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

    if manufacturer_key.status is not KeyStatus.ACTIVE:
        raise KeyNotEligibleForSigningError(
            manufacturer_key.key_version, manufacturer_key.status
        )

    batch = identity.batch
    if batch.manufacturing_date is None:
        raise UndatedBatchError(batch.batch_ref)

    signed_at = datetime.now(UTC)
    fields = SignedPayloadFields(
        manufacturer_id=identity.manufacturer_id,
        key_version=manufacturer_key.key_version,
        product_ref=batch.product.product_ref,
        batch_ref=batch.batch_ref,
        serial=identity.serial,
        manufactured_at=batch.manufacturing_date,
        expiry_at=batch.expiry_date,
        physical_security_reference_hash=physical_security_reference_hash,
        issued_at=signed_at.date(),
    )
    canonical_payload = build_canonical_payload(fields)
    signature = signer.sign(key_handle, canonical_payload)

    previous_state = identity.lifecycle_state
    identity.manufacturer_key_id = manufacturer_key.id
    identity.physical_security_reference_hash = physical_security_reference_hash
    identity.canonical_payload = canonical_payload
    identity.signature = signature
    identity.lifecycle_state = LifecycleState.SIGNED
    identity.signed_at = signed_at
    db.flush()

    _record_identity_event(
        db,
        identity,
        previous_state=previous_state,
        new_state=LifecycleState.SIGNED,
        actor=actor.actor_id,
    )
    return identity


def transition_identity(
    db: Session,
    *,
    identity: ProductIdentity,
    new_state: LifecycleState,
    actor: ActorContext,
    event_metadata: str | None = None,
) -> ProductIdentity:
    assert_legal_transition(identity.lifecycle_state, new_state)

    required = _CAPABILITY_FOR_STATE.get(new_state)
    if required is not None:
        actor.require(required)

    previous_state = identity.lifecycle_state
    identity.lifecycle_state = new_state
    if new_state == LifecycleState.ACTIVATED:
        identity.activated_at = datetime.now(UTC)
    db.flush()

    _record_identity_event(
        db,
        identity,
        previous_state=previous_state,
        new_state=new_state,
        actor=actor.actor_id,
        event_metadata=event_metadata,
    )
    return identity


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
