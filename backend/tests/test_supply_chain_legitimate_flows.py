from datetime import UTC, datetime, timedelta

from app.domains.supply_chain import (
    SupplyChainEventType,
    record_custody_adjustment,
    record_dispatch,
    record_reallocation,
    record_receipt,
    record_retail_placement,
    record_return,
    record_transfer,
)
from tests.identity_fixtures import FULLY_AUTHORIZED_TEST_ACTOR
from tests.supply_chain_fixtures import full_supply_chain_fixture, make_participant


def _t(offset_days: int) -> datetime:
    return datetime.now(UTC) + timedelta(days=offset_days)


def test_manufacturer_to_distributor_to_retailer_forward_flow(supply_chain_db_session):
    fx = full_supply_chain_fixture(supply_chain_db_session)
    identity = fx["identity"]

    dispatch = record_dispatch(
        supply_chain_db_session,
        identity=identity,
        occurred_at=_t(0),
        destination_participant=fx["depot"],
        actor=FULLY_AUTHORIZED_TEST_ACTOR,
    )
    receipt = record_receipt(
        supply_chain_db_session,
        identity=identity,
        occurred_at=_t(1),
        source_participant=fx["depot"],
        destination_participant=fx["distributor"],
        actor=FULLY_AUTHORIZED_TEST_ACTOR,
    )
    transfer = record_transfer(
        supply_chain_db_session,
        identity=identity,
        occurred_at=_t(2),
        source_participant=fx["distributor"],
        destination_participant=fx["retailer"],
        actor=FULLY_AUTHORIZED_TEST_ACTOR,
    )
    placement = record_retail_placement(
        supply_chain_db_session,
        identity=identity,
        occurred_at=_t(3),
        source_participant=fx["retailer"],
        actor=FULLY_AUTHORIZED_TEST_ACTOR,
    )
    supply_chain_db_session.commit()

    event_types = [
        dispatch.event_type,
        receipt.event_type,
        transfer.event_type,
        placement.event_type,
    ]
    assert event_types == [
        SupplyChainEventType.DISPATCH,
        SupplyChainEventType.RECEIPT,
        SupplyChainEventType.TRANSFER,
        SupplyChainEventType.RETAIL_PLACEMENT,
    ]


def test_forward_flow_then_legitimate_return_backward(supply_chain_db_session):
    fx = full_supply_chain_fixture(supply_chain_db_session)
    identity = fx["identity"]

    record_dispatch(
        supply_chain_db_session,
        identity=identity,
        occurred_at=_t(0),
        destination_participant=fx["depot"],
        actor=FULLY_AUTHORIZED_TEST_ACTOR,
    )
    record_receipt(
        supply_chain_db_session,
        identity=identity,
        occurred_at=_t(1),
        source_participant=fx["depot"],
        destination_participant=fx["distributor"],
        actor=FULLY_AUTHORIZED_TEST_ACTOR,
    )
    record_transfer(
        supply_chain_db_session,
        identity=identity,
        occurred_at=_t(2),
        source_participant=fx["distributor"],
        destination_participant=fx["retailer"],
        actor=FULLY_AUTHORIZED_TEST_ACTOR,
    )
    return_event = record_return(
        supply_chain_db_session,
        identity=identity,
        occurred_at=_t(90),
        source_participant=fx["retailer"],
        destination_participant=fx["distributor"],
        reason="End-of-season unsold stock returned",
        actor=FULLY_AUTHORIZED_TEST_ACTOR,
    )
    supply_chain_db_session.commit()

    assert return_event.event_type == SupplyChainEventType.RETURN
    assert return_event.source_participant_id == fx["retailer"].id
    assert return_event.destination_participant_id == fx["distributor"].id


def test_lateral_reallocation_between_two_distributors(supply_chain_db_session):
    fx = full_supply_chain_fixture(supply_chain_db_session)
    identity = fx["identity"]
    distributor_b = make_participant(
        supply_chain_db_session,
        fx["manufacturer"].id,
        participant_ref="DIST-B",
        name="Distributor B",
        role=fx["distributor"].role,
    )
    supply_chain_db_session.commit()

    reallocation = record_reallocation(
        supply_chain_db_session,
        identity=identity,
        occurred_at=_t(5),
        source_participant=fx["distributor"],
        destination_participant=distributor_b,
        reason="EMERGENCY_REDISTRIBUTION",
        actor=FULLY_AUTHORIZED_TEST_ACTOR,
    )
    supply_chain_db_session.commit()

    assert reallocation.event_type == SupplyChainEventType.REALLOCATION
    assert reallocation.source_participant_id == fx["distributor"].id
    assert reallocation.destination_participant_id == distributor_b.id


