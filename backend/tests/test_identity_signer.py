import base64

import pytest

from app.core.config import Settings
from app.domains.identity import (
    DevelopmentOnlySigner,
    MasterKeyDerivedSigner,
    NoProductionSignerConfiguredError,
    Signer,
    get_signer,
)


def test_generate_key_returns_only_public_material():
    signer = DevelopmentOnlySigner()
    generated = signer.generate_key()
    assert isinstance(generated.public_key, bytes)
    assert len(generated.public_key) == 32
    assert isinstance(generated.key_handle, str)
    assert not hasattr(generated, "private_key")


def test_sign_verify_round_trip():
    signer = DevelopmentOnlySigner()
    generated = signer.generate_key()
    payload = b"synthetic-test-payload"
    signature = signer.sign(generated.key_handle, payload)
    assert Signer.verify(generated.public_key, payload, signature) is True


def test_wrong_public_key_fails_verification():
    signer = DevelopmentOnlySigner()
    key_a = signer.generate_key()
    key_b = signer.generate_key()
    payload = b"synthetic-test-payload"
    signature = signer.sign(key_a.key_handle, payload)
    assert Signer.verify(key_b.public_key, payload, signature) is False


def test_changed_payload_fails_verification():
    signer = DevelopmentOnlySigner()
    generated = signer.generate_key()
    payload = b"synthetic-test-payload"
    signature = signer.sign(generated.key_handle, payload)
    assert Signer.verify(generated.public_key, b"tampered-payload", signature) is False


def test_malformed_public_key_fails_verification_without_raising():
    signer = DevelopmentOnlySigner()
    generated = signer.generate_key()
    signature = signer.sign(generated.key_handle, b"payload")
    assert Signer.verify(b"too-short", b"payload", signature) is False


def test_unknown_key_handle_raises():
    signer = DevelopmentOnlySigner()
    with pytest.raises(ValueError):
        signer.sign("not-a-real-handle", b"payload")


def test_two_keys_are_independent():
    signer = DevelopmentOnlySigner()
    key_a = signer.generate_key()
    key_b = signer.generate_key()
    assert key_a.key_handle != key_b.key_handle
    assert key_a.public_key != key_b.public_key


def test_get_signer_returns_development_signer_in_development():
    settings = Settings(_env_file=None, environment="development")
    signer = get_signer(settings)
    assert isinstance(signer, DevelopmentOnlySigner)


def test_get_signer_returns_development_signer_in_test():
    settings = Settings(_env_file=None, environment="test")
    signer = get_signer(settings)
    assert isinstance(signer, DevelopmentOnlySigner)


def test_get_signer_raises_in_production():
    settings = Settings(_env_file=None, environment="production")
    with pytest.raises(NoProductionSignerConfiguredError):
        get_signer(settings)


def test_development_signer_never_exposes_private_key_as_raw_bytes_attribute():
    signer = DevelopmentOnlySigner()
    signer.generate_key()
    state = vars(signer)
    assert set(state.keys()) == {"_private_keys"}
    for value in state["_private_keys"].values():
        assert not isinstance(value, bytes | bytearray | str)


MASTER = base64.b64encode(b"m" * 32).decode()


def test_get_signer_derives_keys_when_a_master_key_is_configured():
    for environment in ("development", "production"):
        settings = Settings(_env_file=None, environment=environment, signing_master_key=MASTER)
        assert isinstance(get_signer(settings), MasterKeyDerivedSigner)


def test_derived_keys_survive_a_new_signer_instance():
    first = MasterKeyDerivedSigner(b"m" * 32)
    key = first.generate_key()
    signature = MasterKeyDerivedSigner(b"m" * 32).sign(key.key_handle, b"payload")
    assert Signer.verify(key.public_key, b"payload", signature)


def test_a_different_master_key_cannot_sign_for_an_existing_key():
    key = MasterKeyDerivedSigner(b"m" * 32).generate_key()
    signature = MasterKeyDerivedSigner(b"x" * 32).sign(key.key_handle, b"payload")
    assert not Signer.verify(key.public_key, b"payload", signature)


def test_a_short_master_key_is_refused():
    with pytest.raises(ValueError):
        MasterKeyDerivedSigner(b"short")
