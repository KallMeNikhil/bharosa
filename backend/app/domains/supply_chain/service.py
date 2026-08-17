from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domains.identity import ProductIdentity
from app.domains.supply_chain.models import (
    ChannelAuthorization,
    ParticipantRole,
    SupplyChainEvent,
    SupplyChainEventType,
    SupplyChainParticipant,
    Territory,
)


class CrossManufacturerReferenceError(ValueError):
    def __init__(
        self, *, entity: str, expected_manufacturer_id: uuid.UUID, actual_manufacturer_id: uuid.UUID
    ) -> None:
        self.entity = entity
        self.expected_manufacturer_id = expected_manufacturer_id
        self.actual_manufacturer_id = actual_manufacturer_id
        super().__init__(
            f"{entity} belongs to manufacturer {actual_manufacturer_id!r}, but this "
            f"operation is scoped to manufacturer {expected_manufacturer_id!r}. A "
            f"supply-chain relationship can never cross a manufacturer boundary."
        )


class InvalidTerritoryGeometryError(ValueError):
    pass


class InvalidAuthorizationValidityError(ValueError):
    pass


class SupplyChainEventValidationError(ValueError):
    pass


def register_participant(
    db: Session,
    *,
    manufacturer_id: uuid.UUID,
    participant_ref: str,
    name: str,
    role: ParticipantRole,
) -> SupplyChainParticipant:
    participant = SupplyChainParticipant(
        manufacturer_id=manufacturer_id,
        participant_ref=participant_ref,
        name=name,
        role=role,
    )
    db.add(participant)
    db.flush()
    return participant


def _boundary_is_valid_geometry(db: Session, boundary_wkt: str) -> bool:
    result = db.execute(select(func.ST_IsValid(func.ST_GeomFromText(boundary_wkt, 4326)))).scalar()
    return bool(result)


def define_territory(
    db: Session,
    *,
    manufacturer_id: uuid.UUID,
    territory_ref: str,
    name: str,
    boundary_wkt: str,
) -> Territory:
    if not _boundary_is_valid_geometry(db, boundary_wkt):
        raise InvalidTerritoryGeometryError(
            f"Territory boundary WKT is not a valid geometry: {boundary_wkt!r}"
        )

    territory = Territory(
        manufacturer_id=manufacturer_id,
        territory_ref=territory_ref,
        name=name,
        boundary=boundary_wkt,
    )
    db.add(territory)
    db.flush()
    return territory


def territory_contains_point(
    db: Session, *, territory: Territory, longitude: float, latitude: float
) -> bool:
    point_wkt = f"POINT({longitude} {latitude})"
    result = db.execute(
        select(func.ST_Contains(territory.boundary, func.ST_GeomFromText(point_wkt, 4326)))
    ).scalar()
    return bool(result)


def grant_channel_authorization(
    db: Session,
    *,
    manufacturer_id: uuid.UUID,
    participant: SupplyChainParticipant,
    territory: Territory,
    valid_from: datetime | None = None,
    valid_until: datetime | None = None,
) -> ChannelAuthorization:
    if participant.manufacturer_id != manufacturer_id:
        raise CrossManufacturerReferenceError(
            entity="SupplyChainParticipant",
            expected_manufacturer_id=manufacturer_id,
            actual_manufacturer_id=participant.manufacturer_id,
        )
    if territory.manufacturer_id != manufacturer_id:
        raise CrossManufacturerReferenceError(
            entity="Territory",
            expected_manufacturer_id=manufacturer_id,
            actual_manufacturer_id=territory.manufacturer_id,
        )

    effective_from = valid_from or datetime.now(UTC)
    if valid_until is not None and valid_until <= effective_from:
        raise InvalidAuthorizationValidityError("valid_until must be strictly after valid_from")

    authorization = ChannelAuthorization(
        manufacturer_id=manufacturer_id,
        participant_id=participant.id,
        territory_id=territory.id,
        valid_from=effective_from,
        valid_until=valid_until,
    )
    db.add(authorization)
    db.flush()
    return authorization


