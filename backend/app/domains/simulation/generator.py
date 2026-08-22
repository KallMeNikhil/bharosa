from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.authorization import ActorContext, Capability
from app.domains.detection import DEFAULT_THRESHOLDS
from app.domains.identity import (
    Batch,
    LifecycleState,
    Manufacturer,
    ManufacturerKey,
    Product,
    ProductIdentity,
    Signer,
    issue_manufacturer_key,
    open_batch,
    register_product,
    reserve_identity,
    sign_identity,
    transition_identity,
)
from app.domains.simulation.rng import SimulationRandom
from app.domains.supply_chain import (
    ParticipantRole,
    SupplyChainParticipant,
    Territory,
    define_territory,
    grant_channel_authorization,
    record_dispatch,
    record_reallocation,
    record_retail_placement,
    record_return,
    record_transfer,
    register_participant,
)
from app.domains.verification import (
    NO_RISK_SIGNALS,
    ScanLocation,
    VerificationChannel,
    VerificationRequest,
    verify,
)

SIMULATION_ACTOR_ID = "simulation-engine"

CITY_COORDINATES: tuple[tuple[float, float], ...] = (
    (77.5946, 12.9716),
    (72.8777, 19.0760),
    (80.2707, 13.0827),
    (78.4867, 17.3850),
)

TERRITORY_WKT = "MULTIPOLYGON(((68 6, 68 32, 92 32, 92 6, 68 6)))"

_ACTIVATION_PATH = (
    LifecycleState.PRINTED,
    LifecycleState.PRINT_VERIFIED,
    LifecycleState.RECONCILED,
    LifecycleState.ACTIVATED,
)


def simulation_actor(manufacturer_id: uuid.UUID) -> ActorContext:
    return ActorContext(
        actor_id=SIMULATION_ACTOR_ID,
        manufacturer_id=manufacturer_id,
        capabilities=frozenset(Capability),
    )


@dataclass(frozen=True)
class Topology:
    manufacturer: Manufacturer
    manufacturer_key: ManufacturerKey
    key_handle: str
    signer: Signer
    product: Product
    batch: Batch
    depot: SupplyChainParticipant
    distributor: SupplyChainParticipant
    unauthorized_distributor: SupplyChainParticipant
    retailer: SupplyChainParticipant
    retailer_b: SupplyChainParticipant
    territory: Territory


def build_topology(
    db: Session,
    *,
    manufacturer: Manufacturer,
    signer: Signer,
    run_ref: str,
    key_version: int,
    actor: ActorContext,
    now: datetime,
) -> Topology:
    issued = issue_manufacturer_key(
        db, manufacturer_id=manufacturer.id, signer=signer, key_version=key_version, actor=actor
    )
    product = register_product(
        db,
        manufacturer_id=manufacturer.id,
        product_ref=f"SIM-{run_ref}-PRODUCT",
        name="Simulation Test Product",
        gtin=None,
    )
    batch = open_batch(
        db,
        product_id=product.id,
        batch_ref=f"SIM-{run_ref}-BATCH",
        manufacturing_date=(now - timedelta(days=30)).date(),
        expiry_date=(now + timedelta(days=700)).date(),
    )
    depot = register_participant(
        db,
        manufacturer_id=manufacturer.id,
        participant_ref=f"SIM-{run_ref}-DEPOT",
        name="Simulation Depot",
        role=ParticipantRole.DEPOT,
        actor=actor,
    )
    distributor = register_participant(
        db,
        manufacturer_id=manufacturer.id,
        participant_ref=f"SIM-{run_ref}-DIST",
        name="Simulation Distributor",
        role=ParticipantRole.DISTRIBUTOR,
        actor=actor,
    )
    unauthorized_distributor = register_participant(
        db,
        manufacturer_id=manufacturer.id,
        participant_ref=f"SIM-{run_ref}-DIST-UNAUTH",
        name="Simulation Unauthorized Distributor",
        role=ParticipantRole.DISTRIBUTOR,
        actor=actor,
    )
    retailer = register_participant(
        db,
        manufacturer_id=manufacturer.id,
        participant_ref=f"SIM-{run_ref}-RET",
        name="Simulation Retailer",
        role=ParticipantRole.RETAILER,
        actor=actor,
    )
    retailer_b = register_participant(
        db,
        manufacturer_id=manufacturer.id,
        participant_ref=f"SIM-{run_ref}-RET-B",
        name="Simulation Retailer B",
        role=ParticipantRole.RETAILER,
        actor=actor,
    )
    territory = define_territory(
        db,
        manufacturer_id=manufacturer.id,
        territory_ref=f"SIM-{run_ref}-TERRITORY",
        name="Simulation Territory",
        boundary_wkt=TERRITORY_WKT,
        actor=actor,
    )
    for participant in (distributor, retailer, retailer_b):
        grant_channel_authorization(
            db,
            manufacturer_id=manufacturer.id,
            participant=participant,
            territory=territory,
            actor=actor,
        )
    return Topology(
        manufacturer=manufacturer,
        manufacturer_key=issued.manufacturer_key,
        key_handle=issued.key_handle,
        signer=signer,
        product=product,
        batch=batch,
        depot=depot,
        distributor=distributor,
        unauthorized_distributor=unauthorized_distributor,
        retailer=retailer,
        retailer_b=retailer_b,
        territory=territory,
    )


