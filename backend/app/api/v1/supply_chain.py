from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api import schemas
from app.api.deps import current_actor, owned_or_404, requires, tenant_db
from app.core.authorization import ActorContext, Capability
from app.domains.identity import ProductIdentity
from app.domains.supply_chain import (
    ChannelAuthorization,
    SupplyChainEvent,
    SupplyChainEventType,
    SupplyChainParticipant,
    Territory,
    current_custodian_id,
    define_territory,
    grant_channel_authorization,
    identity_event_history,
    record_custody_adjustment,
    record_dispatch,
    record_reallocation,
    record_receipt,
    record_retail_placement,
    record_return,
    record_transfer,
    register_participant,
    revoke_channel_authorization,
)

router = APIRouter(prefix="/supply-chain", tags=["supply chain"])


@router.post(
    "/participants",
    response_model=schemas.ParticipantView,
    status_code=status.HTTP_201_CREATED,
)
def create_participant(
    body: schemas.ParticipantCreate,
    actor: ActorContext = Depends(
        requires(Capability.MANAGE_SUPPLY_CHAIN_REFERENCE_DATA)
    ),
    db: Session = Depends(tenant_db),
) -> SupplyChainParticipant:
    participant = register_participant(
        db,
        manufacturer_id=actor.manufacturer_id,
        participant_ref=body.participant_ref,
        name=body.name,
        role=body.role,
        actor=actor,
    )
    db.commit()
    return participant


@router.get("/participants", response_model=list[schemas.ParticipantView])
def list_participants(db: Session = Depends(tenant_db)) -> list[SupplyChainParticipant]:
    return list(
        db.execute(
            select(SupplyChainParticipant).order_by(SupplyChainParticipant.participant_ref)
        )
        .scalars()
        .all()
    )


@router.post(
    "/territories",
    response_model=schemas.TerritoryView,
    status_code=status.HTTP_201_CREATED,
)
def create_territory(
    body: schemas.TerritoryCreate,
    actor: ActorContext = Depends(
        requires(Capability.MANAGE_SUPPLY_CHAIN_REFERENCE_DATA)
    ),
    db: Session = Depends(tenant_db),
) -> Territory:
    territory = define_territory(
        db,
        manufacturer_id=actor.manufacturer_id,
        territory_ref=body.territory_ref,
        name=body.name,
        boundary_wkt=body.boundary_wkt,
        actor=actor,
    )
    db.commit()
    return territory


@router.get("/territories", response_model=list[schemas.TerritoryView])
def list_territories(db: Session = Depends(tenant_db)) -> list[Territory]:
    return list(
        db.execute(select(Territory).order_by(Territory.territory_ref)).scalars().all()
    )


@router.post(
    "/channel-authorizations",
    response_model=schemas.ChannelAuthorizationView,
    status_code=status.HTTP_201_CREATED,
)
def create_channel_authorization(
    body: schemas.ChannelAuthorizationCreate,
    actor: ActorContext = Depends(
        requires(Capability.MANAGE_SUPPLY_CHAIN_REFERENCE_DATA)
    ),
    db: Session = Depends(tenant_db),
) -> ChannelAuthorization:
    participant = owned_or_404(
        db.get(SupplyChainParticipant, body.participant_id),
        actor.manufacturer_id,
        name="Participant",
    )
    territory = owned_or_404(
        db.get(Territory, body.territory_id), actor.manufacturer_id, name="Territory"
    )
    authorization = grant_channel_authorization(
        db,
        manufacturer_id=actor.manufacturer_id,
        participant=participant,
        territory=territory,
        actor=actor,
        valid_from=body.valid_from,
        valid_until=body.valid_until,
    )
    db.commit()
    return authorization


@router.get(
    "/channel-authorizations", response_model=list[schemas.ChannelAuthorizationView]
)
def list_channel_authorizations(
    db: Session = Depends(tenant_db),
) -> list[ChannelAuthorization]:
    return list(
        db.execute(
            select(ChannelAuthorization).order_by(ChannelAuthorization.valid_from)
        )
        .scalars()
        .all()
    )


