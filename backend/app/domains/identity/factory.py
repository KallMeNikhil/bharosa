from __future__ import annotations

import base64
import binascii

from app.core.config import Settings
from app.domains.identity.signer import DevelopmentOnlySigner, MasterKeyDerivedSigner, Signer

_DEV_SIGNER_ALLOWED_ENVIRONMENTS = {"development", "test"}

_development_signer: Signer | None = None


class NoProductionSignerConfiguredError(RuntimeError):
    pass


def get_signer(settings: Settings) -> Signer:
    global _development_signer

    if settings.signing_master_key:
        try:
            master = base64.b64decode(settings.signing_master_key, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise NoProductionSignerConfiguredError(
                "SIGNING_MASTER_KEY must be base64 for at least 32 random bytes."
            ) from exc
        return MasterKeyDerivedSigner(master)

    if settings.environment in _DEV_SIGNER_ALLOWED_ENVIRONMENTS:
        if _development_signer is None:
            _development_signer = DevelopmentOnlySigner()
        return _development_signer

    raise NoProductionSignerConfiguredError(
        f"No signer is configured for environment "
        f"{settings.environment!r}. Set SIGNING_MASTER_KEY; DevelopmentOnlySigner is "
        f"not permitted outside {sorted(_DEV_SIGNER_ALLOWED_ENVIRONMENTS)}."
    )
