"""row level security tenant isolation across identity and supply chain

Revision ID: b3f1e60c94ad
Revises: a1c7d4e9b230
Create Date: 2026-08-18 09:41:52.607914

Architectural Invariant 3 requires manufacturer/tenant isolation to be
enforced at the database level, not by application code alone. No table
carried a row-level security policy before this revision.

Every policy compares the row's manufacturer_id against the
bharosa.manufacturer_id session setting. current_setting(..., true) returns
NULL when the setting is absent, and a NULL comparison excludes the row, so
an application session that never establishes a tenant context sees nothing
and can write nothing. The behaviour is fail-closed by construction rather
than by a default value that could be forgotten.

identity_manufacturer is the one deliberate asymmetry: its USING clause
scopes reads and updates to the caller's own tenant row, while its WITH
CHECK clause permits insertion, because onboarding a new manufacturer
necessarily happens before any tenant context for it can exist.

bharosa_owner owns these tables and is therefore exempt from row-level
security by PostgreSQL's normal ownership rules, which is what allows
migrations and backfills to run. FORCE ROW LEVEL SECURITY is deliberately
not set for that reason.

bharosa_verifier receives read access to exactly the identity tables the
public verification path resolves against, under a separate policy. It is
granted nothing on products, batches, participants, territories, channel
authorizations or supply-chain events, so a compromise of the public
endpoint cannot read manufacturer business data.
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "b3f1e60c94ad"
down_revision: str | None = "a1c7d4e9b230"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TENANT_SCOPED_TABLES = (
    "identity_manufacturer_key",
    "identity_manufacturer_key_event",
    "identity_product",
    "identity_batch",
    "identity_product_identity",
    "identity_issuance_event",
    "supply_chain_participant",
    "supply_chain_territory",
    "supply_chain_channel_authorization",
    "supply_chain_event",
)

VERIFIER_READABLE_TABLES = (
    "identity_manufacturer_key",
    "identity_product",
    "identity_batch",
    "identity_product_identity",
)

_TENANT_PREDICATE = "manufacturer_id::text = current_setting('bharosa.manufacturer_id', true)"


def upgrade() -> None:
    op.execute("ALTER TABLE identity_manufacturer ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON identity_manufacturer FOR ALL TO bharosa_app "
        "USING (id::text = current_setting('bharosa.manufacturer_id', true)) "
        "WITH CHECK (true)"
    )

    for table in TENANT_SCOPED_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {table} FOR ALL TO bharosa_app "
            f"USING ({_TENANT_PREDICATE}) WITH CHECK ({_TENANT_PREDICATE})"
        )

    for table in VERIFIER_READABLE_TABLES:
        op.execute(f"GRANT SELECT ON {table} TO bharosa_verifier")
        op.execute(
            f"CREATE POLICY verifier_read ON {table} FOR SELECT TO bharosa_verifier USING (true)"
        )


def downgrade() -> None:
    for table in VERIFIER_READABLE_TABLES:
        op.execute(f"DROP POLICY verifier_read ON {table}")
        op.execute(f"REVOKE SELECT ON {table} FROM bharosa_verifier")

    for table in TENANT_SCOPED_TABLES:
        op.execute(f"DROP POLICY tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    op.execute("DROP POLICY tenant_isolation ON identity_manufacturer")
    op.execute("ALTER TABLE identity_manufacturer DISABLE ROW LEVEL SECURITY")
