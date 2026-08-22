import app.domains.simulation as simulation
from tests.simulation_fixtures import make_simulation_manufacturer, simulation_test_actor


def test_public_interface_exports_everything_this_test_needs():
    for name in [
        "ScenarioType",
        "SimulationRunStatus",
        "GroundTruthClassification",
        "SimulationRun",
        "SimulationGroundTruthEntry",
        "SimulationEvaluation",
        "SCENARIO_CATALOGUE",
        "DEFAULT_IDENTITY_COUNT",
        "MIN_IDENTITY_COUNT",
        "MAX_IDENTITY_COUNT",
        "run_simulation",
        "get_run",
        "list_runs",
        "ground_truth_for_run",
        "latest_evaluation",
        "evaluation_history",
        "recompute_evaluation",
        "ManufacturerNotOnboardedError",
        "InvalidIdentityCountError",
        "SimulationRunNotCompletedError",
    ]:
        assert hasattr(simulation, name), f"public interface missing {name!r}"


def test_full_workflow_using_only_public_interface(postgres_db_session):
    manufacturer = make_simulation_manufacturer(postgres_db_session)
    actor = simulation_test_actor(manufacturer.id)

    run, ground_truth, evaluation = simulation.run_simulation(
        postgres_db_session,
        scenario_type=simulation.ScenarioType.LEGITIMATE_BASELINE,
        actor=actor,
        seed=1,
        identity_count=3,
    )

    assert run.status is simulation.SimulationRunStatus.COMPLETED
    assert len(ground_truth) == 3
    assert evaluation.true_negative_count == 3

    fetched_run = simulation.get_run(postgres_db_session, run_id=run.id)
    assert fetched_run is not None
    assert fetched_run.id == run.id

    fetched_ground_truth = simulation.ground_truth_for_run(postgres_db_session, run_id=run.id)
    assert len(fetched_ground_truth) == 3

    fetched_evaluation = simulation.latest_evaluation(postgres_db_session, run_id=run.id)
    assert fetched_evaluation is not None
    assert fetched_evaluation.id == evaluation.id
