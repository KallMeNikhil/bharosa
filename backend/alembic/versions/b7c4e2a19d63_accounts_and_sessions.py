"""accounts and sessions

Revision ID: b7c4e2a19d63
Revises: a2f5c918e34b
Create Date: 2026-10-30 12:00:00.000000

auth_account and auth_session back real sign-in, replacing the development
credential outside development. They are platform tables rather than
tenant-scoped ones: signing in has to look an account up by email before any
tenant is known, and resolving a session token has to happen before the
request's tenant scope can be set. Row-level security is therefore not
enabled on them; each account instead names the one manufacturer its sessions
are scoped to.

bharosa_app receives its privileges on both through the default privileges
granted for bharosa_owner. bharosa_verifier is granted nothing on either.
Only a SHA-256 hash of each session token is stored.
"""
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
