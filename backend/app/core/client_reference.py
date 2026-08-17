from __future__ import annotations

import hashlib

from app.core.config import Settings

DEVELOPMENT_SALT = "development-only-client-reference-salt"
DIGEST_SIZE = 32


class InsecureClientReferenceSaltError(RuntimeError):
    pass


def client_reference_hash(settings: Settings, client_reference: str | None) -> bytes | None:
    if client_reference is None:
        return None

    salt = settings.client_reference_salt
    if settings.is_production and salt == DEVELOPMENT_SALT:
        raise InsecureClientReferenceSaltError(
            "CLIENT_REFERENCE_SALT is still the development default. Scan "
            "client references would be trivially reversible in production."
        )

    return hashlib.blake2b(
        client_reference.encode("utf-8"), key=salt.encode("utf-8"), digest_size=DIGEST_SIZE
    ).digest()
