from __future__ import annotations

from app.core.config import Settings
from app.domains.identity.signer import DevelopmentOnlySigner, Signer

_DEV_SIGNER_ALLOWED_ENVIRONMENTS = {"development", "test"}

_development_signer: Signer | None = None


class NoProductionSignerConfiguredError(RuntimeError):
    pass


def get_signer(settings: Settings) -> Signer:
    """Resolve the signer for this environment.

    The development signer is a process-wide singleton because a key handle
    has to stay resolvable across requests: the endpoint that issues a key and
    the endpoint that signs with it are separate calls. A KMS-backed signer
    gets this for free, since the handle refers to key material the service
    does not hold. Handing back a fresh in-process signer each time would make
    every handle dead on arrival.
    """
    global _development_signer

    if settings.environment in _DEV_SIGNER_ALLOWED_ENVIRONMENTS:
        if _development_signer is None:
            _development_signer = DevelopmentOnlySigner()
        return _development_signer

    raise NoProductionSignerConfiguredError(
        f"No production (KMS-backed) signer is configured for environment "
        f"{settings.environment!r}. DevelopmentOnlySigner is not permitted "
        f"outside {sorted(_DEV_SIGNER_ALLOWED_ENVIRONMENTS)}."
    )
