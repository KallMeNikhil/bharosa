from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "d5b93c1a7e08"
down_revision: str | None = "c8d2a740fe15"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TENANT_PREDICATE = "manufacturer_id::text = current_setting('bharosa.manufacturer_id', true)"

_REQUIRE_SOURCES_FUNCTION = """
CREATE FUNCTION detection_evidence_requires_sources() RETURNS trigger AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM detection_evidence_source WHERE evidence_id = NEW.id
    ) THEN
        RAISE EXCEPTION
            'detection_evidence % cites no source events', NEW.id
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

_REQUIRE_SOURCES_TRIGGER = """
CREATE CONSTRAINT TRIGGER detection_evidence_requires_sources
AFTER INSERT ON detection_evidence
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION detection_evidence_requires_sources();
"""


def upgrade() -> None:
    op.create_table(
        "detection_evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "manufacturer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("identity_manufacturer.id"),
            nullable=False,
        ),
        sa.Column("identity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("detector_id", sa.String(length=64), nullable=False),
        sa.Column("detector_version", sa.Integer(), nullable=False),
        sa.Column("signal_type", sa.String(length=48), nullable=False),
        sa.Column("fraud_family", sa.String(length=48), nullable=False),
        sa.Column("log_likelihood_ratio", sa.Float(), nullable=False),
        sa.Column("explanation", sa.String(length=2000), nullable=False),
        sa.Column("signal_fingerprint", sa.LargeBinary(), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("previous_event_hash", sa.LargeBinary(), nullable=False),
        sa.Column("event_hash", sa.LargeBinary(), nullable=False),
        sa.UniqueConstraint("identity_id", "sequence", name="uq_detection_evidence_sequence"),
        sa.UniqueConstraint("event_hash", name="uq_detection_evidence_hash"),
        sa.UniqueConstraint(
            "identity_id", "signal_fingerprint", name="uq_detection_evidence_fingerprint"
        ),
        sa.CheckConstraint("window_end >= window_start", name="ck_detection_evidence_window"),
        sa.ForeignKeyConstraint(
            ["identity_id", "manufacturer_id"],
            ["identity_product_identity.id", "identity_product_identity.manufacturer_id"],
            name="fk_detection_evidence_identity_belongs_to_manufacturer",
        ),
    )
    op.create_index(
        "ix_detection_evidence_manufacturer_id", "detection_evidence", ["manufacturer_id"]
    )
    op.create_index("ix_detection_evidence_identity_id", "detection_evidence", ["identity_id"])
    op.create_index("ix_detection_evidence_signal_type", "detection_evidence", ["signal_type"])
    op.create_index(
        "ix_detection_evidence_generated_at", "detection_evidence", ["generated_at"]
    )

    op.create_table(
        "detection_evidence_source",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "evidence_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("detection_evidence.id"),
            nullable=False,
        ),
        sa.Column(
            "manufacturer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("identity_manufacturer.id"),
            nullable=False,
        ),
        sa.Column(
            "verification_event_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("verification_event.id"),
            nullable=True,
        ),
        sa.Column(
            "supply_chain_event_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("supply_chain_event.id"),
            nullable=True,
        ),
        sa.Column(
            "identity_issuance_event_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("identity_issuance_event.id"),
            nullable=True,
        ),
        sa.CheckConstraint(
            "(verification_event_id IS NOT NULL)::int "
            "+ (supply_chain_event_id IS NOT NULL)::int "
            "+ (identity_issuance_event_id IS NOT NULL)::int = 1",
            name="ck_detection_evidence_source_exactly_one",
        ),
    )
    op.create_index(
        "ix_detection_evidence_source_evidence_id", "detection_evidence_source", ["evidence_id"]
    )
    op.create_index(
        "ix_detection_evidence_source_manufacturer_id",
        "detection_evidence_source",
        ["manufacturer_id"],
    )

    op.execute(_REQUIRE_SOURCES_FUNCTION)
    op.execute(_REQUIRE_SOURCES_TRIGGER)

    for table in ("detection_evidence", "detection_evidence_source"):
        op.execute(f"REVOKE UPDATE, DELETE, TRUNCATE ON {table} FROM bharosa_app")
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {table} FOR ALL TO bharosa_app "
            f"USING ({_TENANT_PREDICATE}) WITH CHECK ({_TENANT_PREDICATE})"
        )


def downgrade() -> None:
    for table in ("detection_evidence_source", "detection_evidence"):
        op.execute(f"DROP POLICY tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    op.execute("DROP TRIGGER detection_evidence_requires_sources ON detection_evidence")
    op.execute("DROP FUNCTION detection_evidence_requires_sources()")

    op.drop_index(
        "ix_detection_evidence_source_manufacturer_id", table_name="detection_evidence_source"
    )
    op.drop_index(
        "ix_detection_evidence_source_evidence_id", table_name="detection_evidence_source"
    )
    op.drop_table("detection_evidence_source")

    op.drop_index("ix_detection_evidence_generated_at", table_name="detection_evidence")
    op.drop_index("ix_detection_evidence_signal_type", table_name="detection_evidence")
    op.drop_index("ix_detection_evidence_identity_id", table_name="detection_evidence")
    op.drop_index("ix_detection_evidence_manufacturer_id", table_name="detection_evidence")
    op.drop_table("detection_evidence")