def test_lateral_reallocation_between_two_retailers(supply_chain_db_session):
    fx = full_supply_chain_fixture(supply_chain_db_session)
    identity = fx["identity"]
    retailer_b = make_participant(
        supply_chain_db_session,
        fx["manufacturer"].id,
        participant_ref="RET-B",
        name="Retailer B",
        role=fx["retailer"].role,
    )
    supply_chain_db_session.commit()

    reallocation = record_reallocation(
        supply_chain_db_session,
        identity=identity,
        occurred_at=_t(6),
        source_participant=fx["retailer"],
        destination_participant=retailer_b,
        reason="Authorized lateral stock-share between retailers",
        actor=FULLY_AUTHORIZED_TEST_ACTOR,
    )
    supply_chain_db_session.commit()

    assert reallocation.event_type == SupplyChainEventType.REALLOCATION


def test_damage_correction_through_compensating_event(supply_chain_db_session):
    fx = full_supply_chain_fixture(supply_chain_db_session)
    identity = fx["identity"]

    transfer = record_transfer(
        supply_chain_db_session,
        identity=identity,
        occurred_at=_t(2),
        source_participant=fx["distributor"],
        destination_participant=fx["retailer"],
        actor=FULLY_AUTHORIZED_TEST_ACTOR,
    )
    supply_chain_db_session.commit()

    correction = record_custody_adjustment(
        supply_chain_db_session,
        identity=identity,
        occurred_at=_t(3),
        reason="Quantity recorded on original transfer was incorrect; corrected here",
        related_event=transfer,
        actor=FULLY_AUTHORIZED_TEST_ACTOR,
    )
    supply_chain_db_session.commit()

    assert correction.event_type == SupplyChainEventType.CUSTODY_ADJUSTMENT
    assert correction.related_event_id == transfer.id
    assert transfer.event_type == SupplyChainEventType.TRANSFER


def test_multiple_legitimate_movements_for_same_identity_accumulate_as_history(
    supply_chain_db_session,
):
    fx = full_supply_chain_fixture(supply_chain_db_session)
    identity = fx["identity"]

    record_dispatch(
        supply_chain_db_session,
        identity=identity,
        occurred_at=_t(0),
        destination_participant=fx["depot"],
        actor=FULLY_AUTHORIZED_TEST_ACTOR,
    )
    record_receipt(
        supply_chain_db_session,
        identity=identity,
        occurred_at=_t(1),
        source_participant=fx["depot"],
        destination_participant=fx["distributor"],
        actor=FULLY_AUTHORIZED_TEST_ACTOR,
    )
    record_transfer(
        supply_chain_db_session,
        identity=identity,
        occurred_at=_t(2),
        source_participant=fx["distributor"],
        destination_participant=fx["retailer"],
        actor=FULLY_AUTHORIZED_TEST_ACTOR,
    )
    record_return(
        supply_chain_db_session,
        identity=identity,
        occurred_at=_t(10),
        source_participant=fx["retailer"],
        destination_participant=fx["distributor"],
        reason="Unsold stock return",
        actor=FULLY_AUTHORIZED_TEST_ACTOR,
    )
    record_transfer(
        supply_chain_db_session,
        identity=identity,
        occurred_at=_t(20),
        source_participant=fx["distributor"],
        destination_participant=fx["retailer"],
        reason="Redistributed after return",
        actor=FULLY_AUTHORIZED_TEST_ACTOR,
    )
    record_retail_placement(
        supply_chain_db_session,
        identity=identity,
        occurred_at=_t(21),
        source_participant=fx["retailer"],
        actor=FULLY_AUTHORIZED_TEST_ACTOR,
    )
    supply_chain_db_session.commit()


def test_unusual_but_legitimate_sequence_is_representable_without_error(supply_chain_db_session):
    fx = full_supply_chain_fixture(supply_chain_db_session)
    identity = fx["identity"]

    record_dispatch(
        supply_chain_db_session,
        identity=identity,
        occurred_at=_t(0),
        destination_participant=fx["depot"],
        actor=FULLY_AUTHORIZED_TEST_ACTOR,
    )
    record_receipt(
        supply_chain_db_session,
        identity=identity,
        occurred_at=_t(1),
        source_participant=fx["depot"],
        destination_participant=fx["distributor"],
        actor=FULLY_AUTHORIZED_TEST_ACTOR,
    )
    record_transfer(
        supply_chain_db_session,
        identity=identity,
        occurred_at=_t(2),
        source_participant=fx["distributor"],
        destination_participant=fx["retailer"],
        actor=FULLY_AUTHORIZED_TEST_ACTOR,
    )
    record_retail_placement(
        supply_chain_db_session,
        identity=identity,
        occurred_at=_t(3),
        source_participant=fx["retailer"],
        actor=FULLY_AUTHORIZED_TEST_ACTOR,
    )
    repeat_placement = record_retail_placement(
        supply_chain_db_session,
        identity=identity,
        occurred_at=_t(4),
        source_participant=fx["retailer"],
        reason="Repeat retailer stock-taking scan; legitimate re-check",
        actor=FULLY_AUTHORIZED_TEST_ACTOR,
    )
    supply_chain_db_session.commit()

    assert repeat_placement.event_type == SupplyChainEventType.RETAIL_PLACEMENT
    assert repeat_placement.reason is not None
