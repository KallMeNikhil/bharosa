"""supply chain domain foundation

Revision ID: 180e3f030a6f
Revises: f48d588d67a7
Create Date: 2026-08-16 16:44:41.606865

"""
from collections.abc import Sequence

import sqlalchemy as sa
from geoalchemy2 import Geometry
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "180e3f030a6f"
down_revision: str | None = "f48d588d67a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "supply_chain_participant",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "manufacturer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("identity_manufacturer.id"),
            nullable=False,
        ),
        sa.Column("participant_ref", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "manufacturer_id", "participant_ref", name="uq_participant_manufacturer_ref"
        ),
        sa.UniqueConstraint("id", "manufacturer_id", name="uq_participant_id_manufacturer"),
    )
    op.create_index(
        "ix_participant_manufacturer_id", "supply_chain_participant", ["manufacturer_id"]
    )

    op.create_table(
        "supply_chain_territory",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "manufacturer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("identity_manufacturer.id"),
            nullable=False,
        ),
        sa.Column("territory_ref", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "boundary",
            Geometry(geometry_type="MULTIPOLYGON", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "manufacturer_id", "territory_ref", name="uq_territory_manufacturer_ref"
        ),
        sa.UniqueConstraint("id", "manufacturer_id", name="uq_territory_id_manufacturer"),
        sa.CheckConstraint("ST_IsValid(boundary)", name="ck_territory_boundary_valid"),
    )
    op.create_index("ix_territory_manufacturer_id", "supply_chain_territory", ["manufacturer_id"])
    op.create_index(
        "ix_territory_boundary_gist",
        "supply_chain_territory",
        ["boundary"],
        postgresql_using="gist",
    )

    op.create_table(
        "supply_chain_channel_authorization",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "manufacturer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("identity_manufacturer.id"),
            nullable=False,
        ),
        sa.Column("participant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("territory_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "valid_from",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["participant_id", "manufacturer_id"],
            ["supply_chain_participant.id", "supply_chain_participant.manufacturer_id"],
            name="fk_authorization_participant_belongs_to_manufacturer",
        ),
        sa.ForeignKeyConstraint(
            ["territory_id", "manufacturer_id"],
            ["supply_chain_territory.id", "supply_chain_territory.manufacturer_id"],
            name="fk_authorization_territory_belongs_to_manufacturer",
        ),
        sa.CheckConstraint(
            "valid_until IS NULL OR valid_until > valid_from",
            name="ck_authorization_valid_range",
        ),
    )
    op.create_index(
        "ix_authorization_manufacturer_id",
        "supply_chain_channel_authorization",
        ["manufacturer_id"],
    )
    op.create_index(
        "ix_authorization_participant_id",
        "supply_chain_channel_authorization",
        ["participant_id"],
    )
    op.create_index(
        "ix_authorization_territory_id",
        "supply_chain_channel_authorization",
        ["territory_id"],
    )

    op.create_table(
        "supply_chain_event",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "manufacturer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("identity_manufacturer.id"),
            nullable=False,
        ),
        sa.Column("identity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("source_participant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("destination_participant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("related_event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("related_identity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("id", "manufacturer_id", name="uq_event_id_manufacturer"),
        sa.ForeignKeyConstraint(
            ["identity_id", "manufacturer_id"],
            ["identity_product_identity.id", "identity_product_identity.manufacturer_id"],
            name="fk_event_identity_belongs_to_manufacturer",
        ),
        sa.ForeignKeyConstraint(
            ["related_identity_id", "manufacturer_id"],
            ["identity_product_identity.id", "identity_product_identity.manufacturer_id"],
            name="fk_event_related_identity_belongs_to_manufacturer",
        ),
        sa.ForeignKeyConstraint(
            ["source_participant_id", "manufacturer_id"],
            ["supply_chain_participant.id", "supply_chain_participant.manufacturer_id"],
            name="fk_event_source_participant_belongs_to_manufacturer",
        ),
        sa.ForeignKeyConstraint(
            ["destination_participant_id", "manufacturer_id"],
            ["supply_chain_participant.id", "supply_chain_participant.manufacturer_id"],
            name="fk_event_destination_participant_belongs_to_manufacturer",
        ),
        sa.ForeignKeyConstraint(
            ["related_event_id", "manufacturer_id"],
            ["supply_chain_event.id", "supply_chain_event.manufacturer_id"],
            name="fk_event_related_event_belongs_to_manufacturer",
        ),
    )
    op.create_index("ix_supply_chain_event_manufacturer_id", "supply_chain_event", ["manufacturer_id"])
    op.create_index("ix_supply_chain_event_identity_id", "supply_chain_event", ["identity_id"])
    op.create_index("ix_supply_chain_event_occurred_at", "supply_chain_event", ["occurred_at"])
    op.create_index("ix_supply_chain_event_event_type", "supply_chain_event", ["event_type"])
    op.create_index(
        "ix_supply_chain_event_source_participant_id", "supply_chain_event", ["source_participant_id"]
    )
    op.create_index(
        "ix_supply_chain_event_destination_participant_id",
        "supply_chain_event",
        ["destination_participant_id"],
    )

    op.execute("REVOKE UPDATE, DELETE, TRUNCATE ON supply_chain_event FROM bharosa_app")


def downgrade() -> None:
    op.execute("GRANT UPDATE, DELETE, TRUNCATE ON supply_chain_event TO bharosa_app")

    op.drop_index("ix_supply_chain_event_destination_participant_id", table_name="supply_chain_event")
    op.drop_index("ix_supply_chain_event_source_participant_id", table_name="supply_chain_event")
    op.drop_index("ix_supply_chain_event_event_type", table_name="supply_chain_event")
    op.drop_index("ix_supply_chain_event_occurred_at", table_name="supply_chain_event")
    op.drop_index("ix_supply_chain_event_identity_id", table_name="supply_chain_event")
    op.drop_index("ix_supply_chain_event_manufacturer_id", table_name="supply_chain_event")
    op.drop_table("supply_chain_event")

    op.drop_index(
        "ix_authorization_territory_id", table_name="supply_chain_channel_authorization"
    )
    op.drop_index(
        "ix_authorization_participant_id", table_name="supply_chain_channel_authorization"
    )
    op.drop_index(
        "ix_authorization_manufacturer_id", table_name="supply_chain_channel_authorization"
    )
    op.drop_table("supply_chain_channel_authorization")

    op.drop_index("ix_territory_boundary_gist", table_name="supply_chain_territory")
    op.drop_index("ix_territory_manufacturer_id", table_name="supply_chain_territory")
    op.drop_table("supply_chain_territory")

    op.drop_index("ix_participant_manufacturer_id", table_name="supply_chain_participant")
    op.drop_table("supply_chain_participant")
