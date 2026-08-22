from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.authorization import ActorContext, Capability
from app.domains.identity import Manufacturer, register_manufacturer
from tests.tenancy_helpers import scope_to


def make_simulation_manufacturer(
    db: Session, name: str = "Simulation Test Manufacturer"
) -> Manufacturer:
    manufacturer_id = uuid.uuid4()
    scope_to(db, manufacturer_id)
    manufacturer = register_manufacturer(db, name=name, manufacturer_id=manufacturer_id)
    db.flush()
    return manufacturer


def simulation_test_actor(
    manufacturer_id: uuid.UUID, actor_id: str = "simulation-test-actor"
) -> ActorContext:
    return ActorContext(
        actor_id=actor_id,
        manufacturer_id=manufacturer_id,
        capabilities=frozenset(Capability),
    )
