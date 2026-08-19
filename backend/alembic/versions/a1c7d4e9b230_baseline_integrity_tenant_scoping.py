"""m1 m2 baseline correction: denormalized tenant scoping, event hash chaining, key events

Revision ID: a1c7d4e9b230
Revises: 180e3f030a6f
Create Date: 2026-08-18 09:12:04.118273

This is an M1/M2 baseline correction, not M3 functionality. It closes four
gaps against decisions the Architecture Source of Truth already froze:

  * Denormalized tenant scoping (Architecture Section 13) was applied to
    identity_product_identity but not to identity_batch or
    identity_issuance_event, so neither table can carry an RLS policy keyed
    on manufacturer_id.
  * Per-event hash chaining (Level 4, Section 11.3) was specified as a
    schema decision to be made at each event table's first migration, and
    was not present on identity_issuance_event or supply_chain_event.
  * Key status changes (revocation, rotation, compromise) mutated
    identity_manufacturer_key with no append-only audit record, despite
    Section 3.5 making key compromise the architecture's most consequential
    failure mode.
  * identity_product had no GTIN column, which the GS1 Digital Link
    resolution path added in M3 requires.

The hash algorithm is inlined here rather than imported from application
code so that this migration's output can never change as a side effect of
a later refactor.

Signatures issued before this revision were produced under a BHIP1 layout
that omitted manufacturer_id and issued_at and is no longer generated.
Those signatures remain byte-verifiable against their stored payloads but
no longer match a payload rebuilt from current field values; pre-existing
development identities must be re-issued.
"""
from __future__ import annotations

import hashlib
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "a1c7d4e9b230"
down_revision: str | None = "180e3f030a6f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

GENESIS_EVENT_HASH = b"\x00" * 32


def _var_str(value: str) -> bytes:
    raw = value.encode("utf-8")
    return len(raw).to_bytes(4, "big") + raw


def _event_hash(previous_event_hash: bytes, event_kind: str, fields: list[str | None]) -> bytes:
    digest = hashlib.sha256()
    digest.update(previous_event_hash)
    digest.update(_var_str(event_kind))
    digest.update(len(fields).to_bytes(4, "big"))
    for field in fields:
        digest.update(b"\x00" if field is None else b"\x01" + _var_str(field))
    return digest.digest()


def _text(value) -> str | None:  # noqa: ANN001
    return None if value is None else str(value)


def _upgrade_product() -> None:
    op.add_column("identity_product", sa.Column("gtin", sa.String(length=14), nullable=True))
    op.create_unique_constraint(
        "uq_product_id_manufacturer", "identity_product", ["id", "manufacturer_id"]
    )
    op.create_index("ix_product_manufacturer_id", "identity_product", ["manufacturer_id"])


