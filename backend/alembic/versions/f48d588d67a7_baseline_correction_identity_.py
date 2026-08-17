"""m1 baseline correction identity issuance event revoke truncate

Revision ID: f48d588d67a7
Revises: bd00445ce2b3
Create Date: 2026-08-16 16:38:45.340701

This is a continuation of the M1 baseline append-only security correction
introduced in cdddc937abef, not M2 functionality.

Verification against real PostgreSQL confirmed that, in addition to
UPDATE/DELETE, the non-superuser application role (bharosa_app) also held
TRUNCATE on identity_issuance_event, and that TRUNCATE actually executes
successfully for that role. TRUNCATE is not a MERGE of UPDATE or DELETE
privileges in PostgreSQL's privilege model — it is governed by its own
distinct grantable privilege and must be revoked separately. Because
TRUNCATE can remove all historical issuance events in a single statement,
leaving it granted would leave the database-level append-only invariant
(Architecture Source of Truth, Level 4 / Invariant #5) incomplete despite
cdddc937abef. This migration closes that gap. It is purely a privilege
change: no table shape, column, constraint, or application behavior is
altered, and no previously applied migration is modified.
"""
from collections.abc import Sequence

from alembic import op

revision: str = "f48d588d67a7"
down_revision: str | None = "bd00445ce2b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("REVOKE TRUNCATE ON identity_issuance_event FROM bharosa_app")


def downgrade() -> None:
    op.execute("GRANT TRUNCATE ON identity_issuance_event TO bharosa_app")
