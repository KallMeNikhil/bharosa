from datetime import date

from app.domains.identity import SignedPayloadFields, build_canonical_payload


def _fields(**overrides):
    base = dict(
        product_ref="SYN-PRODUCT-001",
        serial="SYN-SERIAL-000001",
        batch_ref="SYN-BATCH-001",
        manufacturing_date=date(2026, 1, 1),
        expiry_date=date(2028, 1, 1),
        key_version=1,
        physical_security_reference_hash=None,
    )
    base.update(overrides)
    return SignedPayloadFields(**base)


def test_same_logical_identity_produces_same_canonical_bytes():
    a = build_canonical_payload(_fields())
    b = build_canonical_payload(_fields())
    assert a == b


def test_canonical_bytes_start_with_magic_and_are_deterministic_across_calls():
    payload = build_canonical_payload(_fields())
    assert payload.startswith(b"BHIP1")
    rebuilds = {build_canonical_payload(_fields()) for _ in range(5)}
    assert rebuilds == {payload}


def test_changed_signed_field_changes_canonical_bytes():
    baseline = build_canonical_payload(_fields())
    for override in [
        {"product_ref": "SYN-PRODUCT-002"},
        {"serial": "SYN-SERIAL-000002"},
        {"batch_ref": "SYN-BATCH-002"},
        {"manufacturing_date": date(2026, 6, 1)},
        {"expiry_date": date(2029, 1, 1)},
        {"key_version": 2},
        {"physical_security_reference_hash": b"\x01" * 32},
    ]:
        changed = build_canonical_payload(_fields(**override))
        assert changed != baseline, f"expected change for override {override}"


def test_optional_fields_absent_vs_present_are_distinguishable():
    with_hash = build_canonical_payload(_fields(physical_security_reference_hash=b"\x00"))
    without_hash = build_canonical_payload(_fields(physical_security_reference_hash=None))
    assert with_hash != without_hash


def test_optional_date_fields_absent_encoding():
    no_expiry = build_canonical_payload(_fields(expiry_date=None))
    with_expiry = build_canonical_payload(_fields(expiry_date=date(2028, 1, 1)))
    assert no_expiry != with_expiry


def test_length_prefixing_prevents_field_boundary_ambiguity():
    a = build_canonical_payload(_fields(serial="AB", batch_ref="CDE"))
    b = build_canonical_payload(_fields(serial="ABC", batch_ref="DE"))
    assert a != b
