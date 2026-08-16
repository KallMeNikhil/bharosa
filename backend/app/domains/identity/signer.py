from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


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
