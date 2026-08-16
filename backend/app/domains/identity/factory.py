from __future__ import annotations

from app.core.config import Settings
from app.domains.identity.signer import DevelopmentOnlySigner, Signer

_DEV_SIGNER_ALLOWED_ENVIRONMENTS = {"development", "test"}


class NoProductionSignerConfiguredError(RuntimeError):
    pass


def get_signer(settings: Settings) -> Signer:
    if settings.environment in _DEV_SIGNER_ALLOWED_ENVIRONMENTS:
        return DevelopmentOnlySigner()

    raise NoProductionSignerConfiguredError(
        f"No production (KMS-backed) signer is configured for environment "
        f"{settings.environment!r}. DevelopmentOnlySigner is not permitted "
        f"outside {sorted(_DEV_SIGNER_ALLOWED_ENVIRONMENTS)}."
    )
