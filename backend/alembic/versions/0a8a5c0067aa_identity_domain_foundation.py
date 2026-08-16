from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0a8a5c0067aa"
down_revision: str | None = "2de2192837a9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "identity_manufacturer",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "identity_manufacturer_key",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "manufacturer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("identity_manufacturer.id"),
            nullable=False,
        ),
        sa.Column("key_version", sa.Integer(), nullable=False),
        sa.Column("public_key", sa.LargeBinary(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "valid_from",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "manufacturer_id", "key_version", name="uq_manufacturer_key_version"
        ),
    )
    op.create_index(
        "ix_manufacturer_key_manufacturer_id",
        "identity_manufacturer_key",
        ["manufacturer_id"],
    )

    op.create_table(
        "identity_product",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "manufacturer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("identity_manufacturer.id"),
            nullable=False,
        ),
        sa.Column("product_ref", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("manufacturer_id", "product_ref", name="uq_product_manufacturer_ref"),
    )

    op.create_table(
        "identity_batch",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("identity_product.id"),
            nullable=False,
        ),
        sa.Column("batch_ref", sa.String(length=64), nullable=False),
        sa.Column("manufacturing_date", sa.Date(), nullable=True),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("product_id", "batch_ref", name="uq_batch_product_ref"),
    )

    op.create_table(
        "identity_product_identity",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "batch_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("identity_batch.id"),
            nullable=False,
        ),
        sa.Column("serial", sa.String(length=64), nullable=False),
        sa.Column(
            "manufacturer_key_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("identity_manufacturer_key.id"),
            nullable=True,
        ),
        sa.Column("physical_security_reference_hash", sa.LargeBinary(), nullable=True),
        sa.Column("canonical_payload", sa.LargeBinary(), nullable=True),
        sa.Column("signature", sa.LargeBinary(), nullable=True),
        sa.Column("lifecycle_state", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("serial", name="uq_identity_serial"),
        sa.CheckConstraint(
            "lifecycle_state IN ("
            "'RESERVED','SIGNED','PRINTED','PRINT_VERIFIED','RECONCILED','ACTIVATED','PRINT_REJECTED'"
            ")",
            name="ck_identity_lifecycle_state",
        ),
    )
    op.create_index("ix_identity_batch_id", "identity_product_identity", ["batch_id"])
    op.create_index(
        "ix_identity_manufacturer_key_id", "identity_product_identity", ["manufacturer_key_id"]
    )

    op.create_table(
        "identity_issuance_event",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "identity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("identity_product_identity.id"),
            nullable=False,
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("previous_state", sa.String(length=32), nullable=True),
        sa.Column("new_state", sa.String(length=32), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("actor", sa.String(length=255), nullable=True),
        sa.Column("event_metadata", sa.String(length=2000), nullable=True),
        sa.UniqueConstraint("identity_id", "sequence", name="uq_event_identity_sequence"),
    )
    op.create_index("ix_event_identity_id", "identity_issuance_event", ["identity_id"])


def downgrade() -> None:
    op.drop_index("ix_event_identity_id", table_name="identity_issuance_event")
    op.drop_table("identity_issuance_event")

    op.drop_index("ix_identity_manufacturer_key_id", table_name="identity_product_identity")
    op.drop_index("ix_identity_batch_id", table_name="identity_product_identity")
    op.drop_table("identity_product_identity")

    op.drop_table("identity_batch")
    op.drop_table("identity_product")

    op.drop_index(
        "ix_manufacturer_key_manufacturer_id", table_name="identity_manufacturer_key"
    )
    op.drop_table("identity_manufacturer_key")

    op.drop_table("identity_manufacturer")
