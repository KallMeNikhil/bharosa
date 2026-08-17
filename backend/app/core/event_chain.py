from __future__ import annotations

import hashlib
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.core.binary import ABSENT, PRESENT, u32, var_str

EVENT_HASH_LENGTH = 32
GENESIS_EVENT_HASH = b"\x00" * EVENT_HASH_LENGTH


class EventChainError(ValueError):
    pass


def compute_event_hash(
    *,
    previous_event_hash: bytes,
    event_kind: str,
    fields: Sequence[str | None],
) -> bytes:
    if len(previous_event_hash) != EVENT_HASH_LENGTH:
        raise EventChainError(
            f"previous_event_hash must be exactly {EVENT_HASH_LENGTH} bytes, "
            f"got {len(previous_event_hash)}"
        )

    digest = hashlib.sha256()
    digest.update(previous_event_hash)
    digest.update(var_str(event_kind))
    digest.update(u32(len(fields)))
    for field in fields:
        digest.update(ABSENT if field is None else PRESENT + var_str(field))
    return digest.digest()


def next_chain_link(
    db: Session,
    *,
    sequence_column: ColumnElement[int],
    event_hash_column: ColumnElement[bytes],
    scope_clause: ColumnElement[bool],
) -> tuple[int, bytes]:
    row = db.execute(
        select(sequence_column, event_hash_column)
        .where(scope_clause)
        .order_by(sequence_column.desc())
        .limit(1)
    ).first()
    if row is None:
        return 1, GENESIS_EVENT_HASH
    return row[0] + 1, row[1]


def verify_chain(
    links: Sequence[tuple[bytes, bytes]],
    *,
    genesis: bytes = GENESIS_EVENT_HASH,
) -> bool:
    expected_previous = genesis
    for previous_event_hash, event_hash in links:
        if previous_event_hash != expected_previous:
            return False
        expected_previous = event_hash
    return True