def _upgrade_batch() -> None:
    op.add_column(
        "identity_batch",
        sa.Column("manufacturer_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.execute(
        """
        UPDATE identity_batch AS b
        SET manufacturer_id = p.manufacturer_id
        FROM identity_product AS p
        WHERE b.product_id = p.id
        """
    )
    op.alter_column("identity_batch", "manufacturer_id", nullable=False)
    op.create_foreign_key(
        "fk_batch_manufacturer_id",
        "identity_batch",
        "identity_manufacturer",
        ["manufacturer_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_batch_product_belongs_to_manufacturer",
        "identity_batch",
        "identity_product",
        ["product_id", "manufacturer_id"],
        ["id", "manufacturer_id"],
    )
    op.create_unique_constraint(
        "uq_batch_id_manufacturer", "identity_batch", ["id", "manufacturer_id"]
    )
    op.create_index("ix_batch_manufacturer_id", "identity_batch", ["manufacturer_id"])
    op.create_foreign_key(
        "fk_identity_batch_belongs_to_manufacturer",
        "identity_product_identity",
        "identity_batch",
        ["batch_id", "manufacturer_id"],
        ["id", "manufacturer_id"],
    )


def _upgrade_issuance_event() -> None:
    op.add_column(
        "identity_issuance_event",
        sa.Column("manufacturer_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "identity_issuance_event",
        sa.Column("previous_event_hash", sa.LargeBinary(), nullable=True),
    )
    op.add_column(
        "identity_issuance_event", sa.Column("event_hash", sa.LargeBinary(), nullable=True)
    )
    op.execute(
        """
        UPDATE identity_issuance_event AS e
        SET manufacturer_id = pi.manufacturer_id
        FROM identity_product_identity AS pi
        WHERE e.identity_id = pi.id
        """
    )

    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            "SELECT id, manufacturer_id, identity_id, sequence, event_type, "
            "previous_state, new_state, actor, event_metadata "
            "FROM identity_issuance_event ORDER BY identity_id, sequence"
        )
    ).all()

    previous_by_identity: dict[str, bytes] = {}
    for row in rows:
        identity_key = str(row.identity_id)
        previous = previous_by_identity.get(identity_key, GENESIS_EVENT_HASH)
        event_hash = _event_hash(
            previous,
            "identity_issuance_event",
            [
                _text(row.manufacturer_id),
                _text(row.identity_id),
                _text(row.sequence),
                _text(row.event_type),
                _text(row.previous_state),
                _text(row.new_state),
                row.actor,
                row.event_metadata,
            ],
        )
        connection.execute(
            sa.text(
                "UPDATE identity_issuance_event "
                "SET previous_event_hash = :previous, event_hash = :current WHERE id = :id"
            ),
            {"previous": previous, "current": event_hash, "id": row.id},
        )
        previous_by_identity[identity_key] = event_hash

    op.alter_column("identity_issuance_event", "manufacturer_id", nullable=False)
    op.alter_column("identity_issuance_event", "previous_event_hash", nullable=False)
    op.alter_column("identity_issuance_event", "event_hash", nullable=False)

    op.create_foreign_key(
        "fk_issuance_event_manufacturer_id",
        "identity_issuance_event",
        "identity_manufacturer",
        ["manufacturer_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_issuance_event_identity_belongs_to_manufacturer",
        "identity_issuance_event",
        "identity_product_identity",
        ["identity_id", "manufacturer_id"],
        ["id", "manufacturer_id"],
    )
    op.create_unique_constraint(
        "uq_issuance_event_hash", "identity_issuance_event", ["event_hash"]
    )
    op.create_index(
        "ix_event_manufacturer_id", "identity_issuance_event", ["manufacturer_id"]
    )


def _upgrade_key_event() -> None:
    op.create_table(
        "identity_manufacturer_key_event",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "manufacturer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("identity_manufacturer.id"),
            nullable=False,
        ),
        sa.Column("key_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("previous_status", sa.String(length=32), nullable=True),
        sa.Column("new_status", sa.String(length=32), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("actor", sa.String(length=255), nullable=True),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("previous_event_hash", sa.LargeBinary(), nullable=False),
        sa.Column("event_hash", sa.LargeBinary(), nullable=False),
        sa.UniqueConstraint("key_id", "sequence", name="uq_key_event_key_sequence"),
        sa.UniqueConstraint("event_hash", name="uq_key_event_hash"),
        sa.ForeignKeyConstraint(
            ["key_id", "manufacturer_id"],
            ["identity_manufacturer_key.id", "identity_manufacturer_key.manufacturer_id"],
            name="fk_key_event_key_belongs_to_manufacturer",
        ),
    )
    op.create_index("ix_key_event_key_id", "identity_manufacturer_key_event", ["key_id"])
    op.create_index(
        "ix_key_event_manufacturer_id", "identity_manufacturer_key_event", ["manufacturer_id"]
    )

    connection = op.get_bind()
    keys = connection.execute(
        sa.text(
            "SELECT id, manufacturer_id, key_version, status, created_at "
            "FROM identity_manufacturer_key ORDER BY created_at, id"
        )
    ).all()
    for key in keys:
        event_hash = _event_hash(
            GENESIS_EVENT_HASH,
            "identity_manufacturer_key_event",
            [
                _text(key.manufacturer_id),
                _text(key.id),
                _text(key.key_version),
                "1",
                "ISSUED",
                None,
                "ACTIVE",
                None,
                "backfilled when the key event table was introduced",
            ],
        )
        connection.execute(
            sa.text(
                "INSERT INTO identity_manufacturer_key_event "
                "(id, manufacturer_id, key_id, sequence, event_type, previous_status, "
                "new_status, occurred_at, actor, reason, previous_event_hash, event_hash) "
                "VALUES (gen_random_uuid(), :manufacturer_id, :key_id, 1, 'ISSUED', NULL, "
                "'ACTIVE', :occurred_at, NULL, :reason, :previous, :current)"
            ),
            {
                "manufacturer_id": key.manufacturer_id,
                "key_id": key.id,
                "occurred_at": key.created_at,
                "reason": "backfilled when the key event table was introduced",
                "previous": GENESIS_EVENT_HASH,
                "current": event_hash,
            },
        )

    op.execute(
        "REVOKE UPDATE, DELETE, TRUNCATE ON identity_manufacturer_key_event FROM bharosa_app"
    )


def _upgrade_supply_chain_event() -> None:
    op.add_column("supply_chain_event", sa.Column("sequence", sa.Integer(), nullable=True))
    op.add_column(
        "supply_chain_event", sa.Column("previous_event_hash", sa.LargeBinary(), nullable=True)
    )
    op.add_column("supply_chain_event", sa.Column("event_hash", sa.LargeBinary(), nullable=True))

    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            "SELECT id, manufacturer_id, identity_id, event_type, source_participant_id, "
            "destination_participant_id, related_event_id, related_identity_id, reason, "
            "occurred_at FROM supply_chain_event ORDER BY identity_id, occurred_at, recorded_at, id"
        )
    ).all()

    sequence_by_identity: dict[str, int] = {}
    previous_by_identity: dict[str, bytes] = {}
    for row in rows:
        identity_key = str(row.identity_id)
        sequence = sequence_by_identity.get(identity_key, 0) + 1
        previous = previous_by_identity.get(identity_key, GENESIS_EVENT_HASH)
        event_hash = _event_hash(
            previous,
            "supply_chain_event",
            [
                _text(row.manufacturer_id),
                _text(row.identity_id),
                _text(sequence),
                _text(row.event_type),
                _text(row.source_participant_id),
                _text(row.destination_participant_id),
                _text(row.related_event_id),
                _text(row.related_identity_id),
                row.reason,
                row.occurred_at.isoformat(),
            ],
        )
        connection.execute(
            sa.text(
                "UPDATE supply_chain_event SET sequence = :sequence, "
                "previous_event_hash = :previous, event_hash = :current WHERE id = :id"
            ),
            {
                "sequence": sequence,
                "previous": previous,
                "current": event_hash,
                "id": row.id,
            },
        )
        sequence_by_identity[identity_key] = sequence
        previous_by_identity[identity_key] = event_hash

    op.alter_column("supply_chain_event", "sequence", nullable=False)
    op.alter_column("supply_chain_event", "previous_event_hash", nullable=False)
    op.alter_column("supply_chain_event", "event_hash", nullable=False)
    op.create_unique_constraint(
        "uq_supply_chain_event_sequence", "supply_chain_event", ["identity_id", "sequence"]
    )
    op.create_unique_constraint(
        "uq_supply_chain_event_hash", "supply_chain_event", ["event_hash"]
    )


def upgrade() -> None:
    _upgrade_product()
    _upgrade_batch()
    _upgrade_issuance_event()
    _upgrade_key_event()
    _upgrade_supply_chain_event()


def downgrade() -> None:
    op.drop_constraint("uq_supply_chain_event_hash", "supply_chain_event", type_="unique")
    op.drop_constraint("uq_supply_chain_event_sequence", "supply_chain_event", type_="unique")
    op.drop_column("supply_chain_event", "event_hash")
    op.drop_column("supply_chain_event", "previous_event_hash")
    op.drop_column("supply_chain_event", "sequence")

    op.drop_index("ix_key_event_manufacturer_id", table_name="identity_manufacturer_key_event")
    op.drop_index("ix_key_event_key_id", table_name="identity_manufacturer_key_event")
    op.drop_table("identity_manufacturer_key_event")

    op.drop_index("ix_event_manufacturer_id", table_name="identity_issuance_event")
    op.drop_constraint("uq_issuance_event_hash", "identity_issuance_event", type_="unique")
    op.drop_constraint(
        "fk_issuance_event_identity_belongs_to_manufacturer",
        "identity_issuance_event",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_issuance_event_manufacturer_id", "identity_issuance_event", type_="foreignkey"
    )
    op.drop_column("identity_issuance_event", "event_hash")
    op.drop_column("identity_issuance_event", "previous_event_hash")
    op.drop_column("identity_issuance_event", "manufacturer_id")

    op.drop_constraint(
        "fk_identity_batch_belongs_to_manufacturer",
        "identity_product_identity",
        type_="foreignkey",
    )
    op.drop_index("ix_batch_manufacturer_id", table_name="identity_batch")
    op.drop_constraint("uq_batch_id_manufacturer", "identity_batch", type_="unique")
    op.drop_constraint(
        "fk_batch_product_belongs_to_manufacturer", "identity_batch", type_="foreignkey"
    )
    op.drop_constraint("fk_batch_manufacturer_id", "identity_batch", type_="foreignkey")
    op.drop_column("identity_batch", "manufacturer_id")

    op.drop_index("ix_product_manufacturer_id", table_name="identity_product")
    op.drop_constraint("uq_product_id_manufacturer", "identity_product", type_="unique")
    op.drop_column("identity_product", "gtin")
