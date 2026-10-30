from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "b7c4e2a19d63"
down_revision: str | None = "a2f5c918e34b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "auth_account",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column(
            "manufacturer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("identity_manufacturer.id"),
            nullable=False,
        ),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("last_signed_in_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("email", name="uq_auth_account_email"),
    )
    op.create_index("ix_auth_account_manufacturer_id", "auth_account", ["manufacturer_id"])

    op.create_table(
        "auth_session",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("auth_account.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.LargeBinary(32), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("token_hash", name="uq_auth_session_token_hash"),
    )
    op.create_index("ix_auth_session_account_id", "auth_session", ["account_id"])


def downgrade() -> None:
    op.drop_index("ix_auth_session_account_id", table_name="auth_session")
    op.drop_table("auth_session")
    op.drop_index("ix_auth_account_manufacturer_id", table_name="auth_account")
    op.drop_table("auth_account")
