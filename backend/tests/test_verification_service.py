from datetime import UTC, datetime, timedelta

from app.domains.identity import (
    LifecycleState,
    generate_serial,
    mark_manufacturer_key_compromised,
    revoke_manufacturer_key,
)
from app.domains.verification import (
    UnresolvedScanTally,
    VerificationState,
    build_digital_link,
    identity_verification_history,
    verify,
)
from tests.identity_fixtures import FULLY_AUTHORIZED_TEST_ACTOR, full_signed_fixture
from tests.verification_fixtures import (
    BENGALURU,
    activated_identity_fixture,
    scan_request,
)


class _OpenIncidentSignals:
    def has_open_incident(self, db, identity_id):
        return True

    def has_elevated_risk(self, db, identity_id):
        return False


class _ElevatedRiskSignals:
    def has_open_incident(self, db, identity_id):
        return False

    def has_elevated_risk(self, db, identity_id):
        return True


def test_activated_identity_verifies_as_genuine(postgres_db_session):
    fx = activated_identity_fixture(postgres_db_session)

    result = verify(postgres_db_session, scan_request(serial=fx["identity"].serial))

    assert result.state is VerificationState.GENUINE
    assert result.event_id is not None


def test_unknown_serial_is_invalid_and_records_no_event(postgres_db_session):
    activated_identity_fixture(postgres_db_session)

    result = verify(postgres_db_session, scan_request(serial=generate_serial()))

    assert result.state is VerificationState.INVALID
    assert result.event_id is None


def test_malformed_serial_is_invalid(postgres_db_session):
    activated_identity_fixture(postgres_db_session)

    result = verify(postgres_db_session, scan_request(serial="not-a-real-serial"))

    assert result.state is VerificationState.INVALID


def test_identity_not_yet_activated_is_invalid(postgres_db_session):
    fx = full_signed_fixture(postgres_db_session)
    assert fx["identity"].lifecycle_state is LifecycleState.SIGNED

    result = verify(postgres_db_session, scan_request(serial=fx["identity"].serial))

    assert result.state is VerificationState.INVALID


def test_tampered_signature_is_invalid(postgres_db_session):
    fx = activated_identity_fixture(postgres_db_session)
    tampered = bytearray(fx["identity"].signature)
    tampered[0] ^= 0xFF
    fx["identity"].signature = bytes(tampered)
    postgres_db_session.flush()

    result = verify(postgres_db_session, scan_request(serial=fx["identity"].serial))

    assert result.state is VerificationState.INVALID


def test_revoked_key_is_invalid(postgres_db_session):
    fx = activated_identity_fixture(postgres_db_session)
    revoke_manufacturer_key(
        postgres_db_session,
        key=fx["issued_key"].manufacturer_key,
        actor=FULLY_AUTHORIZED_TEST_ACTOR,
    )

    result = verify(postgres_db_session, scan_request(serial=fx["identity"].serial))

    assert result.state is VerificationState.INVALID


def test_compromised_key_is_caution_never_invalid_or_genuine(postgres_db_session):
    fx = activated_identity_fixture(postgres_db_session)
    mark_manufacturer_key_compromised(
        postgres_db_session,
        key=fx["issued_key"].manufacturer_key,
        actor=FULLY_AUTHORIZED_TEST_ACTOR,
    )

    result = verify(postgres_db_session, scan_request(serial=fx["identity"].serial))

    assert result.state is VerificationState.CAUTION


def test_open_incident_reports_already_reported(postgres_db_session):
    fx = activated_identity_fixture(postgres_db_session)

    result = verify(
        postgres_db_session,
        scan_request(serial=fx["identity"].serial),
        risk_signals=_OpenIncidentSignals(),
    )

    assert result.state is VerificationState.ALREADY_REPORTED


def test_elevated_risk_reports_caution(postgres_db_session):
    fx = activated_identity_fixture(postgres_db_session)

    result = verify(
        postgres_db_session,
        scan_request(serial=fx["identity"].serial),
        risk_signals=_ElevatedRiskSignals(),
    )

    assert result.state is VerificationState.CAUTION


def test_digital_link_uri_resolves_the_same_identity_as_a_bare_serial(postgres_db_session):
    fx = activated_identity_fixture(postgres_db_session)
    uri = build_digital_link(
        host="id.bharosa.example",
        gtin=fx["product"].gtin,
        bharosa_serial=fx["identity"].serial,
        lot=fx["batch"].batch_ref,
    )

    result = verify(postgres_db_session, scan_request(digital_link=uri))

    assert result.state is VerificationState.GENUINE


def test_repeated_scans_are_normal_and_all_remain_genuine(postgres_db_session):
    fx = activated_identity_fixture(postgres_db_session)

    for _ in range(4):
        result = verify(postgres_db_session, scan_request(serial=fx["identity"].serial))
        assert result.state is VerificationState.GENUINE

    history = identity_verification_history(
        postgres_db_session, identity_id=fx["identity"].id
    )
    assert [event.sequence for event in history] == [1, 2, 3, 4]


def test_verification_events_form_an_unbroken_hash_chain(postgres_db_session):
    from app.core.event_chain import GENESIS_EVENT_HASH, verify_chain

    fx = activated_identity_fixture(postgres_db_session)
    for _ in range(3):
        verify(postgres_db_session, scan_request(serial=fx["identity"].serial))

    history = identity_verification_history(
        postgres_db_session, identity_id=fx["identity"].id
    )
    links = [(event.previous_event_hash, event.event_hash) for event in history]

    assert links[0][0] == GENESIS_EVENT_HASH
    assert verify_chain(links) is True


def test_precise_location_is_stored_alongside_its_coarse_cell(postgres_db_session):
    fx = activated_identity_fixture(postgres_db_session)

    verify(
        postgres_db_session,
        scan_request(serial=fx["identity"].serial, location=BENGALURU),
    )

    event = identity_verification_history(
        postgres_db_session, identity_id=fx["identity"].id
    )[-1]
    assert event.coarse_cell == BENGALURU.coarse_cell
    assert event.location is not None


def test_scan_without_location_stores_neither_point_nor_cell(postgres_db_session):
    fx = activated_identity_fixture(postgres_db_session)

    verify(postgres_db_session, scan_request(serial=fx["identity"].serial))

    event = identity_verification_history(
        postgres_db_session, identity_id=fx["identity"].id
    )[-1]
    assert event.location is None
    assert event.coarse_cell is None


def test_unresolved_scans_are_tallied_by_day_and_cell_not_stored_per_attempt(
    postgres_db_session,
):
    when = datetime.now(UTC)
    for _ in range(5):
        verify(
            postgres_db_session,
            scan_request(serial=generate_serial(), location=BENGALURU, occurred_at=when),
        )
    postgres_db_session.flush()

    tally = (
        postgres_db_session.query(UnresolvedScanTally)
        .filter_by(scan_date=when.date(), coarse_cell=BENGALURU.coarse_cell)
        .one()
    )
    assert tally.scan_count == 5


def test_event_records_the_lifecycle_and_key_state_observed_at_scan_time(
    postgres_db_session,
):
    fx = activated_identity_fixture(postgres_db_session)

    verify(
        postgres_db_session,
        scan_request(
            serial=fx["identity"].serial, occurred_at=datetime.now(UTC) - timedelta(hours=2)
        ),
    )

    event = identity_verification_history(
        postgres_db_session, identity_id=fx["identity"].id
    )[-1]
    assert event.lifecycle_state_at_scan == LifecycleState.ACTIVATED.value
    assert event.key_status_at_scan == "ACTIVE"
    assert event.signature_valid is True
