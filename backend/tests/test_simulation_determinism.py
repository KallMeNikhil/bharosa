from app.domains.identity import ProductIdentity
from app.domains.simulation import ScenarioType, ground_truth_for_run, run_simulation
from tests.simulation_fixtures import make_simulation_manufacturer, simulation_test_actor


def _serials_and_classifications(db, ground_truth):
    ordered = sorted(ground_truth, key=lambda entry: entry.sequence)
    serials = [db.get(ProductIdentity, entry.identity_id).serial for entry in ordered]
    classifications = [entry.classification.value for entry in ordered]
    injection_types = [entry.injection_type for entry in ordered]
    return serials, classifications, injection_types


def _metrics(evaluation):
    return (
        evaluation.true_positive_count,
        evaluation.false_positive_count,
        evaluation.true_negative_count,
        evaluation.false_negative_count,
    )


def test_the_same_seed_reproduces_the_same_scenario_structure(postgres_db_session):
    """Serials are deterministic from the seed, and globally unique in the schema.

    Reproducing the same seed twice therefore has to happen as two
    non-overlapping database states, not two rows coexisting at once — this
    is a property of the identity domain's global serial uniqueness, not a
    determinism gap. A nested savepoint gives each run a clean slate while
    keeping the manufacturer itself (created before the savepoint) shared.
    """
    manufacturer = make_simulation_manufacturer(postgres_db_session, name="Determinism")
    actor = simulation_test_actor(manufacturer.id)

    savepoint = postgres_db_session.begin_nested()
    _, ground_truth_one, evaluation_one = run_simulation(
        postgres_db_session,
        scenario_type=ScenarioType.CODE_CLONING,
        actor=actor,
        seed=4242,
        identity_count=6,
    )
    first = _serials_and_classifications(postgres_db_session, ground_truth_one)
    first_metrics = _metrics(evaluation_one)
    postgres_db_session.expire_all()
    savepoint.rollback()

    savepoint = postgres_db_session.begin_nested()
    _, ground_truth_two, evaluation_two = run_simulation(
        postgres_db_session,
        scenario_type=ScenarioType.CODE_CLONING,
        actor=actor,
        seed=4242,
        identity_count=6,
    )
    second = _serials_and_classifications(postgres_db_session, ground_truth_two)
    second_metrics = _metrics(evaluation_two)
    postgres_db_session.expire_all()
    savepoint.rollback()

    assert first == second
    assert first_metrics == second_metrics


def test_a_different_seed_produces_a_different_scenario(postgres_db_session):
    manufacturer = make_simulation_manufacturer(postgres_db_session, name="Variation")
    actor = simulation_test_actor(manufacturer.id)

    savepoint = postgres_db_session.begin_nested()
    _, ground_truth_one, _ = run_simulation(
        postgres_db_session,
        scenario_type=ScenarioType.CODE_CLONING,
        actor=actor,
        seed=1,
        identity_count=6,
    )
    first_serials, _, _ = _serials_and_classifications(postgres_db_session, ground_truth_one)
    postgres_db_session.expire_all()
    savepoint.rollback()

    savepoint = postgres_db_session.begin_nested()
    _, ground_truth_two, _ = run_simulation(
        postgres_db_session,
        scenario_type=ScenarioType.CODE_CLONING,
        actor=actor,
        seed=2,
        identity_count=6,
    )
    second_serials, _, _ = _serials_and_classifications(postgres_db_session, ground_truth_two)
    postgres_db_session.expire_all()
    savepoint.rollback()

    assert first_serials != second_serials


def test_repeated_runs_in_the_same_tenant_do_not_collide_on_reference_data(postgres_db_session):
    manufacturer = make_simulation_manufacturer(postgres_db_session)
    actor = simulation_test_actor(manufacturer.id)

    first_run, _, _ = run_simulation(
        postgres_db_session,
        scenario_type=ScenarioType.LEGITIMATE_BASELINE,
        actor=actor,
        seed=10,
        identity_count=2,
    )
    second_run, _, _ = run_simulation(
        postgres_db_session,
        scenario_type=ScenarioType.LEGITIMATE_BASELINE,
        actor=actor,
        seed=11,
        identity_count=2,
    )

    assert first_run.run_ref != second_run.run_ref
    assert first_run.id != second_run.id


def test_ground_truth_is_recorded_in_a_stable_hash_chain(postgres_db_session):
    manufacturer = make_simulation_manufacturer(postgres_db_session)
    actor = simulation_test_actor(manufacturer.id)
    run, _, _ = run_simulation(
        postgres_db_session,
        scenario_type=ScenarioType.DIVERSION,
        actor=actor,
        seed=99,
        identity_count=6,
    )

    entries = ground_truth_for_run(postgres_db_session, run_id=run.id)
    ordered = sorted(entries, key=lambda entry: entry.sequence)
    assert [entry.sequence for entry in ordered] == list(range(1, len(ordered) + 1))
    expected_previous = b"\x00" * 32
    for entry in ordered:
        assert entry.previous_event_hash == expected_previous
        expected_previous = entry.event_hash
