from datetime import UTC, datetime, timedelta

from app.domains.investigation import (
    MANUFACTURER_NODE,
    build_custody_graph,
    common_divergence_point,
    custody_path,
    first_divergence,
)
from app.domains.supply_chain import ParticipantRole, record_dispatch, record_transfer
from tests.identity_fixtures import FULLY_AUTHORIZED_TEST_ACTOR
from tests.supply_chain_fixtures import full_supply_chain_fixture, make_participant
from tests.verification_fixtures import activate


def _now():
    return datetime.now(UTC)


def _identity_moving_through(db, fx, participants, *, batch_ref_suffix=""):
    from tests.identity_fixtures import make_signed_identity

    issued = fx["issued_key"]
    identity = make_signed_identity(
        db, fx["batch"], issued.manufacturer_key, fx["signer"], issued.key_handle
    )
    activate(db, identity)
    db.flush()

    at = _now() - timedelta(days=len(participants) + 1)
    record_dispatch(
        db,
        identity=identity,
        occurred_at=at,
        destination_participant=participants[0],
        actor=FULLY_AUTHORIZED_TEST_ACTOR,
    )
    for index, (source, destination) in enumerate(
        zip(participants, participants[1:], strict=False)
    ):
        record_transfer(
            db,
            identity=identity,
            occurred_at=at + timedelta(days=index + 1),
            source_participant=source,
            destination_participant=destination,
            actor=FULLY_AUTHORIZED_TEST_ACTOR,
        )
    db.flush()
    return identity


def test_custody_path_starts_at_the_manufacturer(postgres_db_session):
    fx = full_supply_chain_fixture(postgres_db_session)
    identity = _identity_moving_through(
        postgres_db_session, fx, [fx["depot"], fx["distributor"], fx["retailer"]]
    )

    path = custody_path(postgres_db_session, identity_id=identity.id)

    assert path[0] == MANUFACTURER_NODE
    assert path[-1] == str(fx["retailer"].id)


def test_an_unbroken_custody_chain_has_no_divergence(postgres_db_session):
    fx = full_supply_chain_fixture(postgres_db_session)
    identity = _identity_moving_through(
        postgres_db_session, fx, [fx["depot"], fx["distributor"], fx["retailer"]]
    )

    assert first_divergence(postgres_db_session, identity_id=identity.id) is None


def test_a_custody_gap_is_reported_as_the_first_divergence(postgres_db_session):
    fx = full_supply_chain_fixture(postgres_db_session)
    stranger = make_participant(
        postgres_db_session,
        fx["manufacturer"].id,
        participant_ref="UNKNOWN-001",
        name="Unrecorded Distributor",
        role=ParticipantRole.DISTRIBUTOR,
    )
    postgres_db_session.flush()

    identity = _identity_moving_through(postgres_db_session, fx, [fx["depot"]])
    record_transfer(
        postgres_db_session,
        identity=identity,
        occurred_at=_now(),
        source_participant=stranger,
        destination_participant=fx["retailer"],
        actor=FULLY_AUTHORIZED_TEST_ACTOR,
    )
    postgres_db_session.flush()

    divergence = first_divergence(postgres_db_session, identity_id=identity.id)

    assert divergence is not None
    assert divergence.expected_custodian == str(fx["depot"].id)
    assert divergence.observed_custodian == str(stranger.id)
    assert "custody" in divergence.description.lower()


def test_the_custody_graph_is_derived_and_counts_identities_per_edge(postgres_db_session):
    fx = full_supply_chain_fixture(postgres_db_session)
    first = _identity_moving_through(
        postgres_db_session, fx, [fx["depot"], fx["distributor"]]
    )
    second = _identity_moving_through(
        postgres_db_session, fx, [fx["depot"], fx["distributor"]]
    )

    graph = build_custody_graph(postgres_db_session, identity_ids=[first.id, second.id])

    assert graph.has_edge(MANUFACTURER_NODE, str(fx["depot"].id))
    assert graph[MANUFACTURER_NODE][str(fx["depot"].id)]["identity_count"] == 2
    assert graph[str(fx["depot"].id)][str(fx["distributor"].id)]["identity_count"] == 2


def test_common_divergence_point_is_the_deepest_shared_custodian(postgres_db_session):
    fx = full_supply_chain_fixture(postgres_db_session)
    second_retailer = make_participant(
        postgres_db_session,
        fx["manufacturer"].id,
        participant_ref="RET-002",
        name="Second Retailer",
        role=ParticipantRole.RETAILER,
    )
    postgres_db_session.flush()

    first = _identity_moving_through(
        postgres_db_session, fx, [fx["depot"], fx["distributor"], fx["retailer"]]
    )
    second = _identity_moving_through(
        postgres_db_session, fx, [fx["depot"], fx["distributor"], second_retailer]
    )

    shared = common_divergence_point(postgres_db_session, identity_ids=[first.id, second.id])

    assert shared == str(fx["distributor"].id)


def test_identities_sharing_only_the_manufacturer_report_the_manufacturer(postgres_db_session):
    fx = full_supply_chain_fixture(postgres_db_session)
    other_depot = make_participant(
        postgres_db_session,
        fx["manufacturer"].id,
        participant_ref="DEPOT-002",
        name="Second Depot",
        role=ParticipantRole.DEPOT,
    )
    postgres_db_session.flush()

    first = _identity_moving_through(postgres_db_session, fx, [fx["depot"]])
    second = _identity_moving_through(postgres_db_session, fx, [other_depot])

    shared = common_divergence_point(postgres_db_session, identity_ids=[first.id, second.id])

    assert shared == MANUFACTURER_NODE


def test_identities_with_no_custody_history_produce_no_divergence_point(postgres_db_session):
    fx = full_supply_chain_fixture(postgres_db_session)

    assert (
        common_divergence_point(postgres_db_session, identity_ids=[fx["identity"].id]) is None
    )


def test_the_graph_is_never_persisted(postgres_db_session):
    from sqlalchemy import inspect

    tables = set(inspect(postgres_db_session.bind).get_table_names())
    assert not any("graph" in name for name in tables)