def revoke_channel_authorization(
    db: Session,
    *,
    authorization: ChannelAuthorization,
    revoked_at: datetime | None = None,
) -> ChannelAuthorization:
    effective_revoked_at = revoked_at or datetime.now(UTC)
    if effective_revoked_at <= authorization.valid_from:
        raise InvalidAuthorizationValidityError(
            "An authorization cannot be revoked at or before its own valid_from"
        )
    authorization.valid_until = effective_revoked_at
    db.flush()
    return authorization


def is_authorization_active_at(authorization: ChannelAuthorization, at: datetime) -> bool:
    if at < authorization.valid_from:
        return False
    if authorization.valid_until is not None and at >= authorization.valid_until:
        return False
    return True


def _validate_participant(
    participant: SupplyChainParticipant | None, *, manufacturer_id: uuid.UUID
) -> uuid.UUID | None:
    if participant is None:
        return None
    if participant.manufacturer_id != manufacturer_id:
        raise CrossManufacturerReferenceError(
            entity="SupplyChainParticipant",
            expected_manufacturer_id=manufacturer_id,
            actual_manufacturer_id=participant.manufacturer_id,
        )
    return participant.id


def _validate_related_event(
    related_event: SupplyChainEvent | None, *, manufacturer_id: uuid.UUID
) -> uuid.UUID | None:
    if related_event is None:
        return None
    if related_event.manufacturer_id != manufacturer_id:
        raise CrossManufacturerReferenceError(
            entity="SupplyChainEvent",
            expected_manufacturer_id=manufacturer_id,
            actual_manufacturer_id=related_event.manufacturer_id,
        )
    return related_event.id


def _validate_related_identity(
    related_identity: ProductIdentity | None,
    *,
    manufacturer_id: uuid.UUID,
    identity_id: uuid.UUID,
) -> uuid.UUID | None:
    if related_identity is None:
        return None
    if related_identity.manufacturer_id != manufacturer_id:
        raise CrossManufacturerReferenceError(
            entity="ProductIdentity",
            expected_manufacturer_id=manufacturer_id,
            actual_manufacturer_id=related_identity.manufacturer_id,
        )
    if related_identity.id == identity_id:
        raise SupplyChainEventValidationError(
            "related_identity_id must reference a different ProductIdentity; one "
            "physical identity can never be its own replacement."
        )
    return related_identity.id


def _create_event(
    db: Session,
    *,
    identity: ProductIdentity,
    event_type: SupplyChainEventType,
    occurred_at: datetime,
    source_participant: SupplyChainParticipant | None = None,
    destination_participant: SupplyChainParticipant | None = None,
    reason: str | None = None,
    related_event: SupplyChainEvent | None = None,
    related_identity: ProductIdentity | None = None,
) -> SupplyChainEvent:
    manufacturer_id = identity.manufacturer_id
    source_id = _validate_participant(source_participant, manufacturer_id=manufacturer_id)
    destination_id = _validate_participant(
        destination_participant, manufacturer_id=manufacturer_id
    )
    related_event_id = _validate_related_event(related_event, manufacturer_id=manufacturer_id)
    related_identity_id = _validate_related_identity(
        related_identity, manufacturer_id=manufacturer_id, identity_id=identity.id
    )

    event = SupplyChainEvent(
        manufacturer_id=manufacturer_id,
        identity_id=identity.id,
        event_type=event_type,
        source_participant_id=source_id,
        destination_participant_id=destination_id,
        related_event_id=related_event_id,
        related_identity_id=related_identity_id,
        reason=reason,
        occurred_at=occurred_at,
    )
    db.add(event)
    db.flush()
    return event


def record_dispatch(
    db: Session,
    *,
    identity: ProductIdentity,
    occurred_at: datetime,
    destination_participant: SupplyChainParticipant,
    source_participant: SupplyChainParticipant | None = None,
    reason: str | None = None,
) -> SupplyChainEvent:
    if destination_participant is None:
        raise SupplyChainEventValidationError("DISPATCH requires a destination_participant")
    return _create_event(
        db,
        identity=identity,
        event_type=SupplyChainEventType.DISPATCH,
        occurred_at=occurred_at,
        source_participant=source_participant,
        destination_participant=destination_participant,
        reason=reason,
    )


