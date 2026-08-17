import pytest

from app.domains.identity import (
    ActorContext,
    Capability,
    SigningNotAuthorizedError,
    sign_identity,
)
from app.domains.identity.signer import DevelopmentOnlySigner
from tests.identity_fixtures import (
    make_batch,
    make_key,
    make_manufacturer,
    make_product,
    make_reserved_identity,
)


def _setup(db):
    signer = DevelopmentOnlySigner()
    manufacturer = make_manufacturer(db, name="Synthetic Manufacturer (AREA D)")
    key = make_key(db, manufacturer, signer, key_version=1)
    product = make_product(db, manufacturer, product_ref="AREAD-PRODUCT")
    batch = make_batch(db, product, batch_ref="AREAD-BATCH")
    return signer, key, batch


def test_production_order_authority_does_not_imply_signing_authority(identity_db_session):
    signer, key, batch = _setup(identity_db_session)
    reserved = make_reserved_identity(identity_db_session, batch)
    identity_db_session.commit()

    production_only_actor = ActorContext(
        actor_id="production-order-only-actor",
        capabilities=frozenset({Capability.CREATE_PRODUCTION_ORDER}),
    )

    with pytest.raises(SigningNotAuthorizedError):
        sign_identity(
            identity_db_session,
            identity=reserved,
            manufacturer_key=key.manufacturer_key,
            signer=signer,
            key_handle=key.key_handle,
            actor=production_only_actor,
        )


def test_explicit_signing_authority_succeeds(identity_db_session):
    signer, key, batch = _setup(identity_db_session)
    reserved = make_reserved_identity(identity_db_session, batch)
    identity_db_session.commit()

    signing_actor = ActorContext(
        actor_id="signing-authority-actor",
        capabilities=frozenset({Capability.AUTHORIZE_SIGNING}),
    )

    signed = sign_identity(
        identity_db_session,
        identity=reserved,
        manufacturer_key=key.manufacturer_key,
        signer=signer,
        key_handle=key.key_handle,
        actor=signing_actor,
    )
    identity_db_session.commit()
    assert signed.signature is not None


def test_actor_with_no_capabilities_fails(identity_db_session):
    signer, key, batch = _setup(identity_db_session)
    reserved = make_reserved_identity(identity_db_session, batch)
    identity_db_session.commit()

    bare_actor = ActorContext(actor_id="no-capability-actor")

    with pytest.raises(SigningNotAuthorizedError):
        sign_identity(
            identity_db_session,
            identity=reserved,
            manufacturer_key=key.manufacturer_key,
            signer=signer,
            key_handle=key.key_handle,
            actor=bare_actor,
        )


def test_unauthorized_attempt_creates_no_event_or_mutation(identity_db_session):
    signer, key, batch = _setup(identity_db_session)
    reserved = make_reserved_identity(identity_db_session, batch)
    identity_db_session.commit()
    event_count_before = len(reserved.events)

    production_only_actor = ActorContext(
        actor_id="production-order-only-actor-2",
        capabilities=frozenset({Capability.CREATE_PRODUCTION_ORDER}),
    )

    with pytest.raises(SigningNotAuthorizedError):
        sign_identity(
            identity_db_session,
            identity=reserved,
            manufacturer_key=key.manufacturer_key,
            signer=signer,
            key_handle=key.key_handle,
            actor=production_only_actor,
        )

    assert len(reserved.events) == event_count_before
    assert reserved.signature is None
    assert reserved.manufacturer_key_id is None


def test_actor_holding_both_capabilities_can_still_sign(identity_db_session):
    signer, key, batch = _setup(identity_db_session)
    reserved = make_reserved_identity(identity_db_session, batch)
    identity_db_session.commit()

    full_actor = ActorContext(
        actor_id="full-actor",
        capabilities=frozenset({Capability.CREATE_PRODUCTION_ORDER, Capability.AUTHORIZE_SIGNING}),
    )

    signed = sign_identity(
        identity_db_session,
        identity=reserved,
        manufacturer_key=key.manufacturer_key,
        signer=signer,
        key_handle=key.key_handle,
        actor=full_actor,
    )
    identity_db_session.commit()
    assert signed.signature is not None


def test_signed_event_records_actor_id(identity_db_session):
    signer, key, batch = _setup(identity_db_session)
    reserved = make_reserved_identity(identity_db_session, batch)
    identity_db_session.commit()

    signing_actor = ActorContext(
        actor_id="audited-signing-actor",
        capabilities=frozenset({Capability.AUTHORIZE_SIGNING}),
    )
    signed = sign_identity(
        identity_db_session,
        identity=reserved,
        manufacturer_key=key.manufacturer_key,
        signer=signer,
        key_handle=key.key_handle,
        actor=signing_actor,
    )
    identity_db_session.commit()

    sign_event = sorted(signed.events, key=lambda e: e.sequence)[-1]
    assert sign_event.actor == "audited-signing-actor"
