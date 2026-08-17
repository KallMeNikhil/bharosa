from __future__ import annotations

import uuid
from datetime import date

ABSENT = b"\x00"
PRESENT = b"\x01"


class BinaryEncodingError(ValueError):
    pass


def u8(value: int) -> bytes:
    if not 0 <= value <= 0xFF:
        raise BinaryEncodingError(f"value {value!r} does not fit in one unsigned byte")
    return value.to_bytes(1, "big")


def u16(value: int) -> bytes:
    if not 0 <= value <= 0xFFFF:
        raise BinaryEncodingError(f"value {value!r} does not fit in two unsigned bytes")
    return value.to_bytes(2, "big")


def u32(value: int) -> bytes:
    if not 0 <= value <= 0xFFFFFFFF:
        raise BinaryEncodingError(f"value {value!r} does not fit in four unsigned bytes")
    return value.to_bytes(4, "big")


def uuid16(value: uuid.UUID) -> bytes:
    return value.bytes


def var_bytes(value: bytes) -> bytes:
    return u32(len(value)) + value


def var_str(value: str) -> bytes:
    return var_bytes(value.encode("utf-8"))


def date4(value: date) -> bytes:
    return u16(value.year) + u8(value.month) + u8(value.day)


def opt_date4(value: date | None) -> bytes:
    return ABSENT if value is None else PRESENT + date4(value)


def opt_var_str(value: str | None) -> bytes:
    return ABSENT if value is None else PRESENT + var_str(value)


def opt_fixed_bytes(value: bytes | None, *, length: int) -> bytes:
    if value is None:
        return ABSENT
    if len(value) != length:
        raise BinaryEncodingError(
            f"expected exactly {length} bytes, got {len(value)}"
        )
    return PRESENT + value
