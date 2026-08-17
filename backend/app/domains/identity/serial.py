from __future__ import annotations

import base64
import secrets

SERIAL_ENTROPY_BITS = 128
SERIAL_LENGTH = 26

_SERIAL_ENTROPY_BYTES = SERIAL_ENTROPY_BITS // 8
_SERIAL_ALPHABET = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZ234567")


class MalformedSerialError(ValueError):
    def __init__(self, serial: str) -> None:
        self.serial = serial
        super().__init__(
            f"Serial {serial!r} is not a well-formed Bharosa serial. A serial is "
            f"{SERIAL_LENGTH} unpadded RFC 4648 base32 characters carrying "
            f"{SERIAL_ENTROPY_BITS} bits of cryptographic randomness; sequential or "
            f"human-readable serials are never accepted."
        )


def generate_serial() -> str:
    raw = secrets.token_bytes(_SERIAL_ENTROPY_BYTES)
    return base64.b32encode(raw).decode("ascii").rstrip("=")


def is_well_formed_serial(serial: str) -> bool:
    return len(serial) == SERIAL_LENGTH and set(serial) <= _SERIAL_ALPHABET


def assert_well_formed_serial(serial: str) -> str:
    if not is_well_formed_serial(serial):
        raise MalformedSerialError(serial)
    return serial
