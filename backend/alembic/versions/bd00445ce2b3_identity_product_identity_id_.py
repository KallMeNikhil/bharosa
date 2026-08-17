"""identity product identity id manufacturer uniqueness

Revision ID: bd00445ce2b3
Revises: f4ae5d07fe85
Create Date: 2026-08-16 12:02:56.922741

"""
from collections.abc import Sequence

from alembic import op

revision: str = "bd00445ce2b3"
down_revision: str | None = "cdddc937abef"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_identity_product_identity_id_manufacturer",
        "identity_product_identity",
        ["id", "manufacturer_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_identity_product_identity_id_manufacturer",
        "identity_product_identity",
        type_="unique",
    )
