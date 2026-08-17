from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.domains.identity import ProductIdentity
from app.domains.supply_chain import (
    ChannelAuthorization,
    ParticipantRole,
    SupplyChainParticipant,
    Territory,
    define_territory,
    grant_channel_authorization,
    register_participant,
)
from tests.identity_fixtures import full_signed_fixture

VALID_SQUARE_WKT = "MULTIPOLYGON(((0 0, 0 1, 1 1, 1 0, 0 0)))"
INVALID_BOWTIE_WKT = "MULTIPOLYGON(((0 0, 1 1, 1 0, 0 1, 0 0)))"


def make_participant(
    db: Session,
    manufacturer_id,
    *,
    participant_ref: str = "PART-001",
    name: str = "Synthetic Depot",
    role: ParticipantRole = ParticipantRole.DEPOT,
) -> SupplyChainParticipant:
    return register_participant(
        db,
        manufacturer_id=manufacturer_id,
        participant_ref=participant_ref,
        name=name,
        role=role,
    )


def make_territory(
    db: Session,
    manufacturer_id,
    *,
    territory_ref: str = "TERR-001",
    name: str = "Synthetic Territory",
    boundary_wkt: str = VALID_SQUARE_WKT,
) -> Territory:
    return define_territory(
        db,
        manufacturer_id=manufacturer_id,
        territory_ref=territory_ref,
        name=name,
        boundary_wkt=boundary_wkt,
    )


def make_authorization(
    db: Session,
    manufacturer_id,
    participant: SupplyChainParticipant,
    territory: Territory,
    *,
    valid_from: datetime | None = None,
    valid_until: datetime | None = None,
) -> ChannelAuthorization:
    return grant_channel_authorization(
        db,
        manufacturer_id=manufacturer_id,
        participant=participant,
        territory=territory,
        valid_from=valid_from,
        valid_until=valid_until,
    )


def full_supply_chain_fixture(db: Session) -> dict:
    identity_fx = full_signed_fixture(db)
    manufacturer = identity_fx["manufacturer"]

    depot = make_participant(
        db,
        manufacturer.id,
        participant_ref="DEPOT-001",
        name="Synthetic Depot",
        role=ParticipantRole.DEPOT,
    )
    distributor = make_participant(
        db,
        manufacturer.id,
        participant_ref="DIST-001",
        name="Synthetic Distributor",
        role=ParticipantRole.DISTRIBUTOR,
    )
    retailer = make_participant(
        db,
        manufacturer.id,
        participant_ref="RET-001",
        name="Synthetic Retailer",
        role=ParticipantRole.RETAILER,
    )
    territory = make_territory(db, manufacturer.id)
    db.commit()

    return {
        **identity_fx,
        "depot": depot,
        "distributor": distributor,
        "retailer": retailer,
        "territory": territory,
    }


def utc_now() -> datetime:
    return datetime.now(UTC)


def identity_of(fx: dict) -> ProductIdentity:
    return fx["identity"]