@router.post(
    "/channel-authorizations/{authorization_id}/revoke",
    response_model=schemas.ChannelAuthorizationView,
)
def revoke_authorization(
    authorization_id: uuid.UUID,
    actor: ActorContext = Depends(
        requires(Capability.MANAGE_SUPPLY_CHAIN_REFERENCE_DATA)
    ),
    db: Session = Depends(tenant_db),
) -> ChannelAuthorization:
    authorization = owned_or_404(
        db.get(ChannelAuthorization, authorization_id),
        actor.manufacturer_id,
        name="Channel authorization",
    )
    revoke_channel_authorization(db, authorization=authorization, actor=actor)
    db.commit()
    return authorization


_RECORDERS = {
    SupplyChainEventType.DISPATCH: record_dispatch,
    SupplyChainEventType.RECEIPT: record_receipt,
    SupplyChainEventType.TRANSFER: record_transfer,
    SupplyChainEventType.RETURN: record_return,
    SupplyChainEventType.REALLOCATION: record_reallocation,
    SupplyChainEventType.RETAIL_PLACEMENT: record_retail_placement,
    SupplyChainEventType.CUSTODY_ADJUSTMENT: record_custody_adjustment,
}


def _participant(db: Session, actor: ActorContext, participant_id: uuid.UUID | None):
    if participant_id is None:
        return None
    return owned_or_404(
        db.get(SupplyChainParticipant, participant_id),
        actor.manufacturer_id,
        name="Participant",
    )


@router.post(
    "/events", response_model=schemas.SupplyChainEventView, status_code=status.HTTP_201_CREATED
)
def record_event(
    body: schemas.SupplyChainEventCreate,
    actor: ActorContext = Depends(requires(Capability.RECORD_SUPPLY_CHAIN_EVENT)),
    db: Session = Depends(tenant_db),
) -> SupplyChainEvent:
    identity = owned_or_404(
        db.get(ProductIdentity, body.identity_id), actor.manufacturer_id, name="Identity"
    )
    arguments = {
        "identity": identity,
        "occurred_at": body.occurred_at,
        "actor": actor,
        "reason": body.reason,
    }

    source = _participant(db, actor, body.source_participant_id)
    destination = _participant(db, actor, body.destination_participant_id)

    if body.event_type is SupplyChainEventType.DISPATCH:
        arguments |= {"destination_participant": destination, "source_participant": source}
    elif body.event_type is SupplyChainEventType.RETAIL_PLACEMENT:
        arguments |= {"source_participant": source}
    elif body.event_type is SupplyChainEventType.CUSTODY_ADJUSTMENT:
        related_event = (
            owned_or_404(
                db.get(SupplyChainEvent, body.related_event_id),
                actor.manufacturer_id,
                name="Supply chain event",
            )
            if body.related_event_id
            else None
        )
        related_identity = (
            owned_or_404(
                db.get(ProductIdentity, body.related_identity_id),
                actor.manufacturer_id,
                name="Identity",
            )
            if body.related_identity_id
            else None
        )
        arguments |= {
            "reason": body.reason or "",
            "source_participant": source,
            "destination_participant": destination,
            "related_event": related_event,
            "related_identity": related_identity,
        }
    else:
        arguments |= {
            "source_participant": source,
            "destination_participant": destination,
        }

    event = _RECORDERS[body.event_type](db, **arguments)
    db.commit()
    return event


@router.get(
    "/identities/{identity_id}/events", response_model=list[schemas.SupplyChainEventView]
)
def list_identity_events(
    identity_id: uuid.UUID, db: Session = Depends(tenant_db)
) -> list[SupplyChainEvent]:
    return identity_event_history(db, identity_id=identity_id)


@router.get(
    "/identities/{identity_id}/custodian", response_model=schemas.CurrentCustodianView
)
def current_custodian(
    identity_id: uuid.UUID,
    actor: ActorContext = Depends(current_actor),
    db: Session = Depends(tenant_db),
) -> schemas.CurrentCustodianView:
    """Current custodian, re-derived from the event log on every request.

    There is no stored custodian column. The projection is computed here so
    that it cannot drift away from the events it is supposed to summarise.
    """
    owned_or_404(
        db.get(ProductIdentity, identity_id), actor.manufacturer_id, name="Identity"
    )
    return schemas.CurrentCustodianView(
        identity_id=identity_id,
        custodian_id=current_custodian_id(db, identity_id=identity_id),
    )
