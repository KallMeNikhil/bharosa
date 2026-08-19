from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from app.domains.detection.thresholds import DEFAULT_THRESHOLDS, DetectorThresholds
from app.domains.identity import IdentityIssuanceEvent, ProductIdentity
from app.domains.supply_chain import SupplyChainEvent
from app.domains.verification import VerificationEvent


@dataclass(frozen=True)
class DetectionContext:
    """Everything a detector is allowed to see.

    Detectors are pure functions of this structure. Spatial and authorization
    lookups are resolved by the service before a detector runs, so that
    detector logic stays independently testable and a detector can never widen
    its own view of the data by issuing a query of its own.
    """

    identity: ProductIdentity
    now: datetime
    verification_events: tuple[VerificationEvent, ...] = ()
    supply_chain_events: tuple[SupplyChainEvent, ...] = ()
    identity_issuance_events: tuple[IdentityIssuanceEvent, ...] = ()
    scan_coordinates: dict[uuid.UUID, tuple[float, float]] = field(default_factory=dict)
    scan_inside_authorized_territory: dict[uuid.UUID, bool] = field(default_factory=dict)
    custodian_authorized_at_event: dict[uuid.UUID, bool] = field(default_factory=dict)
    thresholds: DetectorThresholds = DEFAULT_THRESHOLDS

    @property
    def located_verification_events(self) -> list[VerificationEvent]:
        return [
            event for event in self.verification_events if event.id in self.scan_coordinates
        ]
