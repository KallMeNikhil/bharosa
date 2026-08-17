import pytest
from sqlalchemy.exc import IntegrityError

from app.domains.identity import (
    CrossManufacturerKeyMismatchError,
    IdentityEventType,
    LifecycleState,
    sign_identity,
)
from app.domains.identity.signer import DevelopmentOnlySigner
from tests.identity_fixtures import (
    FULLY_AUTHORIZED_TEST_ACTOR,
    make_batch,
    make_key,
    make_manufacturer,
    make_product,
    make_reserved_identity,
)


def _two_manufacturer_setup(db):
    signer = DevelopmentOnlySigner()
    manufacturer_a = make_manufacturer(db, name="Synthetic Manufacturer A (AREA B)")
    key_a = make_key(db, manufacturer_a, signer, key_version=1)
    product_a = make_product(db, manufacturer_a, product_ref="AREAB-A-PRODUCT")
    batch_a = make_batch(db, product_a, batch_ref="AREAB-A-BATCH")

    manufacturer_b = make_manufacturer(db, name="Synthetic Manufacturer B (AREA B)")
    key_b = make_key(db, manufacturer_b, signer, key_version=1)

    return signer, manufacturer_a, key_a, batch_a, manufacturer_b, key_b


def test_same_manufacturer_key_and_product_succeeds(identity_db_session):
    signer, manufacturer_a, key_a, batch_a, _manufacturer_b, _key_b = _two_manufacturer_setup(
        identity_db_session
    )
    reserved = make_reserved_identity(identity_db_session, batch_a)
    identity_db_session.commit()

    signed = sign_identity(
        identity_db_session,
        identity=reserved,
        manufacturer_key=key_a.manufacturer_key,
        signer=signer,
        key_handle=key_a.key_handle,
        actor=FULLY_AUTHORIZED_TEST_ACTOR,
    )
    identity_db_session.commit()

    assert signed.lifecycle_state == LifecycleState.SIGNED
    assert signed.manufacturer_key_id == key_a.manufacturer_key.id
    assert signed.manufacturer_id == manufacturer_a.id


def test_cross_manufacturer_key_and_product_fails(identity_db_session):
    signer, _manufacturer_a, _key_a, batch_a, _manufacturer_b, key_b = _two_manufacturer_setup(
        identity_db_session
    )
    reserved = make_reserved_identity(identity_db_session, batch_a)
    identity_db_session.commit()

    with pytest.raises(CrossManufacturerKeyMismatchError):
        sign_identity(
            identity_db_session,
            identity=reserved,
            manufacturer_key=key_b.manufacturer_key,
            signer=signer,
            key_handle=key_b.key_handle,
            actor=FULLY_AUTHORIZED_TEST_ACTOR,
        )


def test_cross_manufacturer_association_cannot_silently_persist(identity_db_session):
    signer, _manufacturer_a, _key_a, batch_a, _manufacturer_b, key_b = _two_manufacturer_setup(
        identity_db_session
    )
    reserved = make_reserved_identity(identity_db_session, batch_a)
    identity_db_session.commit()

    with pytest.raises(CrossManufacturerKeyMismatchError):
        sign_identity(
            identity_db_session,
            identity=reserved,
            manufacturer_key=key_b.manufacturer_key,
            signer=signer,
            key_handle=key_b.key_handle,
            actor=FULLY_AUTHORIZED_TEST_ACTOR,
        )

    assert reserved.manufacturer_key_id is None
    assert reserved.signature is None
    assert reserved.canonical_payload is None
    assert reserved.lifecycle_state == LifecycleState.RESERVED


def test_failed_cross_manufacturer_attempt_creates_no_invalid_event(identity_db_session):
    signer, _manufacturer_a, _key_a, batch_a, _manufacturer_b, key_b = _two_manufacturer_setup(
        identity_db_session
    )
    reserved = make_reserved_identity(identity_db_session, batch_a)
    identity_db_session.commit()
    event_count_before = len(reserved.events)

    with pytest.raises(CrossManufacturerKeyMismatchError):
        sign_identity(
            identity_db_session,
            identity=reserved,
            manufacturer_key=key_b.manufacturer_key,
            signer=signer,
            key_handle=key_b.key_handle,
            actor=FULLY_AUTHORIZED_TEST_ACTOR,
        )

    assert len(reserved.events) == event_count_before
    assert [e.event_type for e in reserved.events] == [IdentityEventType.RESERVED]


def test_existing_valid_workflow_unaffected_by_ownership_check(identity_db_session):
    from tests.identity_fixtures import full_signed_fixture

    fx = full_signed_fixture(identity_db_session)
    identity_ = fx["identity"]
    assert identity_.lifecycle_state == LifecycleState.SIGNED
    assert identity_.manufacturer_id == fx["manufacturer"].id
    assert identity_.manufacturer_key_id == fx["issued_key"].manufacturer_key.id


def test_database_level_backstop_rejects_forced_cross_manufacturer_key(identity_db_session):
    _signer, _manufacturer_a, _key_a, batch_a, _manufacturer_b, key_b = _two_manufacturer_setup(
        identity_db_session
    )
    reserved = make_reserved_identity(identity_db_session, batch_a)
    identity_db_session.commit()

    reserved.manufacturer_key_id = key_b.manufacturer_key.id
    reserved.canonical_payload = b"forced-bypass-payload"
    reserved.signature = b"x" * 64

    with pytest.raises(IntegrityError):
        identity_db_session.commit()
    identity_db_session.rollback()
