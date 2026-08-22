from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.authorization import ActorContext
from app.domains.detection import DEFAULT_THRESHOLDS, FraudFamily, SignalType
from app.domains.identity import LifecycleState, ProductIdentity, reserve_identity
from app.domains.simulation.generator import (
    CITY_COORDINATES,
    Topology,
    issue_legitimate_identity,
    jittered_point,
    record_diversion_custody,
    record_legitimate_custody,
    record_scan,
)
from app.domains.simulation.models import GroundTruthClassification
from app.domains.simulation.rng import SimulationRandom
from app.domains.verification import VerificationChannel

COMBINED_INJECTION_LABEL = "COMBINED"


@dataclass(frozen=True)
class GroundTruthDraft:
    classification: GroundTruthClassification
    injection_type: str | None
    expected_signal_types: tuple[SignalType, ...]
    notes: str


def legitimate_draft(notes: str) -> GroundTruthDraft:
    return GroundTruthDraft(
        classification=GroundTruthClassification.LEGITIMATE,
        injection_type=None,
        expected_signal_types=(),
        notes=notes,
    )


def inject_full_counterfeit(
    db: Session,
    *,
    topology: Topology,
    rng: SimulationRandom,
    actor: ActorContext,
    base_time: datetime,
) -> tuple[ProductIdentity, GroundTruthDraft]:
    identity = reserve_identity(db, batch_id=topology.batch.id, serial=rng.serial())
    assert identity.lifecycle_state is LifecycleState.RESERVED

    record_scan(
        db,
        serial=identity.serial,
        occurred_at=base_time + timedelta(hours=1),
        location=jittered_point(rng, CITY_COORDINATES[0]),
        channel=VerificationChannel.WEB,
    )
    return identity, GroundTruthDraft(
        classification=GroundTruthClassification.INJECTED_FRAUD,
        injection_type=FraudFamily.FULL_COUNTERFEIT.value,
        expected_signal_types=(SignalType.SIGNATURE_INVALID,),
        notes=(
            "Identity was reserved but never signed or activated, then "
            "scanned as a counterfeiter guessing at an unissued identity "
            "slot would present it."
        ),
    )


def inject_code_cloning(
    db: Session,
    *,
    topology: Topology,
    rng: SimulationRandom,
    actor: ActorContext,
    base_time: datetime,
) -> tuple[ProductIdentity, GroundTruthDraft]:
    identity = issue_legitimate_identity(db, topology=topology, rng=rng, actor=actor)
    placement_time = record_legitimate_custody(
        db, identity=identity, topology=topology, actor=actor, base_time=base_time
    )

    scan_time = placement_time + timedelta(hours=1)
    for city in CITY_COORDINATES:
        record_scan(db, serial=identity.serial, occurred_at=scan_time, location=city)
        scan_time += timedelta(minutes=20)

    return identity, GroundTruthDraft(
        classification=GroundTruthClassification.INJECTED_FRAUD,
        injection_type=FraudFamily.CODE_CLONING.value,
        expected_signal_types=(SignalType.IMPOSSIBLE_TRAVEL, SignalType.GEOGRAPHIC_SPREAD),
        notes=(
            "One legitimately issued identity was scanned from four widely "
            "separated cities within minutes of each other, as a cloned code "
            "circulating on multiple physical packs would be."
        ),
    )


def inject_refilling(
    db: Session,
    *,
    topology: Topology,
    rng: SimulationRandom,
    actor: ActorContext,
    base_time: datetime,
) -> tuple[ProductIdentity, GroundTruthDraft]:
    identity = issue_legitimate_identity(db, topology=topology, rng=rng, actor=actor)
    placement_time = record_legitimate_custody(
        db, identity=identity, topology=topology, actor=actor, base_time=base_time
    )

    grace_hours = DEFAULT_THRESHOLDS.post_sale_grace_hours
    scan_time = placement_time + timedelta(hours=grace_hours + 24)
    for _ in range(DEFAULT_THRESHOLDS.post_sale_scan_count + 1):
        record_scan(
            db,
            serial=identity.serial,
            occurred_at=scan_time,
            location=jittered_point(rng, CITY_COORDINATES[0]),
        )
        scan_time += timedelta(hours=6)

    return identity, GroundTruthDraft(
        classification=GroundTruthClassification.INJECTED_FRAUD,
        injection_type=FraudFamily.REFILLING.value,
        expected_signal_types=(SignalType.POST_SALE_SCAN_RESURGENCE,),
        notes=(
            "A retail-placed identity generated a burst of scans well past "
            "the post-sale grace period, as a refilled container reentering "
            "circulation would."
        ),
    )


def inject_diversion(
    db: Session,
    *,
    topology: Topology,
    rng: SimulationRandom,
    actor: ActorContext,
    base_time: datetime,
) -> tuple[ProductIdentity, GroundTruthDraft]:
    identity = issue_legitimate_identity(db, topology=topology, rng=rng, actor=actor)
    record_diversion_custody(
        db, identity=identity, topology=topology, actor=actor, base_time=base_time
    )

    return identity, GroundTruthDraft(
        classification=GroundTruthClassification.INJECTED_FRAUD,
        injection_type=FraudFamily.DIVERSION.value,
        expected_signal_types=(SignalType.CHANNEL_VIOLATION,),
        notes=(
            "A legitimately issued identity was transferred to a distributor "
            "holding no channel authorization from this manufacturer, as "
            "diverted stock would be."
        ),
    )


def inject_combined(
    db: Session,
    *,
    topology: Topology,
    rng: SimulationRandom,
    actor: ActorContext,
    base_time: datetime,
) -> tuple[ProductIdentity, GroundTruthDraft]:
    identity = issue_legitimate_identity(db, topology=topology, rng=rng, actor=actor)
    diverted_time = record_diversion_custody(
        db, identity=identity, topology=topology, actor=actor, base_time=base_time
    )

    scan_time = diverted_time + timedelta(hours=2)
    for city in CITY_COORDINATES:
        record_scan(db, serial=identity.serial, occurred_at=scan_time, location=city)
        scan_time += timedelta(minutes=15)

    return identity, GroundTruthDraft(
        classification=GroundTruthClassification.INJECTED_FRAUD,
        injection_type=COMBINED_INJECTION_LABEL,
        expected_signal_types=(
            SignalType.IMPOSSIBLE_TRAVEL,
            SignalType.GEOGRAPHIC_SPREAD,
            SignalType.CHANNEL_VIOLATION,
        ),
        notes=(
            "A single identity received both the diversion and cloning "
            "treatment, to exercise cross-family evidence correlation and "
            "risk escalation."
        ),
    )
