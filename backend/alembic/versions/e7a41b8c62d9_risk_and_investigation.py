"""risk assessment and investigation

Revision ID: e7a41b8c62d9
Revises: d5b93c1a7e08
Create Date: 2026-08-18 14:47:19.554023

risk_assessment stores the accumulated log-odds together with the prior it
started from and the ruleset version that produced it, so an old assessment
can always be read back on the terms it was made under. Re-assessing under a
new ruleset writes a new row; nothing here is ever recomputed in place.

risk_assessment_contribution records what each piece of evidence actually
contributed after within-family discounting, alongside the benign explanation
for that signal type. Investigators are shown the alternative reading of the
evidence next to the incriminating one by construction, rather than it being
left to a UI to remember.

investigation_fraud_incident carries a deferred constraint trigger requiring
at least one evidence citation, mirroring detection_evidence. The service
already refuses to build one without evidence; this makes the same statement
to anything that writes to the database directly.

Incident status is a projection over investigation_incident_event, which is
append-only and hash-chained like every other event table, so the history of
who moved an incident to which state and why cannot be quietly rewritten.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "e7a41b8c62d9"
down_revision: str | None = "d5b93c1a7e08"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TENANT_PREDICATE = "manufacturer_id::text = current_setting('bharosa.manufacturer_id', true)"

_SECURED_TABLES = (
    "risk_assessment",
    "risk_assessment_contribution",
    "investigation_fraud_incident",
    "investigation_incident_evidence",
    "investigation_incident_event",
)

_APPEND_ONLY_TABLES = (
    "risk_assessment",
    "risk_assessment_contribution",
    "investigation_incident_evidence",
    "investigation_incident_event",
)

_REQUIRE_CITATION_FUNCTION = """
CREATE FUNCTION fraud_incident_requires_evidence() RETURNS trigger AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM investigation_incident_evidence WHERE incident_id = NEW.id
    ) THEN
        RAISE EXCEPTION
            'fraud incident % cites no detection evidence', NEW.id
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

_REQUIRE_CITATION_TRIGGER = """
CREATE CONSTRAINT TRIGGER fraud_incident_requires_evidence
AFTER INSERT ON investigation_fraud_incident
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION fraud_incident_requires_evidence();
"""

_RISK_FLAG_VIEW = """
CREATE VIEW verification_identity_risk_flag AS
SELECT DISTINCT ON (identity_id)
       identity_id,
       confidence IN ('MODERATE', 'HIGH') AS elevated
FROM risk_assessment
ORDER BY identity_id, sequence DESC;
"""

_INCIDENT_FLAG_VIEW = """
CREATE VIEW verification_identity_incident_flag AS
SELECT DISTINCT identity_id, true AS reported
FROM investigation_fraud_incident
WHERE status IN ('OPEN', 'UNDER_REVIEW');
"""


def _create_risk_tables() -> None:
    op.create_table(
        "risk_assessment",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "manufacturer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("identity_manufacturer.id"),
            nullable=False,
        ),
        sa.Column("identity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("ruleset_version", sa.Integer(), nullable=False),
        sa.Column("prior_log_odds", sa.Float(), nullable=False),
        sa.Column("posterior_log_odds", sa.Float(), nullable=False),
        sa.Column("confidence", sa.String(length=32), nullable=False),
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
        sa.UniqueConstraint("identity_id", "sequence", name="uq_risk_assessment_sequence"),
        sa.UniqueConstraint("event_hash", name="uq_risk_assessment_hash"),
        sa.CheckConstraint("window_end >= window_start", name="ck_risk_assessment_window"),
        sa.ForeignKeyConstraint(
            ["identity_id", "manufacturer_id"],
            ["identity_product_identity.id", "identity_product_identity.manufacturer_id"],
            name="fk_risk_assessment_identity_belongs_to_manufacturer",
        ),
    )
    op.create_index("ix_risk_assessment_manufacturer_id", "risk_assessment", ["manufacturer_id"])
    op.create_index("ix_risk_assessment_identity_id", "risk_assessment", ["identity_id"])
    op.create_index("ix_risk_assessment_confidence", "risk_assessment", ["confidence"])

    op.create_table(
        "risk_assessment_contribution",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "assessment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("risk_assessment.id"),
            nullable=False,
        ),
        sa.Column(
            "manufacturer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("identity_manufacturer.id"),
            nullable=False,
        ),
        sa.Column(
            "evidence_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("detection_evidence.id"),
            nullable=False,
        ),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("contributed_log_odds", sa.Float(), nullable=False),
        sa.Column("benign_explanation", sa.String(length=500), nullable=False),
        sa.UniqueConstraint(
            "assessment_id", "evidence_id", name="uq_risk_contribution_assessment_evidence"
        ),
    )
    op.create_index(
        "ix_risk_contribution_assessment_id", "risk_assessment_contribution", ["assessment_id"]
    )
    op.create_index(
        "ix_risk_contribution_manufacturer_id",
        "risk_assessment_contribution",
        ["manufacturer_id"],
    )


