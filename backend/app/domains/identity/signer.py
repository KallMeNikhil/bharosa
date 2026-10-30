from __future__ import annotations

import secrets
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


@dataclass(frozen=True)
class GeneratedKey:
    key_handle: str
    public_key: bytes


class Signer(ABC):
    @abstractmethod
    def generate_key(self) -> GeneratedKey: ...

    @abstractmethod
    def sign(self, key_handle: str, payload: bytes) -> bytes: ...

    @staticmethod
    def verify(public_key: bytes, payload: bytes, signature: bytes) -> bool:
        try:
            Ed25519PublicKey.from_public_bytes(public_key).verify(signature, payload)
            return True
        except InvalidSignature:
            return False
        except ValueError:
            return False


class DevelopmentOnlySigner(Signer):
    def __init__(self) -> None:
        self._private_keys: dict[str, Ed25519PrivateKey] = {}

    def generate_key(self) -> GeneratedKey:
        private_key = Ed25519PrivateKey.generate()
        handle = str(uuid.uuid4())
        self._private_keys[handle] = private_key
        public_bytes = private_key.public_key().public_bytes_raw()
        return GeneratedKey(key_handle=handle, public_key=public_bytes)

    def sign(self, key_handle: str, payload: bytes) -> bytes:
        try:
            private_key = self._private_keys[key_handle]
        except KeyError as exc:
            raise ValueError(
                f"Unknown key handle for DevelopmentOnlySigner: {key_handle!r}"
            ) from exc
        return private_key.sign(payload)


class MasterKeyDerivedSigner(Signer):
    """Derives each signing key from one master secret and the key's handle.

    Nothing secret is stored: the handle is random and public-safe on its own,
    and the private key is recomputed from the master secret whenever it is
    needed, so keys survive restarts and work across instances. The master
    secret is therefore the single thing to protect. A KMS-backed signer is
    still the stronger arrangement and can replace this behind the same
    interface.
    """

    _SALT = b"bharosa-signer-v1"

    def __init__(self, master_secret: bytes) -> None:
        if len(master_secret) < 32:
            raise ValueError("The signing master key must be at least 32 bytes.")
        self._master_secret = master_secret

    def _private_key(self, key_handle: str) -> Ed25519PrivateKey:
        seed = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self._SALT,
            info=key_handle.encode("utf-8"),
        ).derive(self._master_secret)
        return Ed25519PrivateKey.from_private_bytes(seed)

    def generate_key(self) -> GeneratedKey:
        handle = secrets.token_urlsafe(24)
        public_bytes = self._private_key(handle).public_key().public_bytes_raw()
        return GeneratedKey(key_handle=handle, public_key=public_bytes)

    def sign(self, key_handle: str, payload: bytes) -> bytes:
        if not key_handle:
            raise ValueError("A key handle is required to sign.")
        return self._private_key(key_handle).sign(payload)
