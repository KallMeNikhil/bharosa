from datetime import UTC, datetime

import pytest

from app.domains.identity import LifecycleState
from app.domains.identity.signer import DevelopmentOnlySigner
from app.domains.supply_chain import (
    CrossManufacturerReferenceError,
    SupplyChainEventType,
    SupplyChainEventValidationError,
    record_custody_adjustment,
)
from tests.identity_fixtures import (
    FULLY_AUTHORIZED_TEST_ACTOR,
    make_batch,
    make_key,
    make_manufacturer,
    make_product,
    make_reserved_identity,
)
from tests.supply_chain_fixtures import full_supply_chain_fixture
from tests.tenancy_helpers import scope_to


def _now():
    return datetime.now(UTC)


def test_replacement_identity_remains_a_distinct_product_identity(supply_chain_db_session):
    fx = full_supply_chain_fixture(supply_chain_db_session)
    original_identity = fx["identity"]

    replacement_identity = make_reserved_identity(
        supply_chain_db_session, fx["batch"]
    )
    supply_chain_db_session.commit()

    assert replacement_identity.id != original_identity.id
    assert replacement_identity.lifecycle_state == LifecycleState.RESERVED

    adjustment = record_custody_adjustment(
        supply_chain_db_session,
        identity=original_identity,
        occurred_at=_now(),
        reason="Damaged in transit; replaced by a new physical identity",
        related_identity=replacement_identity,
        actor=FULLY_AUTHORIZED_TEST_ACTOR,
    )
    supply_chain_db_session.commit()

    assert adjustment.event_type == SupplyChainEventType.CUSTODY_ADJUSTMENT
    assert adjustment.identity_id == original_identity.id
    assert adjustment.related_identity_id == replacement_identity.id
    assert adjustment.related_identity_id != adjustment.identity_id


def test_replacement_identity_cannot_reference_itself(supply_chain_db_session):
    fx = full_supply_chain_fixture(supply_chain_db_session)

    with pytest.raises(SupplyChainEventValidationError):
        record_custody_adjustment(
            supply_chain_db_session,
            identity=fx["identity"],
            occurred_at=_now(),
            reason="Invalid self-reference attempt",
            related_identity=fx["identity"],
            actor=FULLY_AUTHORIZED_TEST_ACTOR,
        )


def test_replacement_identity_from_different_manufacturer_is_rejected(supply_chain_db_session):
    fx = full_supply_chain_fixture(supply_chain_db_session)
    other_manufacturer = make_manufacturer(supply_chain_db_session, name="Other Replacement Mfr")
    supply_chain_db_session.commit()

    signer = DevelopmentOnlySigner()
    other_key = make_key(supply_chain_db_session, other_manufacturer, signer)
    other_product = make_product(supply_chain_db_session, other_manufacturer)
    other_batch = make_batch(supply_chain_db_session, other_product)
    foreign_identity = make_reserved_identity(supply_chain_db_session, other_batch)
    supply_chain_db_session.commit()
    scope_to(supply_chain_db_session, fx["manufacturer"].id)
    assert other_key is not None

    with pytest.raises(CrossManufacturerReferenceError):
        record_custody_adjustment(
            supply_chain_db_session,
            identity=fx["identity"],
            occurred_at=_now(),
            reason="Cross-manufacturer replacement attempt",
            related_identity=foreign_identity,
            actor=FULLY_AUTHORIZED_TEST_ACTOR,
        )
