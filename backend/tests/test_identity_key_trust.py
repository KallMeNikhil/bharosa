from app.domains.identity import (
    AuthenticityResult,
    KeyStatus,
    Signer,
    mark_manufacturer_key_compromised,
    revoke_manufacturer_key,
    verify_cryptographic_authenticity,
)
from tests.identity_fixtures import full_signed_fixture


def test_compromised_is_a_distinct_key_status_from_revoked():
    assert KeyStatus.COMPROMISED != KeyStatus.REVOKED
    assert {s.value for s in KeyStatus} == {"ACTIVE", "ROTATED", "REVOKED", "COMPROMISED"}


def test_revoke_manufacturer_key_sets_status(identity_db_session):
    fx = full_signed_fixture(identity_db_session)
    key = fx["issued_key"].manufacturer_key
    assert key.status == KeyStatus.ACTIVE

    revoke_manufacturer_key(identity_db_session, key=key)
    identity_db_session.commit()
    assert key.status == KeyStatus.REVOKED


def test_mark_manufacturer_key_compromised_sets_status(identity_db_session):
    fx = full_signed_fixture(identity_db_session)
    key = fx["issued_key"].manufacturer_key
    assert key.status == KeyStatus.ACTIVE

    mark_manufacturer_key_compromised(identity_db_session, key=key)
    identity_db_session.commit()
    assert key.status == KeyStatus.COMPROMISED


def test_revoking_a_key_does_not_touch_already_signed_identity(identity_db_session):
    fx = full_signed_fixture(identity_db_session)
    identity_ = fx["identity"]
    payload_before = identity_.canonical_payload
    signature_before = identity_.signature

    revoke_manufacturer_key(identity_db_session, key=fx["issued_key"].manufacturer_key)
    identity_db_session.commit()

    assert identity_.canonical_payload == payload_before
    assert identity_.signature == signature_before


def test_active_key_valid_signature(identity_db_session):
    fx = full_signed_fixture(identity_db_session)
    result = verify_cryptographic_authenticity(fx["identity"])
    assert isinstance(result, AuthenticityResult)
    assert result.signature_valid is True
    assert result.key_status == KeyStatus.ACTIVE
    assert result.is_valid is True


def test_active_key_invalid_signature(identity_db_session):
    fx = full_signed_fixture(identity_db_session)
    identity_ = fx["identity"]
    tampered = bytearray(identity_.signature)
    tampered[0] ^= 0xFF
    identity_.signature = bytes(tampered)

    result = verify_cryptographic_authenticity(identity_)
    assert result.signature_valid is False
    assert result.key_status == KeyStatus.ACTIVE
    assert result.is_valid is False


def test_revoked_key_mathematically_valid_signature_is_not_currently_trusted(
    identity_db_session,
):
    fx = full_signed_fixture(identity_db_session)
    identity_ = fx["identity"]
    revoke_manufacturer_key(identity_db_session, key=fx["issued_key"].manufacturer_key)
    identity_db_session.commit()

    result = verify_cryptographic_authenticity(identity_)
    assert result.signature_valid is True
    assert result.key_status == KeyStatus.REVOKED
    assert result.is_valid is False


def test_compromised_key_mathematically_valid_signature_is_not_currently_trusted(
    identity_db_session,
):
    fx = full_signed_fixture(identity_db_session)
    identity_ = fx["identity"]
    mark_manufacturer_key_compromised(identity_db_session, key=fx["issued_key"].manufacturer_key)
    identity_db_session.commit()

    result = verify_cryptographic_authenticity(identity_)
    assert result.signature_valid is True
    assert result.key_status == KeyStatus.COMPROMISED
    assert result.is_valid is False


def test_unknown_key_unsigned_identity(identity_db_session):
    from tests.identity_fixtures import (
        make_batch,
        make_manufacturer,
        make_product,
        make_reserved_identity,
    )

    manufacturer = make_manufacturer(identity_db_session)
    product = make_product(identity_db_session, manufacturer)
    batch = make_batch(identity_db_session, product)
    identity_ = make_reserved_identity(identity_db_session, batch)
    identity_db_session.commit()

    result = verify_cryptographic_authenticity(identity_)
    assert result.signature_valid is False
    assert result.key_status is None
    assert result.is_valid is False


def test_tampered_payload_is_signature_invalid_not_key_untrusted(identity_db_session):
    fx = full_signed_fixture(identity_db_session)
    identity_ = fx["identity"]
    identity_.canonical_payload = identity_.canonical_payload + b"\x00"

    result = verify_cryptographic_authenticity(identity_)
    assert result.signature_valid is False
    assert result.key_status == KeyStatus.ACTIVE
    assert result.is_valid is False
    assert "invalid" in result.reason.lower()


def test_tampered_signature_is_signature_invalid(identity_db_session):
    fx = full_signed_fixture(identity_db_session)
    identity_ = fx["identity"]
    tampered = bytearray(identity_.signature)
    tampered[-1] ^= 0xFF
    identity_.signature = bytes(tampered)

    result = verify_cryptographic_authenticity(identity_)
    assert result.signature_valid is False
    assert result.is_valid is False


def test_cross_manufacturer_key_verification_via_signer_directly(identity_db_session):
    from tests.identity_fixtures import make_key, make_manufacturer

    fx = full_signed_fixture(identity_db_session)
    identity_a = fx["identity"]
    signer = fx["signer"]

    manufacturer_b = make_manufacturer(
        identity_db_session, name="Synthetic Manufacturer B (AREA C)"
    )
    key_b = make_key(identity_db_session, manufacturer_b, signer, key_version=1)
    identity_db_session.commit()

    assert (
        Signer.verify(
            key_b.manufacturer_key.public_key, identity_a.canonical_payload, identity_a.signature
        )
        is False
    )


def test_rotated_key_is_still_currently_trusted(identity_db_session):
    fx = full_signed_fixture(identity_db_session)
    identity_ = fx["identity"]
    key = fx["issued_key"].manufacturer_key
    key.status = KeyStatus.ROTATED
    identity_db_session.commit()

    result = verify_cryptographic_authenticity(identity_)
    assert result.signature_valid is True
    assert result.key_status == KeyStatus.ROTATED
    assert result.is_valid is True
