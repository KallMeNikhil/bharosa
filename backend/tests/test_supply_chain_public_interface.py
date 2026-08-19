from datetime import UTC, datetime

import app.domains.supply_chain as supply_chain
from tests.identity_fixtures import FULLY_AUTHORIZED_TEST_ACTOR, make_manufacturer
from tests.supply_chain_fixtures import VALID_SQUARE_WKT


def test_public_interface_exports_everything_this_test_needs():
    for name in [
        "SupplyChainParticipant",
        "ParticipantRole",
        "Territory",
        "ChannelAuthorization",
        "SupplyChainEvent",
        "SupplyChainEventType",
        "register_participant",
        "define_territory",
        "territory_contains_point",
        "grant_channel_authorization",
        "revoke_channel_authorization",
        "is_authorization_active_at",
        "record_dispatch",
        "record_receipt",
        "record_transfer",
        "record_return",
        "record_reallocation",
        "record_retail_placement",
        "record_custody_adjustment",
        "CrossManufacturerReferenceError",
        "InvalidTerritoryGeometryError",
        "InvalidAuthorizationValidityError",
        "SupplyChainEventValidationError",
    ]:
        assert hasattr(supply_chain, name), f"public interface missing {name!r}"


def test_full_workflow_using_only_the_public_interface(supply_chain_db_session):
    manufacturer = make_manufacturer(supply_chain_db_session, name="Public Interface Mfr")
    supply_chain_db_session.commit()

    depot = supply_chain.register_participant(
        supply_chain_db_session,
        manufacturer_id=manufacturer.id,
        participant_ref="PI-DEPOT",
        name="Public Interface Depot",
        role=supply_chain.ParticipantRole.DEPOT,
        actor=FULLY_AUTHORIZED_TEST_ACTOR,
    )
    distributor = supply_chain.register_participant(
        supply_chain_db_session,
        manufacturer_id=manufacturer.id,
        participant_ref="PI-DIST",
        name="Public Interface Distributor",
        role=supply_chain.ParticipantRole.DISTRIBUTOR,
        actor=FULLY_AUTHORIZED_TEST_ACTOR,
    )
    territory = supply_chain.define_territory(
        supply_chain_db_session,
        manufacturer_id=manufacturer.id,
        territory_ref="PI-TERR",
        name="Public Interface Territory",
        boundary_wkt=VALID_SQUARE_WKT,
        actor=FULLY_AUTHORIZED_TEST_ACTOR,
    )
    authorization = supply_chain.grant_channel_authorization(
        supply_chain_db_session,
        manufacturer_id=manufacturer.id,
        participant=distributor,
        territory=territory,
        actor=FULLY_AUTHORIZED_TEST_ACTOR,
    )
    supply_chain_db_session.commit()

    assert supply_chain.is_authorization_active_at(authorization, datetime.now(UTC))
    assert depot.role == supply_chain.ParticipantRole.DEPOT
