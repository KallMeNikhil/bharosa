from __future__ import annotations

import uuid
from collections.abc import Iterator
from contextlib import contextmanager, nullcontext

from sqlalchemy.orm import Session

from app.core.tenancy import set_tenant_context, tenant_context


def _enforces_rls(db: Session) -> bool:
    return db.bind is not None and db.bind.dialect.name == "postgresql"


def scope_to(db: Session, manufacturer_id: uuid.UUID) -> None:
    if _enforces_rls(db):
        set_tenant_context(db, manufacturer_id)


@contextmanager
def tenant_scope(db: Session, manufacturer_id: uuid.UUID) -> Iterator[None]:
    if not _enforces_rls(db):
        with nullcontext():
            yield
        return
    with tenant_context(db, manufacturer_id):
        yield
