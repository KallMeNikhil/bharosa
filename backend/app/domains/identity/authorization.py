from __future__ import annotations

import enum
from dataclasses import dataclass, field


class Capability(str, enum.Enum):
    CREATE_PRODUCTION_ORDER = "CREATE_PRODUCTION_ORDER"
    AUTHORIZE_SIGNING = "AUTHORIZE_SIGNING"


@dataclass(frozen=True)
class ActorContext:
    actor_id: str
    capabilities: frozenset[Capability] = field(default_factory=frozenset)

    def has(self, capability: Capability) -> bool:
        return capability in self.capabilities


class SigningNotAuthorizedError(PermissionError):
    def __init__(self, actor_id: str) -> None:
        self.actor_id = actor_id
        super().__init__(
            f"Actor {actor_id!r} does not hold AUTHORIZE_SIGNING; "
            f"CREATE_PRODUCTION_ORDER (if held) does not imply signing authority."
        )
