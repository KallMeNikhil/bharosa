from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from app.domains.detection import DEFAULT_THRESHOLDS, DetectionContext, DetectorThresholds
from app.domains.identity import LifecycleState, ProductIdentity
from app.domains.supply_chain import SupplyChainEvent, SupplyChainEventType
from app.domains.verification import VerificationEvent, VerificationState, coarse_cell

NOW = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)

BENGALURU = (77.5946, 12.9716)
MUMBAI = (72.8777, 19.0760)
CHENNAI = (80.2707, 13.0827)
HYDERABAD = (78.4867, 17.3850)

MANUFACTURER_ID = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")


def make_identity(lifecycle_state: LifecycleState = LifecycleState.ACTIVATED) -> ProductIdentity:
    return ProductIdentity(
        id=uuid.uuid4(),
        manufacturer_id=MANUFACTURER_ID,
        batch_id=uuid.uuid4(),
        serial="AAAAAAAAAAAAAAAAAAAAAAAAAA",
        lifecycle_state=lifecycle_state,
    )


def make_scan(
    *,
    at: datetime,
    coordinates: tuple[float, float] | None = None,
    signature_valid: bool = True,
    key_status: str | None = "ACTIVE",
    lifecycle_state: LifecycleState = LifecycleState.ACTIVATED,
    reported_accuracy_m: int | None = None,
) -> VerificationEvent:
    return VerificationEvent(
        id=uuid.uuid4(),
        manufacturer_id=MANUFACTURER_ID,
        identity_id=uuid.uuid4(),
        sequence=1,
        state=VerificationState.GENUINE,
        signature_valid=signature_valid,
        key_status_at_scan=key_status,
        lifecycle_state_at_scan=lifecycle_state.value,
        coarse_cell=coarse_cell(*coordinates) if coordinates else None,
        reported_accuracy_m=reported_accuracy_m,
        occurred_at=at,
    )


def make_supply_chain_event(
    *,
    at: datetime,
    event_type: SupplyChainEventType,
    destination_participant_id: uuid.UUID | None = None,
) -> SupplyChainEvent:
    return SupplyChainEvent(
        id=uuid.uuid4(),
        manufacturer_id=MANUFACTURER_ID,
        identity_id=uuid.uuid4(),
        sequence=1,
        event_type=event_type,
        destination_participant_id=destination_participant_id,
        occurred_at=at,
    )


def make_context(
    *,
    scans: list[VerificationEvent] | None = None,
    scan_coordinates: dict[uuid.UUID, tuple[float, float]] | None = None,
    supply_chain_events: list[SupplyChainEvent] | None = None,
    inside_territory: dict[uuid.UUID, bool] | None = None,
    custodian_authorized: dict[uuid.UUID, bool] | None = None,
    identity: ProductIdentity | None = None,
    thresholds: DetectorThresholds = DEFAULT_THRESHOLDS,
    now: datetime = NOW,
) -> DetectionContext:
    return DetectionContext(
        identity=identity or make_identity(),
        now=now,
        verification_events=tuple(scans or ()),
        supply_chain_events=tuple(supply_chain_events or ()),
        scan_coordinates=scan_coordinates or {},
        scan_inside_authorized_territory=inside_territory or {},
        custodian_authorized_at_event=custodian_authorized or {},
        thresholds=thresholds,
    )


def located_scans(
    entries: list[tuple[timedelta, tuple[float, float]]],
) -> tuple[list[VerificationEvent], dict[uuid.UUID, tuple[float, float]]]:
    scans = []
    coordinates = {}
    for offset, point in entries:
        scan = make_scan(at=NOW + offset, coordinates=point)
        scans.append(scan)
        coordinates[scan.id] = point
    return scans, coordinates