def activate_identity(
    db: Session, *, identity: ProductIdentity, actor: ActorContext
) -> ProductIdentity:
    for state in _ACTIVATION_PATH:
        identity = transition_identity(db, identity=identity, new_state=state, actor=actor)
    return identity


def issue_legitimate_identity(
    db: Session, *, topology: Topology, rng: SimulationRandom, actor: ActorContext
) -> ProductIdentity:
    identity = reserve_identity(db, batch_id=topology.batch.id, serial=rng.serial())
    identity = sign_identity(
        db,
        identity=identity,
        manufacturer_key=topology.manufacturer_key,
        signer=topology.signer,
        key_handle=topology.key_handle,
        actor=actor,
    )
    return activate_identity(db, identity=identity, actor=actor)


def record_legitimate_custody(
    db: Session,
    *,
    identity: ProductIdentity,
    topology: Topology,
    actor: ActorContext,
    base_time: datetime,
) -> datetime:
    dispatch_time = base_time
    depot_to_distributor = base_time + timedelta(hours=6)
    distributor_to_retailer = base_time + timedelta(hours=30)
    placement_time = base_time + timedelta(hours=54)

    record_dispatch(
        db,
        identity=identity,
        occurred_at=dispatch_time,
        actor=actor,
        destination_participant=topology.depot,
    )
    record_transfer(
        db,
        identity=identity,
        occurred_at=depot_to_distributor,
        actor=actor,
        source_participant=topology.depot,
        destination_participant=topology.distributor,
    )
    record_transfer(
        db,
        identity=identity,
        occurred_at=distributor_to_retailer,
        actor=actor,
        source_participant=topology.distributor,
        destination_participant=topology.retailer,
    )
    record_retail_placement(
        db,
        identity=identity,
        occurred_at=placement_time,
        actor=actor,
        source_participant=topology.retailer,
    )
    return placement_time


def record_diversion_custody(
    db: Session,
    *,
    identity: ProductIdentity,
    topology: Topology,
    actor: ActorContext,
    base_time: datetime,
) -> datetime:
    dispatch_time = base_time
    diverted_transfer_time = base_time + timedelta(hours=6)

    record_dispatch(
        db,
        identity=identity,
        occurred_at=dispatch_time,
        actor=actor,
        destination_participant=topology.depot,
    )
    record_transfer(
        db,
        identity=identity,
        occurred_at=diverted_transfer_time,
        actor=actor,
        source_participant=topology.depot,
        destination_participant=topology.unauthorized_distributor,
    )
    return diverted_transfer_time


