from datetime import UTC, datetime

import pytest

from app.domains.supply_chain import (
    CrossManufacturerReferenceError,
    SupplyChainEventType,
    SupplyChainEventValidationError,
    record_custody_adjustment,
    record_dispatch,
    record_reallocation,
    record_receipt,
    record_retail_placement,
    record_return,
    record_transfer,
)
from tests.identity_fixtures import make_manufacturer
from tests.supply_chain_fixtures import full_supply_chain_fixture, make_participant


def _now():
    return datetime.now(UTC)


def test_record_dispatch_from_manufacturer_origin(supply_chain_db_session):
    fx = full_supply_chain_fixture(supply_chain_db_session)

    event = record_dispatch(
        supply_chain_db_session,
        identity=fx["identity"],
        occurred_at=_now(),
        destination_participant=fx["depot"],
    )
    supply_chain_db_session.commit()

    assert event.event_type == SupplyChainEventType.DISPATCH
    assert event.source_participant_id is None
    assert event.destination_participant_id == fx["depot"].id
    assert event.manufacturer_id == fx["manufacturer"].id


def test_record_dispatch_requires_destination(supply_chain_db_session):
    fx = full_supply_chain_fixture(supply_chain_db_session)

    with pytest.raises(SupplyChainEventValidationError):
        record_dispatch(
            supply_chain_db_session,
            identity=fx["identity"],
            occurred_at=_now(),
            destination_participant=None,
        )


def test_record_receipt_requires_both_participants(supply_chain_db_session):
    fx = full_supply_chain_fixture(supply_chain_db_session)

    with pytest.raises(SupplyChainEventValidationError):
        record_receipt(
            supply_chain_db_session,
            identity=fx["identity"],
            occurred_at=_now(),
            source_participant=fx["depot"],
            destination_participant=None,
        )


def test_record_receipt_succeeds(supply_chain_db_session):
    fx = full_supply_chain_fixture(supply_chain_db_session)

    event = record_receipt(
        supply_chain_db_session,
        identity=fx["identity"],
        occurred_at=_now(),
        source_participant=fx["depot"],
        destination_participant=fx["distributor"],
    )
    supply_chain_db_session.commit()

    assert event.event_type == SupplyChainEventType.RECEIPT
    assert event.source_participant_id == fx["depot"].id
    assert event.destination_participant_id == fx["distributor"].id


def test_record_transfer_succeeds(supply_chain_db_session):
    fx = full_supply_chain_fixture(supply_chain_db_session)

    event = record_transfer(
        supply_chain_db_session,
        identity=fx["identity"],
        occurred_at=_now(),
        source_participant=fx["distributor"],
        destination_participant=fx["retailer"],
    )
    supply_chain_db_session.commit()

    assert event.event_type == SupplyChainEventType.TRANSFER


def test_record_return_succeeds(supply_chain_db_session):
    fx = full_supply_chain_fixture(supply_chain_db_session)

    event = record_return(
        supply_chain_db_session,
        identity=fx["identity"],
        occurred_at=_now(),
        source_participant=fx["retailer"],
        destination_participant=fx["distributor"],
        reason="End-of-season unsold stock",
    )
    supply_chain_db_session.commit()

    assert event.event_type == SupplyChainEventType.RETURN
    assert event.reason == "End-of-season unsold stock"


def test_record_reallocation_succeeds(supply_chain_db_session):
    fx = full_supply_chain_fixture(supply_chain_db_session)
    other_distributor = make_participant(
        supply_chain_db_session,
        fx["manufacturer"].id,
        participant_ref="DIST-002",
        name="Second Distributor",
        role=fx["distributor"].role,
    )
    supply_chain_db_session.commit()

    event = record_reallocation(
        supply_chain_db_session,
        identity=fx["identity"],
        occurred_at=_now(),
        source_participant=fx["distributor"],
        destination_participant=other_distributor,
        reason="SEASONAL_REDISTRIBUTION",
    )
    supply_chain_db_session.commit()

    assert event.event_type == SupplyChainEventType.REALLOCATION
    assert event.reason == "SEASONAL_REDISTRIBUTION"


def test_record_retail_placement_succeeds(supply_chain_db_session):
    fx = full_supply_chain_fixture(supply_chain_db_session)

    event = record_retail_placement(
        supply_chain_db_session,
        identity=fx["identity"],
        occurred_at=_now(),
        source_participant=fx["retailer"],
    )
    supply_chain_db_session.commit()

    assert event.event_type == SupplyChainEventType.RETAIL_PLACEMENT
    assert event.destination_participant_id is None


def test_record_retail_placement_requires_source(supply_chain_db_session):
    fx = full_supply_chain_fixture(supply_chain_db_session)

    with pytest.raises(SupplyChainEventValidationError):
        record_retail_placement(
            supply_chain_db_session,
            identity=fx["identity"],
            occurred_at=_now(),
            source_participant=None,
        )


def test_record_custody_adjustment_requires_reason(supply_chain_db_session):
    fx = full_supply_chain_fixture(supply_chain_db_session)

    with pytest.raises(SupplyChainEventValidationError):
        record_custody_adjustment(
            supply_chain_db_session,
            identity=fx["identity"],
            occurred_at=_now(),
            reason="",
            source_participant=fx["depot"],
        )


def test_record_custody_adjustment_requires_contextual_reference(supply_chain_db_session):
    fx = full_supply_chain_fixture(supply_chain_db_session)

    with pytest.raises(SupplyChainEventValidationError):
        record_custody_adjustment(
            supply_chain_db_session,
            identity=fx["identity"],
            occurred_at=_now(),
            reason="Damaged in transit",
        )


def test_record_custody_adjustment_referencing_participant_succeeds(supply_chain_db_session):
    fx = full_supply_chain_fixture(supply_chain_db_session)

    event = record_custody_adjustment(
        supply_chain_db_session,
        identity=fx["identity"],
        occurred_at=_now(),
        reason="Count correction after physical audit",
        source_participant=fx["depot"],
    )
    supply_chain_db_session.commit()

    assert event.event_type == SupplyChainEventType.CUSTODY_ADJUSTMENT
    assert event.reason == "Count correction after physical audit"


def test_record_custody_adjustment_referencing_prior_event_succeeds(supply_chain_db_session):
    fx = full_supply_chain_fixture(supply_chain_db_session)
    original = record_dispatch(
        supply_chain_db_session,
        identity=fx["identity"],
        occurred_at=_now(),
        destination_participant=fx["depot"],
    )
    supply_chain_db_session.commit()

    correction = record_custody_adjustment(
        supply_chain_db_session,
        identity=fx["identity"],
        occurred_at=_now(),
        reason="Corrects dispatch quantity recorded in error",
        related_event=original,
    )
    supply_chain_db_session.commit()

    assert correction.related_event_id == original.id


def test_participant_from_different_manufacturer_is_rejected(supply_chain_db_session):
    fx = full_supply_chain_fixture(supply_chain_db_session)
    other_manufacturer = make_manufacturer(supply_chain_db_session, name="Other Mfr")
    supply_chain_db_session.commit()
    foreign_participant = make_participant(supply_chain_db_session, other_manufacturer.id)
    supply_chain_db_session.commit()

    with pytest.raises(CrossManufacturerReferenceError):
        record_dispatch(
            supply_chain_db_session,
            identity=fx["identity"],
            occurred_at=_now(),
            destination_participant=foreign_participant,
        )
