"""m1 baseline correction identity issuance event append only

Revision ID: cdddc937abef
Revises: f4ae5d07fe85
Create Date: 2026-08-16 16:32:32.082108

This is an M1 baseline security correction, not M2 functionality.

The Architecture Source of Truth (Level 4, Invariant #5) and the Roadmap's
own M1 scope require identity_issuance_event to be database-enforced
append-only: INSERT permitted, UPDATE and DELETE denied for the
non-superuser application runtime role. This was not applied when the M1
baseline was provisioned (infra/postgres-init.sql grants ALL PRIVILEGES to
bharosa_app with no corresponding REVOKE). This migration corrects that
gap without altering any already-applied migration, table shape, column,
constraint, or application behavior.
"""
from collections.abc import Sequence

from alembic import op

revision: str = "cdddc937abef"
down_revision: str | None = "f4ae5d07fe85"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("REVOKE UPDATE, DELETE ON identity_issuance_event FROM bharosa_app")


def downgrade() -> None:
    op.execute("GRANT UPDATE, DELETE ON identity_issuance_event TO bharosa_app")