def jittered_point(rng: SimulationRandom, base: tuple[float, float]) -> tuple[float, float]:
    longitude, latitude = base
    return (longitude + rng.uniform(-0.01, 0.01), latitude + rng.uniform(-0.01, 0.01))


def record_scan(
    db: Session,
    *,
    serial: str,
    occurred_at: datetime,
    location: tuple[float, float] | None = None,
    channel: VerificationChannel = VerificationChannel.RETAILER_APP,
) -> None:
    scan_location = None
    if location is not None:
        scan_location = ScanLocation(longitude=location[0], latitude=location[1])
    verify(
        db,
        VerificationRequest(
            channel=channel,
            occurred_at=occurred_at.astimezone(UTC),
            serial=serial,
            location=scan_location,
        ),
        risk_signals=NO_RISK_SIGNALS,
    )


def record_legitimate_scans(
    db: Session,
    *,
    identity: ProductIdentity,
    rng: SimulationRandom,
    placement_time: datetime,
    count: int = 2,
) -> None:
    scan_time = placement_time + timedelta(hours=2)
    for _ in range(count):
        record_scan(
            db,
            serial=identity.serial,
            occurred_at=scan_time,
            location=jittered_point(rng, CITY_COORDINATES[0]),
        )
        scan_time += timedelta(hours=6)


def build_legitimate_population(
    db: Session,
    *,
    topology: Topology,
    rng: SimulationRandom,
    actor: ActorContext,
    base_time: datetime,
) -> ProductIdentity:
    identity = issue_legitimate_identity(db, topology=topology, rng=rng, actor=actor)
    placement_time = record_legitimate_custody(
        db, identity=identity, topology=topology, actor=actor, base_time=base_time
    )
    record_legitimate_scans(db, identity=identity, rng=rng, placement_time=placement_time)
    return identity


def build_benign_unusual_population(
    db: Session,
    *,
    topology: Topology,
    rng: SimulationRandom,
    actor: ActorContext,
    base_time: datetime,
) -> ProductIdentity:
    identity = issue_legitimate_identity(db, topology=topology, rng=rng, actor=actor)

    dispatch_time = base_time
    depot_to_distributor = base_time + timedelta(hours=6)
    distributor_to_retailer = base_time + timedelta(hours=30)
    return_time = distributor_to_retailer + timedelta(hours=12)
    reallocation_time = return_time + timedelta(hours=6)
    placement_time = reallocation_time + timedelta(hours=6)

    record_dispatch(
        db,
        identity=identity,
        occurred_at=dispatch_time,
        actor=actor,
        destination_participant=topology.depot,
    )
    record_transfer(
        db,
        identity=identity,
        occurred_at=depot_to_distributor,
        actor=actor,
        source_participant=topology.depot,
        destination_participant=topology.distributor,
    )
    record_transfer(
        db,
        identity=identity,
        occurred_at=distributor_to_retailer,
        actor=actor,
        source_participant=topology.distributor,
        destination_participant=topology.retailer,
    )
    record_return(
        db,
        identity=identity,
        occurred_at=return_time,
        actor=actor,
        source_participant=topology.retailer,
        destination_participant=topology.distributor,
        reason="Simulated end-of-season unsold stock return.",
    )
    record_reallocation(
        db,
        identity=identity,
        occurred_at=reallocation_time,
        actor=actor,
        source_participant=topology.distributor,
        destination_participant=topology.retailer_b,
        reason="Simulated reallocation between the distributor's own retailers.",
    )
    record_retail_placement(
        db,
        identity=identity,
        occurred_at=placement_time,
        actor=actor,
        source_participant=topology.retailer_b,
    )

    scan_time = placement_time + timedelta(hours=4)
    for _ in range(min(5, DEFAULT_THRESHOLDS.scan_velocity_min_scans - 1)):
        record_scan(
            db,
            serial=identity.serial,
            occurred_at=scan_time,
            location=jittered_point(rng, CITY_COORDINATES[0]),
        )
        scan_time += timedelta(hours=3)

    return identity
