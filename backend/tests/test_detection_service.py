from datetime import UTC, datetime, timedelta

import pytest

from app.core.authorization import ActorContext, Capability, CapabilityNotHeldError
from app.domains.detection import (
    DetectionEvidence,
    DetectionEvidenceSource,
    SignalType,
    identity_evidence,
    run_detection,
)
from app.domains.verification import ScanLocation, verify
from tests.identity_fixtures import FULLY_AUTHORIZED_TEST_ACTOR
from tests.verification_fixtures import BENGALURU, MUMBAI, activated_identity_fixture, scan_request


def _scan(db, identity, *, location: ScanLocation | None, at: datetime):
    return verify(db, scan_request(serial=identity.serial, location=location, occurred_at=at))


def test_detection_requires_the_run_detection_capability(postgres_db_session):
    fx = activated_identity_fixture(postgres_db_session)
    powerless = ActorContext(actor_id="no-capabilities")

    with pytest.raises(CapabilityNotHeldError):
        run_detection(postgres_db_session, identity=fx["identity"], actor=powerless)


def test_a_quiet_identity_produces_no_evidence(postgres_db_session):
    fx = activated_identity_fixture(postgres_db_session)
    _scan(postgres_db_session, fx["identity"], location=BENGALURU, at=datetime.now(UTC))

    evidence = run_detection(
        postgres_db_session, identity=fx["identity"], actor=FULLY_AUTHORIZED_TEST_ACTOR
    )
    assert evidence == []


def test_impossible_travel_is_persisted_with_its_source_events(postgres_db_session):
    fx = activated_identity_fixture(postgres_db_session)
    now = datetime.now(UTC)
    _scan(postgres_db_session, fx["identity"], location=BENGALURU, at=now - timedelta(hours=2))
    _scan(postgres_db_session, fx["identity"], location=MUMBAI, at=now - timedelta(hours=1))

    evidence = run_detection(
        postgres_db_session, identity=fx["identity"], actor=FULLY_AUTHORIZED_TEST_ACTOR
    )
    travel = [e for e in evidence if e.signal_type is SignalType.IMPOSSIBLE_TRAVEL]

    assert len(travel) == 1
    sources = (
        postgres_db_session.query(DetectionEvidenceSource)
        .filter_by(evidence_id=travel[0].id)
        .all()
    )
    assert len(sources) == 2
    assert all(source.verification_event_id is not None for source in sources)


def test_evidence_carries_the_detector_version_that_produced_it(postgres_db_session):
    fx = activated_identity_fixture(postgres_db_session)
    now = datetime.now(UTC)
    _scan(postgres_db_session, fx["identity"], location=BENGALURU, at=now - timedelta(hours=2))
    _scan(postgres_db_session, fx["identity"], location=MUMBAI, at=now - timedelta(hours=1))

    evidence = run_detection(
        postgres_db_session, identity=fx["identity"], actor=FULLY_AUTHORIZED_TEST_ACTOR
    )
    assert all(e.detector_version >= 1 for e in evidence)
    assert all(e.detector_id for e in evidence)


def test_rerunning_the_same_detector_version_is_idempotent(postgres_db_session):
    fx = activated_identity_fixture(postgres_db_session)
    now = datetime.now(UTC)
    _scan(postgres_db_session, fx["identity"], location=BENGALURU, at=now - timedelta(hours=2))
    _scan(postgres_db_session, fx["identity"], location=MUMBAI, at=now - timedelta(hours=1))

    first = run_detection(
        postgres_db_session, identity=fx["identity"], actor=FULLY_AUTHORIZED_TEST_ACTOR
    )
    second = run_detection(
        postgres_db_session, identity=fx["identity"], actor=FULLY_AUTHORIZED_TEST_ACTOR
    )

    assert first != []
    assert second == []
    assert len(identity_evidence(postgres_db_session, identity_id=fx["identity"].id)) == len(
        first
    )


def test_evidence_rows_form_an_unbroken_hash_chain(postgres_db_session):
    from app.core.event_chain import GENESIS_EVENT_HASH, verify_chain

    fx = activated_identity_fixture(postgres_db_session)
    now = datetime.now(UTC)
    _scan(postgres_db_session, fx["identity"], location=BENGALURU, at=now - timedelta(hours=2))
    _scan(postgres_db_session, fx["identity"], location=MUMBAI, at=now - timedelta(hours=1))
    run_detection(
        postgres_db_session, identity=fx["identity"], actor=FULLY_AUTHORIZED_TEST_ACTOR
    )

    rows = identity_evidence(postgres_db_session, identity_id=fx["identity"].id)
    links = [(row.previous_event_hash, row.event_hash) for row in rows]

    assert links[0][0] == GENESIS_EVENT_HASH
    assert verify_chain(links) is True


def test_evidence_without_any_source_is_rejected_at_the_database_level(postgres_db_session):
    from sqlalchemy.exc import DatabaseError

    from app.core.event_chain import GENESIS_EVENT_HASH
    from app.domains.detection.signals import FraudFamily

    fx = activated_identity_fixture(postgres_db_session)
    now = datetime.now(UTC)

    postgres_db_session.add(
        DetectionEvidence(
            manufacturer_id=fx["manufacturer"].id,
            identity_id=fx["identity"].id,
            sequence=1,
            detector_id="handwritten",
            detector_version=1,
            signal_type=SignalType.SCAN_VELOCITY,
            fraud_family=FraudFamily.CODE_CLONING,
            log_likelihood_ratio=1.0,
            explanation="inserted without citing anything",
            signal_fingerprint=b"\x00" * 32,
            window_start=now - timedelta(days=1),
            window_end=now,
            previous_event_hash=GENESIS_EVENT_HASH,
            event_hash=b"\x01" * 32,
        )
    )
    with pytest.raises(DatabaseError):
        postgres_db_session.commit()
    postgres_db_session.rollback()


def test_detection_uses_the_actor_capability_not_the_tenant_alone(postgres_db_session):
    fx = activated_identity_fixture(postgres_db_session)
    detection_only = ActorContext(
        actor_id="detection-runner",
        manufacturer_id=fx["manufacturer"].id,
        capabilities=frozenset({Capability.RUN_DETECTION}),
    )

    assert (
        run_detection(postgres_db_session, identity=fx["identity"], actor=detection_only) == []
    )
