from __future__ import annotations

from dataclasses import dataclass
from datetime import date

MAGIC = b"BHIP1"

_PRESENT = b"\x01"
_ABSENT = b"\x00"


@dataclass(frozen=True)
class SignedPayloadFields:
    product_ref: str
    serial: str
    batch_ref: str
    manufacturing_date: date | None
    expiry_date: date | None
    key_version: int
    physical_security_reference_hash: bytes | None


def _encode_str_field(value: str | None) -> bytes:
    if value is None:
        return _ABSENT
    raw = value.encode("utf-8")
    return _PRESENT + len(raw).to_bytes(4, "big") + raw


def _encode_bytes_field(value: bytes | None) -> bytes:
    if value is None:
        return _ABSENT
    return _PRESENT + len(value).to_bytes(4, "big") + value


def _encode_date_field(value: date | None) -> bytes:
    if value is None:
        return _ABSENT
    return _encode_str_field(value.isoformat())


def build_canonical_payload(fields: SignedPayloadFields) -> bytes:
    parts = [
        MAGIC,
        _encode_str_field(fields.product_ref),
        _encode_str_field(fields.serial),
        _encode_str_field(fields.batch_ref),
        _encode_date_field(fields.manufacturing_date),
        _encode_date_field(fields.expiry_date),
        _encode_str_field(str(fields.key_version)),
        _encode_bytes_field(fields.physical_security_reference_hash),
    ]
    return b"".join(parts)