def _create_investigation_tables() -> None:
    op.create_table(
        "investigation_fraud_incident",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "manufacturer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("identity_manufacturer.id"),
            nullable=False,
        ),
        sa.Column("identity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "risk_assessment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("risk_assessment.id"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("summary", sa.String(length=1000), nullable=False),
        sa.Column("opened_by", sa.String(length=255), nullable=False),
        sa.Column(
            "opened_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("id", "manufacturer_id", name="uq_incident_id_manufacturer"),
        sa.ForeignKeyConstraint(
            ["identity_id", "manufacturer_id"],
            ["identity_product_identity.id", "identity_product_identity.manufacturer_id"],
            name="fk_incident_identity_belongs_to_manufacturer",
        ),
    )
    op.create_index(
        "ix_incident_manufacturer_id", "investigation_fraud_incident", ["manufacturer_id"]
    )
    op.create_index("ix_incident_identity_id", "investigation_fraud_incident", ["identity_id"])
    op.create_index("ix_incident_status", "investigation_fraud_incident", ["status"])

    op.create_table(
        "investigation_incident_evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "incident_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("investigation_fraud_incident.id"),
            nullable=False,
        ),
        sa.Column(
            "manufacturer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("identity_manufacturer.id"),
            nullable=False,
        ),
        sa.Column(
            "evidence_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("detection_evidence.id"),
            nullable=False,
        ),
        sa.UniqueConstraint("incident_id", "evidence_id", name="uq_incident_evidence"),
    )
    op.create_index(
        "ix_incident_evidence_incident_id", "investigation_incident_evidence", ["incident_id"]
    )
    op.create_index(
        "ix_incident_evidence_manufacturer_id",
        "investigation_incident_evidence",
        ["manufacturer_id"],
    )

    op.create_table(
        "investigation_incident_event",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "incident_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("investigation_fraud_incident.id"),
            nullable=False,
        ),
        sa.Column(
            "manufacturer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("identity_manufacturer.id"),
            nullable=False,
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("previous_status", sa.String(length=32), nullable=True),
        sa.Column("new_status", sa.String(length=32), nullable=False),
        sa.Column("note", sa.String(length=2000), nullable=True),
        sa.Column("actor", sa.String(length=255), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("previous_event_hash", sa.LargeBinary(), nullable=False),
        sa.Column("event_hash", sa.LargeBinary(), nullable=False),
        sa.UniqueConstraint("incident_id", "sequence", name="uq_incident_event_sequence"),
        sa.UniqueConstraint("event_hash", name="uq_incident_event_hash"),
        sa.ForeignKeyConstraint(
            ["incident_id", "manufacturer_id"],
            [
                "investigation_fraud_incident.id",
                "investigation_fraud_incident.manufacturer_id",
            ],
            name="fk_incident_event_incident_belongs_to_manufacturer",
        ),
    )
    op.create_index(
        "ix_incident_event_incident_id", "investigation_incident_event", ["incident_id"]
    )
    op.create_index(
        "ix_incident_event_manufacturer_id",
        "investigation_incident_event",
        ["manufacturer_id"],
    )


def upgrade() -> None:
    _create_risk_tables()
    _create_investigation_tables()

    op.execute(_REQUIRE_CITATION_FUNCTION)
    op.execute(_REQUIRE_CITATION_TRIGGER)

    for table in _APPEND_ONLY_TABLES:
        op.execute(f"REVOKE UPDATE, DELETE, TRUNCATE ON {table} FROM bharosa_app")
    op.execute("REVOKE DELETE, TRUNCATE ON investigation_fraud_incident FROM bharosa_app")

    for table in _SECURED_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {table} FOR ALL TO bharosa_app "
            f"USING ({_TENANT_PREDICATE}) WITH CHECK ({_TENANT_PREDICATE})"
        )

    op.execute(_RISK_FLAG_VIEW)
    op.execute(_INCIDENT_FLAG_VIEW)
    for view in ("verification_identity_risk_flag", "verification_identity_incident_flag"):
        op.execute(f"GRANT SELECT ON {view} TO bharosa_verifier")
        op.execute(f"GRANT SELECT ON {view} TO bharosa_app")


def downgrade() -> None:
    for view in ("verification_identity_incident_flag", "verification_identity_risk_flag"):
        op.execute(f"REVOKE SELECT ON {view} FROM bharosa_app")
        op.execute(f"REVOKE SELECT ON {view} FROM bharosa_verifier")
        op.execute(f"DROP VIEW {view}")

    for table in _SECURED_TABLES:
        op.execute(f"DROP POLICY tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    op.execute(
        "DROP TRIGGER fraud_incident_requires_evidence ON investigation_fraud_incident"
    )
    op.execute("DROP FUNCTION fraud_incident_requires_evidence()")

    op.drop_index(
        "ix_incident_event_manufacturer_id", table_name="investigation_incident_event"
    )
    op.drop_index("ix_incident_event_incident_id", table_name="investigation_incident_event")
    op.drop_table("investigation_incident_event")

    op.drop_index(
        "ix_incident_evidence_manufacturer_id", table_name="investigation_incident_evidence"
    )
    op.drop_index(
        "ix_incident_evidence_incident_id", table_name="investigation_incident_evidence"
    )
    op.drop_table("investigation_incident_evidence")

    op.drop_index("ix_incident_status", table_name="investigation_fraud_incident")
    op.drop_index("ix_incident_identity_id", table_name="investigation_fraud_incident")
    op.drop_index("ix_incident_manufacturer_id", table_name="investigation_fraud_incident")
    op.drop_table("investigation_fraud_incident")

    op.drop_index(
        "ix_risk_contribution_manufacturer_id", table_name="risk_assessment_contribution"
    )
    op.drop_index(
        "ix_risk_contribution_assessment_id", table_name="risk_assessment_contribution"
    )
    op.drop_table("risk_assessment_contribution")

    op.drop_index("ix_risk_assessment_confidence", table_name="risk_assessment")
    op.drop_index("ix_risk_assessment_identity_id", table_name="risk_assessment")
    op.drop_index("ix_risk_assessment_manufacturer_id", table_name="risk_assessment")
    op.drop_table("risk_assessment")
