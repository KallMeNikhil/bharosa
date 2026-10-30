"""Password hashing with scrypt from the standard library.

scrypt is memory-hard, so guessing at scale costs memory as well as time, and
using hashlib's implementation avoids a native dependency. Each stored hash
carries its own parameters, so they can be raised later without invalidating
existing accounts.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

_SCHEME = "scrypt"
_N = 2**14
_R = 8
_P = 1
_KEY_LENGTH = 32
_SALT_BYTES = 16

MIN_PASSWORD_LENGTH = 10


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(_SALT_BYTES)
    digest = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=_N, r=_R, p=_P, dklen=_KEY_LENGTH
    )
    return f"{_SCHEME}${_N}${_R}${_P}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt, digest = stored.split("$")
        if scheme != _SCHEME:
            return False
        expected = base64.b64decode(digest)
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=base64.b64decode(salt),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


# Verified against when an email is unknown, so a failed sign-in takes the same
# time whether or not the account exists.
DUMMY_HASH = hash_password(secrets.token_urlsafe(16))
