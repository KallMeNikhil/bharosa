from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f4ae5d07fe85"
down_revision: str | None = "0a8a5c0067aa"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_manufacturer_key_id_manufacturer",
        "identity_manufacturer_key",
        ["id", "manufacturer_id"],
    )

    op.add_column(
        "identity_product_identity",
        sa.Column("manufacturer_id", postgresql.UUID(as_uuid=True), nullable=True),
    )

    op.execute(
        """
        UPDATE identity_product_identity AS pi
        SET manufacturer_id = p.manufacturer_id
        FROM identity_batch AS b
        JOIN identity_product AS p ON p.id = b.product_id
        WHERE pi.batch_id = b.id
        """
    )

    op.alter_column("identity_product_identity", "manufacturer_id", nullable=False)
    op.create_foreign_key(
        "fk_identity_manufacturer_id",
        "identity_product_identity",
        "identity_manufacturer",
        ["manufacturer_id"],
        ["id"],
    )
    op.create_index(
        "ix_identity_manufacturer_id", "identity_product_identity", ["manufacturer_id"]
    )

    op.drop_constraint(
        "identity_product_identity_manufacturer_key_id_fkey",
        "identity_product_identity",
        type_="foreignkey",
    )

    op.create_foreign_key(
        "fk_identity_key_belongs_to_identity_manufacturer",
        "identity_product_identity",
        "identity_manufacturer_key",
        ["manufacturer_key_id", "manufacturer_id"],
        ["id", "manufacturer_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_identity_key_belongs_to_identity_manufacturer",
        "identity_product_identity",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "identity_product_identity_manufacturer_key_id_fkey",
        "identity_product_identity",
        "identity_manufacturer_key",
        ["manufacturer_key_id"],
        ["id"],
    )
    op.drop_index("ix_identity_manufacturer_id", table_name="identity_product_identity")
    op.drop_constraint(
        "fk_identity_manufacturer_id", "identity_product_identity", type_="foreignkey"
    )
    op.drop_column("identity_product_identity", "manufacturer_id")
    op.drop_constraint(
        "uq_manufacturer_key_id_manufacturer", "identity_manufacturer_key", type_="unique"
    )
