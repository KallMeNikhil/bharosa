import uuid
from datetime import date

import pytest

from app.domains.identity import (
    BHIP_SCHEMA_VERSION,
    CanonicalPayloadError,
    SignedPayloadFields,
    build_canonical_payload,
    read_schema_version,
)

MANUFACTURER_ID = uuid.UUID("11111111-2222-3333-4444-555555555555")
OTHER_MANUFACTURER_ID = uuid.UUID("11111111-2222-3333-4444-555555555556")


def _fields(**overrides):
    base = dict(
        manufacturer_id=MANUFACTURER_ID,
        key_version=1,
        product_ref="SYN-PRODUCT-001",
        batch_ref="SYN-BATCH-001",
        serial="AAAAAAAAAAAAAAAAAAAAAAAAAA",
        manufactured_at=date(2026, 1, 1),
        expiry_at=date(2028, 1, 1),
        physical_security_reference_hash=None,
        issued_at=date(2026, 1, 2),
    )
    base.update(overrides)
    return SignedPayloadFields(**base)


def test_same_logical_identity_produces_same_canonical_bytes():
    assert build_canonical_payload(_fields()) == build_canonical_payload(_fields())


def test_schema_version_is_the_first_byte():
    payload = build_canonical_payload(_fields())
    assert payload[0] == BHIP_SCHEMA_VERSION
    assert read_schema_version(payload) == BHIP_SCHEMA_VERSION


def test_canonical_bytes_are_deterministic_across_calls():
    payload = build_canonical_payload(_fields())
    assert {build_canonical_payload(_fields()) for _ in range(5)} == {payload}


def test_every_signed_field_changes_the_canonical_bytes():
    baseline = build_canonical_payload(_fields())
    for override in [
        {"manufacturer_id": OTHER_MANUFACTURER_ID},
        {"key_version": 2},
        {"product_ref": "SYN-PRODUCT-002"},
        {"batch_ref": "SYN-BATCH-002"},
        {"serial": "BAAAAAAAAAAAAAAAAAAAAAAAAA"},
        {"manufactured_at": date(2026, 6, 1)},
        {"expiry_at": date(2029, 1, 1)},
        {"physical_security_reference_hash": b"\x01" * 32},
        {"issued_at": date(2026, 3, 4)},
    ]:
        assert build_canonical_payload(_fields(**override)) != baseline, override


def test_manufacturer_id_is_bound_into_the_signed_payload():
    a = build_canonical_payload(_fields(manufacturer_id=MANUFACTURER_ID))
    b = build_canonical_payload(_fields(manufacturer_id=OTHER_MANUFACTURER_ID))
    assert a != b
    assert MANUFACTURER_ID.bytes in a
    assert MANUFACTURER_ID.bytes not in b


def test_optional_fields_absent_vs_present_are_distinguishable():
    with_hash = build_canonical_payload(
        _fields(physical_security_reference_hash=b"\x00" * 32)
    )
    without_hash = build_canonical_payload(_fields(physical_security_reference_hash=None))
    assert with_hash != without_hash


def test_optional_expiry_absent_encoding():
    assert build_canonical_payload(_fields(expiry_at=None)) != build_canonical_payload(_fields())


def test_length_prefixing_prevents_field_boundary_ambiguity():
    a = build_canonical_payload(_fields(product_ref="AB", batch_ref="CDE"))
    b = build_canonical_payload(_fields(product_ref="ABC", batch_ref="DE"))
    assert a != b


def test_physical_security_reference_hash_must_be_exactly_32_bytes():
    with pytest.raises(ValueError):
        build_canonical_payload(_fields(physical_security_reference_hash=b"\x01" * 31))


def test_empty_opaque_reference_is_rejected():
    for override in [{"product_ref": ""}, {"batch_ref": ""}, {"serial": ""}]:
        with pytest.raises(CanonicalPayloadError):
            build_canonical_payload(_fields(**override))


def test_unsupported_schema_version_is_rejected():
    with pytest.raises(CanonicalPayloadError):
        build_canonical_payload(_fields(), schema_version=99)


def test_field_order_matches_the_frozen_bhip1_layout():
    payload = build_canonical_payload(
        _fields(physical_security_reference_hash=b"\x07" * 32)
    )
    cursor = 0
    assert payload[cursor] == BHIP_SCHEMA_VERSION
    cursor += 1
    assert payload[cursor : cursor + 16] == MANUFACTURER_ID.bytes
    cursor += 16
    assert payload[cursor : cursor + 4] == (1).to_bytes(4, "big")
    cursor += 4
    for value in ["SYN-PRODUCT-001", "SYN-BATCH-001", "AAAAAAAAAAAAAAAAAAAAAAAAAA"]:
        raw = value.encode("utf-8")
        assert payload[cursor : cursor + 4] == len(raw).to_bytes(4, "big")
        cursor += 4
        assert payload[cursor : cursor + len(raw)] == raw
        cursor += len(raw)
    assert payload[cursor : cursor + 4] == b"\x07\xea\x01\x01"
    cursor += 4
    assert payload[cursor] == 1
    cursor += 1
    assert payload[cursor : cursor + 4] == b"\x07\xec\x01\x01"
    cursor += 4
    assert payload[cursor] == 1
    cursor += 1
    assert payload[cursor : cursor + 32] == b"\x07" * 32
    cursor += 32
    assert payload[cursor : cursor + 4] == b"\x07\xea\x01\x02"
    cursor += 4
    assert cursor == len(payload)
