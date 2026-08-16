import inspect

from app.domains.identity import (
    AuthenticityResult,
    LifecycleState,
    Signer,
    verify_cryptographic_authenticity,
)
from app.domains.identity.signer import DevelopmentOnlySigner
from tests.identity_fixtures import (
    full_signed_fixture,
    make_batch,
    make_key,
    make_manufacturer,
    make_product,
    make_signed_identity,
)


def test_verify_cryptographic_authenticity_passes_for_untampered_identity(identity_db_session):
    fx = full_signed_fixture(identity_db_session)
    result = verify_cryptographic_authenticity(fx["identity"])
    assert isinstance(result, AuthenticityResult)
    assert result.is_valid is True


def test_verify_fails_if_canonical_payload_tampered_after_signing(identity_db_session):
    fx = full_signed_fixture(identity_db_session)
    identity = fx["identity"]
    identity.canonical_payload = identity.canonical_payload + b"\x00"
    result = verify_cryptographic_authenticity(identity)
    assert result.is_valid is False


def test_verify_fails_if_signature_tampered(identity_db_session):
    fx = full_signed_fixture(identity_db_session)
    identity = fx["identity"]
    tampered = bytearray(identity.signature)
    tampered[0] ^= 0xFF
    identity.signature = bytes(tampered)
    result = verify_cryptographic_authenticity(identity)
    assert result.is_valid is False


def test_cross_manufacturer_key_cannot_validate_other_manufacturers_identity(identity_db_session):
    signer = DevelopmentOnlySigner()

    manufacturer_a = make_manufacturer(identity_db_session, name="Synthetic Manufacturer A")
    key_a = make_key(identity_db_session, manufacturer_a, signer, key_version=1)
    product_a = make_product(identity_db_session, manufacturer_a, product_ref="A-PRODUCT")
    batch_a = make_batch(identity_db_session, product_a, batch_ref="A-BATCH")
    identity_a = make_signed_identity(
        identity_db_session,
        batch_a,
        key_a.manufacturer_key,
        signer,
        key_a.key_handle,
        serial="A-SERIAL-1",
    )

    manufacturer_b = make_manufacturer(identity_db_session, name="Synthetic Manufacturer B")
    key_b = make_key(identity_db_session, manufacturer_b, signer, key_version=1)
    identity_db_session.commit()

    assert (
        Signer.verify(
            key_b.manufacturer_key.public_key, identity_a.canonical_payload, identity_a.signature
        )
        is False
    )
    assert (
        Signer.verify(
            key_a.manufacturer_key.public_key, identity_a.canonical_payload, identity_a.signature
        )
        is True
    )


def test_manufacturer_key_table_has_no_private_key_column():
    from app.domains.identity import ManufacturerKey

    columns = {c.name for c in ManufacturerKey.__table__.columns}
    assert "private_key" not in columns
    assert "seed" not in columns
    assert "secret" not in columns


def test_development_signer_has_no_disk_or_env_persistence_calls():
    source = inspect.getsource(DevelopmentOnlySigner)
    forbidden = ["open(", "os.environ[", "os.putenv", "logging.", "print("]
    for token in forbidden:
        assert token not in source, f"DevelopmentOnlySigner source unexpectedly contains {token!r}"


def test_identity_no_signature_before_signing_returns_invalid(identity_db_session):
    from tests.identity_fixtures import (
        make_batch,
        make_manufacturer,
        make_product,
        make_reserved_identity,
    )

    manufacturer = make_manufacturer(identity_db_session)
    product = make_product(identity_db_session, manufacturer)
    batch = make_batch(identity_db_session, product)
    identity = make_reserved_identity(identity_db_session, batch)
    identity_db_session.commit()

    assert identity.lifecycle_state == LifecycleState.RESERVED
    result = verify_cryptographic_authenticity(identity)
    assert result.is_valid is False
    assert "not been signed" in result.reason
