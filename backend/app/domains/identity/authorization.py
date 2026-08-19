from __future__ import annotations

from app.core.authorization import (
    ActorContext,
    Capability,
    CapabilityNotHeldError,
    TenantScopeViolationError,
)


class SigningNotAuthorizedError(CapabilityNotHeldError):
    def __init__(self, actor_id: str) -> None:
        super().__init__(actor_id, Capability.AUTHORIZE_SIGNING)


__all__ = [
    "ActorContext",
    "Capability",
    "CapabilityNotHeldError",
    "TenantScopeViolationError",
    "SigningNotAuthorizedError",
]
