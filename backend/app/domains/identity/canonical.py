from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date

from app.core.binary import (
    date4,
    opt_date4,
    opt_fixed_bytes,
    u8,
    u32,
    uuid16,
    var_str,
)

BHIP_SCHEMA_VERSION = 1

PHYSICAL_SECURITY_REFERENCE_HASH_LENGTH = 32

_SUPPORTED_SCHEMA_VERSIONS = frozenset({BHIP_SCHEMA_VERSION})


class CanonicalPayloadError(ValueError):
    pass


@dataclass(frozen=True)
class SignedPayloadFields:
    manufacturer_id: uuid.UUID
    key_version: int
    product_ref: str
    batch_ref: str
    serial: str
    manufactured_at: date
    expiry_at: date | None
    physical_security_reference_hash: bytes | None
    issued_at: date


def _require_non_empty(name: str, value: str) -> str:
    if not value:
        raise CanonicalPayloadError(f"{name} must be a non-empty opaque reference")
    return value


def build_canonical_payload(
    fields: SignedPayloadFields, *, schema_version: int = BHIP_SCHEMA_VERSION
) -> bytes:
    if schema_version not in _SUPPORTED_SCHEMA_VERSIONS:
        raise CanonicalPayloadError(
            f"unsupported BHIP schema_version {schema_version!r}; "
            f"supported versions are {sorted(_SUPPORTED_SCHEMA_VERSIONS)}"
        )

    return b"".join(
        [
            u8(schema_version),
            uuid16(fields.manufacturer_id),
            u32(fields.key_version),
            var_str(_require_non_empty("product_ref", fields.product_ref)),
            var_str(_require_non_empty("batch_ref", fields.batch_ref)),
            var_str(_require_non_empty("serial", fields.serial)),
            date4(fields.manufactured_at),
            opt_date4(fields.expiry_at),
            opt_fixed_bytes(
                fields.physical_security_reference_hash,
                length=PHYSICAL_SECURITY_REFERENCE_HASH_LENGTH,
            ),
            date4(fields.issued_at),
        ]
    )


def read_schema_version(payload: bytes) -> int:
    if not payload:
        raise CanonicalPayloadError("canonical payload is empty")
    return payload[0]
