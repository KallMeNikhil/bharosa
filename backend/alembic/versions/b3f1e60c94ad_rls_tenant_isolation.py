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
