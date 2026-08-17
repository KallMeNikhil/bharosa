"""verification domain

Revision ID: c8d2a740fe15
Revises: b3f1e60c94ad
Create Date: 2026-08-18 11:24:36.905112

verification_event is the system's first location-bearing table. Precise
coordinates are captured for internal detection use only and never leave the
internal boundary; coarse_cell carries the rounded grid cell that anything
surfaced to a dashboard, export or public response is derived from.

The table is append-only at the database level like every other event table,
and its GiST index exists from this first migration because the velocity and
impossible-travel detectors query it spatially.

bharosa_verifier receives INSERT and SELECT here -- SELECT because the event
hash chain has to read the previous link before writing the next one -- plus
INSERT and UPDATE on the unresolved-scan tally, which is a current-state
projection rather than an event log and is therefore mutable by design.

verification_unresolved_scan_tally deliberately holds no manufacturer_id and
carries no row-level security policy: a scan that resolves to no identity
cannot be attributed to a tenant. Counting those scans per day and per coarse
cell, rather than writing a row per attempt, keeps an enumeration attack from
turning the public endpoint into an unbounded write amplifier.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from geoalchemy2 import Geometry
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "c8d2a740fe15"
down_revision: str | None = "b3f1e60c94ad"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TENANT_PREDICATE = "manufacturer_id::text = current_setting('bharosa.manufacturer_id', true)"


def upgrade() -> None:
    op.create_table(
        "verification_event",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "manufacturer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("identity_manufacturer.id"),
            nullable=False,
        ),
        sa.Column("identity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("signature_valid", sa.Boolean(), nullable=False),
        sa.Column("key_status_at_scan", sa.String(length=32), nullable=True),
        sa.Column("lifecycle_state_at_scan", sa.String(length=32), nullable=False),
        sa.Column("physical_check_result", sa.String(length=32), nullable=False),
        sa.Column(
            "location",
            Geometry(geometry_type="POINT", srid=4326, spatial_index=False),
            nullable=True,
        ),
        sa.Column("coarse_cell", sa.String(length=32), nullable=True),
        sa.Column("reported_accuracy_m", sa.Integer(), nullable=True),
        sa.Column("client_reference_hash", sa.LargeBinary(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("previous_event_hash", sa.LargeBinary(), nullable=False),
        sa.Column("event_hash", sa.LargeBinary(), nullable=False),
        sa.UniqueConstraint("identity_id", "sequence", name="uq_verification_event_sequence"),
        sa.UniqueConstraint("event_hash", name="uq_verification_event_hash"),
        sa.ForeignKeyConstraint(
            ["identity_id", "manufacturer_id"],
            ["identity_product_identity.id", "identity_product_identity.manufacturer_id"],
            name="fk_verification_event_identity_belongs_to_manufacturer",
        ),
    )
    op.create_index(
        "ix_verification_event_manufacturer_id", "verification_event", ["manufacturer_id"]
    )
    op.create_index("ix_verification_event_identity_id", "verification_event", ["identity_id"])
    op.create_index("ix_verification_event_occurred_at", "verification_event", ["occurred_at"])
    op.create_index(
        "ix_verification_event_client_reference_hash",
        "verification_event",
        ["client_reference_hash"],
    )
    op.create_index(
        "ix_verification_event_location_gist",
        "verification_event",
        ["location"],
        postgresql_using="gist",
    )

    op.create_table(
        "verification_unresolved_scan_tally",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("scan_date", sa.Date(), nullable=False),
        sa.Column("coarse_cell", sa.String(length=32), nullable=False),
        sa.Column("scan_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("scan_date", "coarse_cell", name="uq_unresolved_scan_day_cell"),
    )
    op.create_index(
        "ix_unresolved_scan_tally_scan_date",
        "verification_unresolved_scan_tally",
        ["scan_date"],
    )

    op.execute("REVOKE UPDATE, DELETE, TRUNCATE ON verification_event FROM bharosa_app")

    op.execute("ALTER TABLE verification_event ENABLE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY tenant_isolation ON verification_event FOR ALL TO bharosa_app "
        f"USING ({_TENANT_PREDICATE}) WITH CHECK ({_TENANT_PREDICATE})"
    )
    op.execute(
        "CREATE POLICY verifier_write ON verification_event FOR ALL TO bharosa_verifier "
        "USING (true) WITH CHECK (true)"
    )
    op.execute("GRANT SELECT, INSERT ON verification_event TO bharosa_verifier")
    op.execute(
        "GRANT SELECT, INSERT, UPDATE ON verification_unresolved_scan_tally TO bharosa_verifier"
    )


def downgrade() -> None:
    op.execute(
        "REVOKE SELECT, INSERT, UPDATE ON verification_unresolved_scan_tally "
        "FROM bharosa_verifier"
    )
    op.execute("REVOKE SELECT, INSERT ON verification_event FROM bharosa_verifier")
    op.execute("DROP POLICY verifier_write ON verification_event")
    op.execute("DROP POLICY tenant_isolation ON verification_event")
    op.execute("ALTER TABLE verification_event DISABLE ROW LEVEL SECURITY")

    op.drop_index(
        "ix_unresolved_scan_tally_scan_date", table_name="verification_unresolved_scan_tally"
    )
    op.drop_table("verification_unresolved_scan_tally")

    op.drop_index("ix_verification_event_location_gist", table_name="verification_event")
    op.drop_index(
        "ix_verification_event_client_reference_hash", table_name="verification_event"
    )
    op.drop_index("ix_verification_event_occurred_at", table_name="verification_event")
    op.drop_index("ix_verification_event_identity_id", table_name="verification_event")
    op.drop_index("ix_verification_event_manufacturer_id", table_name="verification_event")
    op.drop_table("verification_event")
