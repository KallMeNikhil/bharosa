from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass, field


class Capability(str, enum.Enum):
    CREATE_PRODUCTION_ORDER = "CREATE_PRODUCTION_ORDER"
    AUTHORIZE_SIGNING = "AUTHORIZE_SIGNING"
    AUTHORIZE_PRINT = "AUTHORIZE_PRINT"
    MANAGE_KEYS = "MANAGE_KEYS"
    MANAGE_SUPPLY_CHAIN_REFERENCE_DATA = "MANAGE_SUPPLY_CHAIN_REFERENCE_DATA"
    RECORD_SUPPLY_CHAIN_EVENT = "RECORD_SUPPLY_CHAIN_EVENT"
    RUN_DETECTION = "RUN_DETECTION"
    REVIEW_RISK = "REVIEW_RISK"
    MANAGE_INVESTIGATION = "MANAGE_INVESTIGATION"


class CapabilityNotHeldError(PermissionError):
    def __init__(self, actor_id: str, capability: Capability) -> None:
        self.actor_id = actor_id
        self.capability = capability
        super().__init__(
            f"Actor {actor_id!r} does not hold {capability.value}. Issuance, "
            f"signing and print authority are separable capabilities and holding "
            f"one never implies another."
        )


class TenantScopeViolationError(PermissionError):
    def __init__(self, actor_id: str, actor_manufacturer_id, resource_manufacturer_id) -> None:  # noqa: ANN001
        self.actor_id = actor_id
        self.actor_manufacturer_id = actor_manufacturer_id
        self.resource_manufacturer_id = resource_manufacturer_id
        super().__init__(
            f"Actor {actor_id!r} is scoped to manufacturer "
            f"{actor_manufacturer_id!r} and can never operate on a resource "
            f"belonging to manufacturer {resource_manufacturer_id!r}."
        )


@dataclass(frozen=True)
class ActorContext:
    actor_id: str
    manufacturer_id: uuid.UUID | None = None
    capabilities: frozenset[Capability] = field(default_factory=frozenset)

    def has(self, capability: Capability) -> bool:
        return capability in self.capabilities

    def require(self, capability: Capability) -> None:
        if not self.has(capability):
            raise CapabilityNotHeldError(self.actor_id, capability)

    def require_tenant(self, resource_manufacturer_id: uuid.UUID) -> None:
        if self.manufacturer_id != resource_manufacturer_id:
            raise TenantScopeViolationError(
                self.actor_id, self.manufacturer_id, resource_manufacturer_id
            )
