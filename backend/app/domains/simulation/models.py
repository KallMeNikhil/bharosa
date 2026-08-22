from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    LargeBinary,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def _enum_column(enum_cls: type[enum.Enum], length: int = 32):
    return SAEnum(
        enum_cls,
        native_enum=False,
        length=length,
        values_callable=lambda e: [member.value for member in e],
    )


class ScenarioType(str, enum.Enum):
    LEGITIMATE_BASELINE = "LEGITIMATE_BASELINE"
    FULL_COUNTERFEIT = "FULL_COUNTERFEIT"
    CODE_CLONING = "CODE_CLONING"
    REFILLING = "REFILLING"
    DIVERSION = "DIVERSION"
    COMBINED_MULTI_SIGNAL = "COMBINED_MULTI_SIGNAL"
    BENIGN_ANOMALY = "BENIGN_ANOMALY"


class SimulationRunStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class GroundTruthClassification(str, enum.Enum):
    LEGITIMATE = "LEGITIMATE"
    INJECTED_FRAUD = "INJECTED_FRAUD"


class SimulationRun(Base):
    __tablename__ = "simulation_run"
    __table_args__ = (
        UniqueConstraint("id", "manufacturer_id", name="uq_simulation_run_id_manufacturer"),
        UniqueConstraint("manufacturer_id", "run_ref", name="uq_simulation_run_manufacturer_ref"),
        Index("ix_simulation_run_manufacturer_id", "manufacturer_id"),
        Index("ix_simulation_run_status", "status"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    manufacturer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity_manufacturer.id"), nullable=False
    )
    run_ref: Mapped[str] = mapped_column(String(64), nullable=False)
    scenario_type: Mapped[ScenarioType] = mapped_column(_enum_column(ScenarioType), nullable=False)
    seed: Mapped[int] = mapped_column(Integer, nullable=False)
    identity_count: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[SimulationRunStatus] = mapped_column(
        _enum_column(SimulationRunStatus), nullable=False, default=SimulationRunStatus.PENDING
    )
    triggered_by: Mapped[str] = mapped_column(String(255), nullable=False)
    error_message: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SimulationGroundTruthEntry(Base):
    __tablename__ = "simulation_ground_truth_entry"
    __table_args__ = (
        UniqueConstraint(
            "simulation_run_id", "sequence", name="uq_ground_truth_entry_sequence"
        ),
        UniqueConstraint("event_hash", name="uq_ground_truth_entry_hash"),
        ForeignKeyConstraint(
            ["simulation_run_id", "manufacturer_id"],
            ["simulation_run.id", "simulation_run.manufacturer_id"],
            name="fk_ground_truth_run_belongs_to_manufacturer",
        ),
        ForeignKeyConstraint(
            ["identity_id", "manufacturer_id"],
            ["identity_product_identity.id", "identity_product_identity.manufacturer_id"],
            name="fk_ground_truth_identity_belongs_to_manufacturer",
        ),
        Index("ix_ground_truth_entry_manufacturer_id", "manufacturer_id"),
        Index("ix_ground_truth_entry_simulation_run_id", "simulation_run_id"),
        Index("ix_ground_truth_entry_identity_id", "identity_id"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    manufacturer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity_manufacturer.id"), nullable=False
    )
    simulation_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    identity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    classification: Mapped[GroundTruthClassification] = mapped_column(
        _enum_column(GroundTruthClassification), nullable=False
    )
    injection_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    expected_signal_types: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    notes: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    previous_event_hash: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    event_hash: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)


class SimulationEvaluation(Base):
    __tablename__ = "simulation_evaluation"
    __table_args__ = (
        UniqueConstraint(
            "simulation_run_id", "sequence", name="uq_simulation_evaluation_sequence"
        ),
        UniqueConstraint("event_hash", name="uq_simulation_evaluation_hash"),
        ForeignKeyConstraint(
            ["simulation_run_id", "manufacturer_id"],
            ["simulation_run.id", "simulation_run.manufacturer_id"],
            name="fk_evaluation_run_belongs_to_manufacturer",
        ),
        CheckConstraint(
            "true_positive_count >= 0 AND false_positive_count >= 0 "
            "AND true_negative_count >= 0 AND false_negative_count >= 0",
            name="ck_simulation_evaluation_counts_non_negative",
        ),
        Index("ix_simulation_evaluation_manufacturer_id", "manufacturer_id"),
        Index("ix_simulation_evaluation_simulation_run_id", "simulation_run_id"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    manufacturer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity_manufacturer.id"), nullable=False
    )
    simulation_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)

    true_positive_count: Mapped[int] = mapped_column(Integer, nullable=False)
    false_positive_count: Mapped[int] = mapped_column(Integer, nullable=False)
    true_negative_count: Mapped[int] = mapped_column(Integer, nullable=False)
    false_negative_count: Mapped[int] = mapped_column(Integer, nullable=False)

    precision: Mapped[float | None] = mapped_column(Float, nullable=True)
    recall: Mapped[float | None] = mapped_column(Float, nullable=True)
    detection_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    missed_fraud_rate: Mapped[float | None] = mapped_column(Float, nullable=True)

    investigation_true_positive_count: Mapped[int] = mapped_column(Integer, nullable=False)
    investigation_false_positive_count: Mapped[int] = mapped_column(Integer, nullable=False)

    per_detector_breakdown: Mapped[dict] = mapped_column(JSONB, nullable=False)

    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    previous_event_hash: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    event_hash: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