def record_receipt(
    db: Session,
    *,
    identity: ProductIdentity,
    occurred_at: datetime,
    source_participant: SupplyChainParticipant,
    destination_participant: SupplyChainParticipant,
    reason: str | None = None,
) -> SupplyChainEvent:
    if source_participant is None or destination_participant is None:
        raise SupplyChainEventValidationError(
            "RECEIPT requires both source_participant and destination_participant"
        )
    return _create_event(
        db,
        identity=identity,
        event_type=SupplyChainEventType.RECEIPT,
        occurred_at=occurred_at,
        source_participant=source_participant,
        destination_participant=destination_participant,
        reason=reason,
    )


def record_transfer(
    db: Session,
    *,
    identity: ProductIdentity,
    occurred_at: datetime,
    source_participant: SupplyChainParticipant,
    destination_participant: SupplyChainParticipant,
    reason: str | None = None,
) -> SupplyChainEvent:
    if source_participant is None or destination_participant is None:
        raise SupplyChainEventValidationError(
            "TRANSFER requires both source_participant and destination_participant"
        )
    return _create_event(
        db,
        identity=identity,
        event_type=SupplyChainEventType.TRANSFER,
        occurred_at=occurred_at,
        source_participant=source_participant,
        destination_participant=destination_participant,
        reason=reason,
    )


def record_return(
    db: Session,
    *,
    identity: ProductIdentity,
    occurred_at: datetime,
    source_participant: SupplyChainParticipant,
    destination_participant: SupplyChainParticipant,
    reason: str | None = None,
) -> SupplyChainEvent:
    if source_participant is None or destination_participant is None:
        raise SupplyChainEventValidationError(
            "RETURN requires both source_participant and destination_participant"
        )
    return _create_event(
        db,
        identity=identity,
        event_type=SupplyChainEventType.RETURN,
        occurred_at=occurred_at,
        source_participant=source_participant,
        destination_participant=destination_participant,
        reason=reason,
    )


def record_reallocation(
    db: Session,
    *,
    identity: ProductIdentity,
    occurred_at: datetime,
    source_participant: SupplyChainParticipant,
    destination_participant: SupplyChainParticipant,
    reason: str | None = None,
) -> SupplyChainEvent:
    if source_participant is None or destination_participant is None:
        raise SupplyChainEventValidationError(
            "REALLOCATION requires both source_participant and destination_participant"
        )
    return _create_event(
        db,
        identity=identity,
        event_type=SupplyChainEventType.REALLOCATION,
        occurred_at=occurred_at,
        source_participant=source_participant,
        destination_participant=destination_participant,
        reason=reason,
    )


def record_retail_placement(
    db: Session,
    *,
    identity: ProductIdentity,
    occurred_at: datetime,
    source_participant: SupplyChainParticipant,
    reason: str | None = None,
) -> SupplyChainEvent:
    if source_participant is None:
        raise SupplyChainEventValidationError("RETAIL_PLACEMENT requires a source_participant")
    return _create_event(
        db,
        identity=identity,
        event_type=SupplyChainEventType.RETAIL_PLACEMENT,
        occurred_at=occurred_at,
        source_participant=source_participant,
        destination_participant=None,
        reason=reason,
    )


def record_custody_adjustment(
    db: Session,
    *,
    identity: ProductIdentity,
    occurred_at: datetime,
    reason: str,
    source_participant: SupplyChainParticipant | None = None,
    destination_participant: SupplyChainParticipant | None = None,
    related_event: SupplyChainEvent | None = None,
    related_identity: ProductIdentity | None = None,
) -> SupplyChainEvent:
    if not reason or not reason.strip():
        raise SupplyChainEventValidationError("CUSTODY_ADJUSTMENT requires a non-empty reason")
    if not any([source_participant, destination_participant, related_event, related_identity]):
        raise SupplyChainEventValidationError(
            "CUSTODY_ADJUSTMENT requires at least one contextual reference: a "
            "source_participant, destination_participant, related_event, or "
            "related_identity"
        )
    return _create_event(
        db,
        identity=identity,
        event_type=SupplyChainEventType.CUSTODY_ADJUSTMENT,
        occurred_at=occurred_at,
        source_participant=source_participant,
        destination_participant=destination_participant,
        reason=reason,
        related_event=related_event,
        related_identity=related_identity,
    )
