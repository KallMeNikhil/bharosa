"""simulation domain foundation

Revision ID: a2f5c918e34b
Revises: e7a41b8c62d9
Create Date: 2026-08-21 00:00:00.000000

simulation_run is a mutable operational record, not evidence: it tracks a
scenario's status (PENDING/RUNNING/COMPLETED/FAILED) the way Batch or
ProductIdentity track operational state elsewhere, paired with an append-only
event log living in a different table. It is never deleted, so a run's
history is never silently lost, but its status/error/completion columns are
ordinary mutable state.

simulation_ground_truth_entry records, independently of any detector, what
the simulator actually generated or injected for each identity in a run. It
is append-only and hash-chained per run, exactly like every other event
table in the system, so a ground-truth row can never be edited to match
whatever a detector happened to find.

simulation_evaluation stores a versioned comparison of that ground truth
against the real detection/investigation pipeline's output. Re-running
evaluation against the same run writes a new sequenced row; nothing here is
ever recomputed in place.

Both tables denormalize manufacturer_id and reuse the identity domain's
composite-FK tenant-scoping pattern rather than re-deriving it. Simulation
runs inside the caller's own existing tenant like every other domain; the
tables carry no separate tenancy model of their own.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "a2f5c918e34b"
down_revision: str | None = "e7a41b8c62d9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TENANT_PREDICATE = "manufacturer_id::text = current_setting('bharosa.manufacturer_id', true)"

_SECURED_TABLES = (
    "simulation_run",
    "simulation_ground_truth_entry",
    "simulation_evaluation",
)

_APPEND_ONLY_TABLES = (
    "simulation_ground_truth_entry",
    "simulation_evaluation",
)


def _create_simulation_run_table() -> None:
    op.create_table(
        "simulation_run",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "manufacturer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("identity_manufacturer.id"),
            nullable=False,
        ),
        sa.Column("run_ref", sa.String(length=64), nullable=False),
        sa.Column("scenario_type", sa.String(length=32), nullable=False),
        sa.Column("seed", sa.Integer(), nullable=False),
        sa.Column("identity_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("triggered_by", sa.String(length=255), nullable=False),
        sa.Column("error_message", sa.String(length=2000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("id", "manufacturer_id", name="uq_simulation_run_id_manufacturer"),
        sa.UniqueConstraint(
            "manufacturer_id", "run_ref", name="uq_simulation_run_manufacturer_ref"
        ),
    )
    op.create_index("ix_simulation_run_manufacturer_id", "simulation_run", ["manufacturer_id"])
    op.create_index("ix_simulation_run_status", "simulation_run", ["status"])


def _create_ground_truth_table() -> None:
    op.create_table(
        "simulation_ground_truth_entry",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "manufacturer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("identity_manufacturer.id"),
            nullable=False,
        ),
        sa.Column("simulation_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("identity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("classification", sa.String(length=32), nullable=False),
        sa.Column("injection_type", sa.String(length=32), nullable=True),
        sa.Column("expected_signal_types", sa.String(length=500), nullable=False),
        sa.Column("notes", sa.String(length=500), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("previous_event_hash", sa.LargeBinary(), nullable=False),
        sa.Column("event_hash", sa.LargeBinary(), nullable=False),
        sa.UniqueConstraint(
            "simulation_run_id", "sequence", name="uq_ground_truth_entry_sequence"
        ),
        sa.UniqueConstraint("event_hash", name="uq_ground_truth_entry_hash"),
        sa.ForeignKeyConstraint(
            ["simulation_run_id", "manufacturer_id"],
            ["simulation_run.id", "simulation_run.manufacturer_id"],
            name="fk_ground_truth_run_belongs_to_manufacturer",
        ),
        sa.ForeignKeyConstraint(
            ["identity_id", "manufacturer_id"],
            ["identity_product_identity.id", "identity_product_identity.manufacturer_id"],
            name="fk_ground_truth_identity_belongs_to_manufacturer",
        ),
    )
    op.create_index(
        "ix_ground_truth_entry_manufacturer_id",
        "simulation_ground_truth_entry",
        ["manufacturer_id"],
    )
    op.create_index(
        "ix_ground_truth_entry_simulation_run_id",
        "simulation_ground_truth_entry",
        ["simulation_run_id"],
    )
    op.create_index(
        "ix_ground_truth_entry_identity_id", "simulation_ground_truth_entry", ["identity_id"]
    )


def _create_evaluation_table() -> None:
    op.create_table(
        "simulation_evaluation",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "manufacturer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("identity_manufacturer.id"),
            nullable=False,
        ),
        sa.Column("simulation_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("true_positive_count", sa.Integer(), nullable=False),
        sa.Column("false_positive_count", sa.Integer(), nullable=False),
        sa.Column("true_negative_count", sa.Integer(), nullable=False),
        sa.Column("false_negative_count", sa.Integer(), nullable=False),
        sa.Column("precision", sa.Float(), nullable=True),
        sa.Column("recall", sa.Float(), nullable=True),
        sa.Column("detection_rate", sa.Float(), nullable=True),
        sa.Column("missed_fraud_rate", sa.Float(), nullable=True),
        sa.Column("investigation_true_positive_count", sa.Integer(), nullable=False),
        sa.Column("investigation_false_positive_count", sa.Integer(), nullable=False),
        sa.Column("per_detector_breakdown", postgresql.JSONB(), nullable=False),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("previous_event_hash", sa.LargeBinary(), nullable=False),
        sa.Column("event_hash", sa.LargeBinary(), nullable=False),
        sa.UniqueConstraint(
            "simulation_run_id", "sequence", name="uq_simulation_evaluation_sequence"
        ),
        sa.UniqueConstraint("event_hash", name="uq_simulation_evaluation_hash"),
        sa.CheckConstraint(
            "true_positive_count >= 0 AND false_positive_count >= 0 "
            "AND true_negative_count >= 0 AND false_negative_count >= 0",
            name="ck_simulation_evaluation_counts_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["simulation_run_id", "manufacturer_id"],
            ["simulation_run.id", "simulation_run.manufacturer_id"],
            name="fk_evaluation_run_belongs_to_manufacturer",
        ),
    )
    op.create_index(
        "ix_simulation_evaluation_manufacturer_id", "simulation_evaluation", ["manufacturer_id"]
    )
    op.create_index(
        "ix_simulation_evaluation_simulation_run_id",
        "simulation_evaluation",
        ["simulation_run_id"],
    )


def upgrade() -> None:
    _create_simulation_run_table()
    _create_ground_truth_table()
    _create_evaluation_table()

    op.execute("REVOKE DELETE, TRUNCATE ON simulation_run FROM bharosa_app")
    for table in _APPEND_ONLY_TABLES:
        op.execute(f"REVOKE UPDATE, DELETE, TRUNCATE ON {table} FROM bharosa_app")

    for table in _SECURED_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {table} FOR ALL TO bharosa_app "
            f"USING ({_TENANT_PREDICATE}) WITH CHECK ({_TENANT_PREDICATE})"
        )


def downgrade() -> None:
    for table in _SECURED_TABLES:
        op.execute(f"DROP POLICY tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    op.drop_index(
        "ix_simulation_evaluation_simulation_run_id", table_name="simulation_evaluation"
    )
    op.drop_index("ix_simulation_evaluation_manufacturer_id", table_name="simulation_evaluation")
    op.drop_table("simulation_evaluation")

    op.drop_index(
        "ix_ground_truth_entry_identity_id", table_name="simulation_ground_truth_entry"
    )
    op.drop_index(
        "ix_ground_truth_entry_simulation_run_id", table_name="simulation_ground_truth_entry"
    )
    op.drop_index(
        "ix_ground_truth_entry_manufacturer_id", table_name="simulation_ground_truth_entry"
    )
    op.drop_table("simulation_ground_truth_entry")

    op.drop_index("ix_simulation_run_status", table_name="simulation_run")
    op.drop_index("ix_simulation_run_manufacturer_id", table_name="simulation_run")
    op.drop_table("simulation_run")
