from datetime import UTC, datetime, timedelta

import pytest

from app.core.authorization import ActorContext, CapabilityNotHeldError
from app.domains.detection import identity_evidence, run_detection
from app.domains.investigation import (
    IllegalIncidentTransitionError,
    IncidentStatus,
    UncitedIncidentError,
    cited_evidence,
    has_open_incident,
    open_incident,
    transition_incident,
)
from app.domains.risk import (
    ConfidenceLevel,
    NoEvidenceToAssessError,
    assess_identity,
    assessment_history,
    has_elevated_risk,
    latest_assessment,
)
from app.domains.verification import verify
from tests.identity_fixtures import FULLY_AUTHORIZED_TEST_ACTOR
from tests.verification_fixtures import BENGALURU, MUMBAI, activated_identity_fixture, scan_request


def _flagged_identity(db):
    fx = activated_identity_fixture(db)
    now = datetime.now(UTC)
    verify(
        db,
        scan_request(
            serial=fx["identity"].serial, location=BENGALURU, occurred_at=now - timedelta(hours=2)
        ),
    )
    verify(
        db,
        scan_request(
            serial=fx["identity"].serial, location=MUMBAI, occurred_at=now - timedelta(hours=1)
        ),
    )
    run_detection(db, identity=fx["identity"], actor=FULLY_AUTHORIZED_TEST_ACTOR)
    return fx


def test_assessment_requires_the_review_risk_capability(postgres_db_session):
    fx = _flagged_identity(postgres_db_session)
    powerless = ActorContext(actor_id="no-capabilities")

    with pytest.raises(CapabilityNotHeldError):
        assess_identity(postgres_db_session, identity=fx["identity"], actor=powerless)


def test_an_identity_with_no_evidence_cannot_be_assessed(postgres_db_session):
    fx = activated_identity_fixture(postgres_db_session)

    with pytest.raises(NoEvidenceToAssessError):
        assess_identity(
            postgres_db_session, identity=fx["identity"], actor=FULLY_AUTHORIZED_TEST_ACTOR
        )


def test_assessment_records_its_prior_ruleset_and_contributions(postgres_db_session):
    fx = _flagged_identity(postgres_db_session)

    assessment = assess_identity(
        postgres_db_session, identity=fx["identity"], actor=FULLY_AUTHORIZED_TEST_ACTOR
    )

    assert assessment.ruleset_version >= 1
    assert assessment.posterior_log_odds > assessment.prior_log_odds
    assert assessment.contributions
    assert all(c.benign_explanation for c in assessment.contributions)


def test_reassessment_appends_a_new_row_rather_than_overwriting(postgres_db_session):
    fx = _flagged_identity(postgres_db_session)

    first = assess_identity(
        postgres_db_session, identity=fx["identity"], actor=FULLY_AUTHORIZED_TEST_ACTOR
    )
    second = assess_identity(
        postgres_db_session, identity=fx["identity"], actor=FULLY_AUTHORIZED_TEST_ACTOR
    )

    assert first.id != second.id
    assert [a.sequence for a in assessment_history(
        postgres_db_session, identity_id=fx["identity"].id
    )] == [1, 2]
    assert latest_assessment(postgres_db_session, identity_id=fx["identity"].id).id == second.id


def test_assessments_form_an_unbroken_hash_chain(postgres_db_session):
    from app.core.event_chain import GENESIS_EVENT_HASH, verify_chain

    fx = _flagged_identity(postgres_db_session)
    assess_identity(
        postgres_db_session, identity=fx["identity"], actor=FULLY_AUTHORIZED_TEST_ACTOR
    )
    assess_identity(
        postgres_db_session, identity=fx["identity"], actor=FULLY_AUTHORIZED_TEST_ACTOR
    )

    rows = assessment_history(postgres_db_session, identity_id=fx["identity"].id)
    links = [(row.previous_event_hash, row.event_hash) for row in rows]
    assert links[0][0] == GENESIS_EVENT_HASH
    assert verify_chain(links) is True


def test_an_incident_cannot_be_opened_without_citing_evidence(postgres_db_session):
    fx = _flagged_identity(postgres_db_session)
    assessment = assess_identity(
        postgres_db_session, identity=fx["identity"], actor=FULLY_AUTHORIZED_TEST_ACTOR
    )

    with pytest.raises(UncitedIncidentError):
        open_incident(
            postgres_db_session,
            assessment=assessment,
            evidence=[],
            summary="no evidence cited",
            actor=FULLY_AUTHORIZED_TEST_ACTOR,
        )


