from __future__ import annotations

import uuid
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import text
from sqlalchemy.orm import Session

TENANT_SETTING = "bharosa.manufacturer_id"

_SET_CONFIG = text("SELECT set_config(:name, :value, true)")
_CURRENT_SETTING = text("SELECT current_setting(:name, true)")


def set_tenant_context(db: Session, manufacturer_id: uuid.UUID) -> None:
    db.execute(_SET_CONFIG, {"name": TENANT_SETTING, "value": str(manufacturer_id)})


def clear_tenant_context(db: Session) -> None:
    db.execute(_SET_CONFIG, {"name": TENANT_SETTING, "value": ""})


def current_tenant_context(db: Session) -> uuid.UUID | None:
    value = db.execute(_CURRENT_SETTING, {"name": TENANT_SETTING}).scalar()
    if not value:
        return None
    return uuid.UUID(value)


@contextmanager
def tenant_context(db: Session, manufacturer_id: uuid.UUID) -> Iterator[None]:
    previous = current_tenant_context(db)
    set_tenant_context(db, manufacturer_id)
    try:
        yield
    finally:
        if previous is None:
            clear_tenant_context(db)
        else:
            set_tenant_context(db, previous)
