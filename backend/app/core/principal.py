from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.core.authorization import ActorContext, Capability
from app.core.config import Settings

"""Resolution of an API credential into an actor.

This deliberately mirrors the signer abstraction. The interface is what
calling code depends on; the implementation behind it is expected to be
replaced by real tenant authentication during production hardening, and a
factory-level guard makes the development implementation impossible to reach
outside development and test rather than letting it fall through silently.

The development implementation reads the actor straight out of the
credential. It performs no authentication whatsoever and is not a weak
version of authentication -- it is a stand-in that exists so the API surface
and the frontend that consumes it can be built against a real actor and a
real tenant scope before authentication itself is built.
"""

_DEVELOPMENT_ENVIRONMENTS = frozenset({"development", "test"})

DEVELOPMENT_CREDENTIAL_PREFIX = "dev"


@dataclass(frozen=True)
class Principal:
    actor_id: str
    manufacturer_id: uuid.UUID
    capabilities: frozenset[Capability]

    def to_actor(self) -> ActorContext:
        return ActorContext(
            actor_id=self.actor_id,
            manufacturer_id=self.manufacturer_id,
            capabilities=self.capabilities,
        )


class MalformedCredentialError(ValueError):
    pass


class NoProductionPrincipalResolverConfiguredError(RuntimeError):
    pass


class PrincipalResolver(ABC):
    @abstractmethod
    def resolve(self, credential: str | None) -> Principal | None: ...


class DevelopmentOnlyPrincipalResolver(PrincipalResolver):
    def resolve(self, credential: str | None) -> Principal | None:
        if not credential:
            return None

        parts = credential.split(":")
        if len(parts) != 4 or parts[0] != DEVELOPMENT_CREDENTIAL_PREFIX:
            raise MalformedCredentialError(
                "A development credential is "
                "'dev:<manufacturer_id>:<actor_id>:<CAPABILITY,CAPABILITY>'."
            )

        _, raw_manufacturer_id, actor_id, raw_capabilities = parts
        try:
            manufacturer_id = uuid.UUID(raw_manufacturer_id)
        except ValueError as exc:
            raise MalformedCredentialError(
                f"{raw_manufacturer_id!r} is not a manufacturer id."
            ) from exc

        capabilities = set()
        for name in filter(None, (value.strip() for value in raw_capabilities.split(","))):
            if name == "*":
                capabilities.update(Capability)
                continue
            try:
                capabilities.add(Capability(name))
            except ValueError as exc:
                raise MalformedCredentialError(f"{name!r} is not a capability.") from exc

        if not actor_id:
            raise MalformedCredentialError("A credential must name an actor.")

        return Principal(
            actor_id=actor_id,
            manufacturer_id=manufacturer_id,
            capabilities=frozenset(capabilities),
        )


def get_principal_resolver(settings: Settings) -> PrincipalResolver:
    if settings.environment in _DEVELOPMENT_ENVIRONMENTS:
        return DevelopmentOnlyPrincipalResolver()

    raise NoProductionPrincipalResolverConfiguredError(
        f"No production principal resolver is configured for environment "
        f"{settings.environment!r}. DevelopmentOnlyPrincipalResolver performs "
        f"no authentication and is not permitted outside "
        f"{sorted(_DEVELOPMENT_ENVIRONMENTS)}."
    )