def test_opening_an_incident_links_every_cited_evidence_row(postgres_db_session):
    fx = _flagged_identity(postgres_db_session)
    assessment = assess_identity(
        postgres_db_session, identity=fx["identity"], actor=FULLY_AUTHORIZED_TEST_ACTOR
    )
    evidence = identity_evidence(postgres_db_session, identity_id=fx["identity"].id)

    incident = open_incident(
        postgres_db_session,
        assessment=assessment,
        evidence=evidence,
        summary="Impossible travel between two scans",
        actor=FULLY_AUTHORIZED_TEST_ACTOR,
    )

    assert incident.status is IncidentStatus.OPEN
    cited = cited_evidence(postgres_db_session, incident_id=incident.id)
    assert {row.id for row in cited} == {row.id for row in evidence}


def test_incident_status_moves_only_along_legal_transitions(postgres_db_session):
    fx = _flagged_identity(postgres_db_session)
    assessment = assess_identity(
        postgres_db_session, identity=fx["identity"], actor=FULLY_AUTHORIZED_TEST_ACTOR
    )
    incident = open_incident(
        postgres_db_session,
        assessment=assessment,
        evidence=identity_evidence(postgres_db_session, identity_id=fx["identity"].id),
        summary="under review",
        actor=FULLY_AUTHORIZED_TEST_ACTOR,
    )

    with pytest.raises(IllegalIncidentTransitionError):
        transition_incident(
            postgres_db_session,
            incident=incident,
            new_status=IncidentStatus.SUBSTANTIATED,
            actor=FULLY_AUTHORIZED_TEST_ACTOR,
        )

    transition_incident(
        postgres_db_session,
        incident=incident,
        new_status=IncidentStatus.UNDER_REVIEW,
        actor=FULLY_AUTHORIZED_TEST_ACTOR,
    )
    transition_incident(
        postgres_db_session,
        incident=incident,
        new_status=IncidentStatus.SUBSTANTIATED,
        actor=FULLY_AUTHORIZED_TEST_ACTOR,
        note="confirmed by field visit",
    )

    assert incident.status is IncidentStatus.SUBSTANTIATED
    assert incident.resolved_at is not None
    assert [e.new_status for e in incident.events] == [
        IncidentStatus.OPEN,
        IncidentStatus.UNDER_REVIEW,
        IncidentStatus.SUBSTANTIATED,
    ]


def test_a_dismissed_incident_is_terminal(postgres_db_session):
    fx = _flagged_identity(postgres_db_session)
    assessment = assess_identity(
        postgres_db_session, identity=fx["identity"], actor=FULLY_AUTHORIZED_TEST_ACTOR
    )
    incident = open_incident(
        postgres_db_session,
        assessment=assessment,
        evidence=identity_evidence(postgres_db_session, identity_id=fx["identity"].id),
        summary="to be dismissed",
        actor=FULLY_AUTHORIZED_TEST_ACTOR,
    )
    transition_incident(
        postgres_db_session,
        incident=incident,
        new_status=IncidentStatus.DISMISSED,
        actor=FULLY_AUTHORIZED_TEST_ACTOR,
        note="location accuracy was the likelier explanation",
    )

    with pytest.raises(IllegalIncidentTransitionError):
        transition_incident(
            postgres_db_session,
            incident=incident,
            new_status=IncidentStatus.UNDER_REVIEW,
            actor=FULLY_AUTHORIZED_TEST_ACTOR,
        )


def test_open_incident_lookup_reflects_incident_status(postgres_db_session):
    fx = _flagged_identity(postgres_db_session)
    assert has_open_incident(postgres_db_session, fx["identity"].id) is False

    assessment = assess_identity(
        postgres_db_session, identity=fx["identity"], actor=FULLY_AUTHORIZED_TEST_ACTOR
    )
    incident = open_incident(
        postgres_db_session,
        assessment=assessment,
        evidence=identity_evidence(postgres_db_session, identity_id=fx["identity"].id),
        summary="open then dismissed",
        actor=FULLY_AUTHORIZED_TEST_ACTOR,
    )
    assert has_open_incident(postgres_db_session, fx["identity"].id) is True

    transition_incident(
        postgres_db_session,
        incident=incident,
        new_status=IncidentStatus.DISMISSED,
        actor=FULLY_AUTHORIZED_TEST_ACTOR,
    )
    assert has_open_incident(postgres_db_session, fx["identity"].id) is False


def test_elevated_risk_reflects_the_latest_assessment_only(postgres_db_session):
    fx = _flagged_identity(postgres_db_session)
    assess_identity(
        postgres_db_session, identity=fx["identity"], actor=FULLY_AUTHORIZED_TEST_ACTOR
    )

    assessment = latest_assessment(postgres_db_session, identity_id=fx["identity"].id)
    expected = assessment.confidence in {ConfidenceLevel.MODERATE, ConfidenceLevel.HIGH}
    assert has_elevated_risk(postgres_db_session, fx["identity"].id) is expected
