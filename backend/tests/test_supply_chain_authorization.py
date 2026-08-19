from datetime import UTC, datetime, timedelta

import pytest

from app.domains.supply_chain import (
    CrossManufacturerReferenceError,
    InvalidAuthorizationValidityError,
    grant_channel_authorization,
    is_authorization_active_at,
    revoke_channel_authorization,
)
from tests.identity_fixtures import FULLY_AUTHORIZED_TEST_ACTOR, make_manufacturer
from tests.supply_chain_fixtures import make_authorization, make_participant, make_territory
from tests.tenancy_helpers import scope_to


def _now():
    return datetime.now(UTC)


def test_grant_channel_authorization_open_ended(supply_chain_db_session):
    manufacturer = make_manufacturer(supply_chain_db_session, name="Auth Test Mfr")
    supply_chain_db_session.commit()
    participant = make_participant(supply_chain_db_session, manufacturer.id)
    territory = make_territory(supply_chain_db_session, manufacturer.id)
    supply_chain_db_session.commit()

    authorization = make_authorization(
        supply_chain_db_session, manufacturer.id, participant, territory
    )
    supply_chain_db_session.commit()

    assert authorization.valid_until is None
    assert is_authorization_active_at(authorization, _now())


def test_authorization_with_future_validity_is_not_yet_active(supply_chain_db_session):
    manufacturer = make_manufacturer(supply_chain_db_session, name="Future Auth Mfr")
    supply_chain_db_session.commit()
    participant = make_participant(supply_chain_db_session, manufacturer.id)
    territory = make_territory(supply_chain_db_session, manufacturer.id)
    supply_chain_db_session.commit()

    future_start = _now() + timedelta(days=30)
    authorization = make_authorization(
        supply_chain_db_session, manufacturer.id, participant, territory, valid_from=future_start
    )
    supply_chain_db_session.commit()

    assert is_authorization_active_at(authorization, _now()) is False
    assert is_authorization_active_at(authorization, future_start + timedelta(days=1)) is True


def test_expired_authorization_is_not_active(supply_chain_db_session):
    manufacturer = make_manufacturer(supply_chain_db_session, name="Expired Auth Mfr")
    supply_chain_db_session.commit()
    participant = make_participant(supply_chain_db_session, manufacturer.id)
    territory = make_territory(supply_chain_db_session, manufacturer.id)
    supply_chain_db_session.commit()

    past_start = _now() - timedelta(days=60)
    past_end = _now() - timedelta(days=30)
    authorization = make_authorization(
        supply_chain_db_session,
        manufacturer.id,
        participant,
        territory,
        valid_from=past_start,
        valid_until=past_end,
    )
    supply_chain_db_session.commit()

    assert is_authorization_active_at(authorization, _now()) is False
    assert is_authorization_active_at(authorization, past_start + timedelta(days=1)) is True


def test_invalid_validity_range_is_rejected(supply_chain_db_session):
    manufacturer = make_manufacturer(supply_chain_db_session, name="Invalid Range Mfr")
    supply_chain_db_session.commit()
    participant = make_participant(supply_chain_db_session, manufacturer.id)
    territory = make_territory(supply_chain_db_session, manufacturer.id)
    supply_chain_db_session.commit()

    start = _now()
    with pytest.raises(InvalidAuthorizationValidityError):
        make_authorization(
            supply_chain_db_session,
            manufacturer.id,
            participant,
            territory,
            valid_from=start,
            valid_until=start - timedelta(days=1),
        )


def test_cross_manufacturer_participant_authorization_is_rejected(supply_chain_db_session):
    manufacturer_a = make_manufacturer(supply_chain_db_session, name="Cross Auth Mfr A")
    manufacturer_b = make_manufacturer(supply_chain_db_session, name="Cross Auth Mfr B")
    supply_chain_db_session.commit()

    participant_b = make_participant(supply_chain_db_session, manufacturer_b.id)
    scope_to(supply_chain_db_session, manufacturer_a.id)
    territory_a = make_territory(supply_chain_db_session, manufacturer_a.id)
    supply_chain_db_session.commit()

    with pytest.raises(CrossManufacturerReferenceError):
        grant_channel_authorization(
            supply_chain_db_session,
            manufacturer_id=manufacturer_a.id,
            participant=participant_b,
            territory=territory_a,
            actor=FULLY_AUTHORIZED_TEST_ACTOR,
        )


def test_cross_manufacturer_territory_authorization_is_rejected(supply_chain_db_session):
    manufacturer_a = make_manufacturer(supply_chain_db_session, name="Cross Auth Terr Mfr A")
    manufacturer_b = make_manufacturer(supply_chain_db_session, name="Cross Auth Terr Mfr B")
    supply_chain_db_session.commit()

    territory_b = make_territory(supply_chain_db_session, manufacturer_b.id)
    scope_to(supply_chain_db_session, manufacturer_a.id)
    participant_a = make_participant(supply_chain_db_session, manufacturer_a.id)
    supply_chain_db_session.commit()

    with pytest.raises(CrossManufacturerReferenceError):
        grant_channel_authorization(
            supply_chain_db_session,
            manufacturer_id=manufacturer_a.id,
            participant=participant_a,
            territory=territory_b,
            actor=FULLY_AUTHORIZED_TEST_ACTOR,
        )


def test_overlapping_authorizations_are_allowed(supply_chain_db_session):
    manufacturer = make_manufacturer(supply_chain_db_session, name="Overlap Mfr")
    supply_chain_db_session.commit()
    participant = make_participant(supply_chain_db_session, manufacturer.id)
    territory = make_territory(supply_chain_db_session, manufacturer.id)
    supply_chain_db_session.commit()

    make_authorization(supply_chain_db_session, manufacturer.id, participant, territory)
    make_authorization(supply_chain_db_session, manufacturer.id, participant, territory)
    supply_chain_db_session.commit()


def test_revoke_channel_authorization_sets_valid_until(supply_chain_db_session):
    manufacturer = make_manufacturer(supply_chain_db_session, name="Revoke Auth Mfr")
    supply_chain_db_session.commit()
    participant = make_participant(supply_chain_db_session, manufacturer.id)
    territory = make_territory(supply_chain_db_session, manufacturer.id)
    supply_chain_db_session.commit()

    authorization = make_authorization(
        supply_chain_db_session, manufacturer.id, participant, territory
    )
    supply_chain_db_session.commit()

    revoke_channel_authorization(
        supply_chain_db_session,
        authorization=authorization,
        actor=FULLY_AUTHORIZED_TEST_ACTOR,
    )
    supply_chain_db_session.commit()

    assert authorization.valid_until is not None
    assert is_authorization_active_at(authorization, _now()) is False
