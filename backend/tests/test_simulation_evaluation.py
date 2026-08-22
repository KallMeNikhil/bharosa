import pytest

from app.domains.simulation import (
    ScenarioType,
    SimulationRunNotCompletedError,
    SimulationRunStatus,
    evaluation_history,
    latest_evaluation,
    recompute_evaluation,
    run_simulation,
)
from tests.simulation_fixtures import make_simulation_manufacturer, simulation_test_actor


def test_precision_and_recall_are_null_rather_than_fabricated_when_undefined(
    postgres_db_session,
):
    manufacturer = make_simulation_manufacturer(postgres_db_session)
    actor = simulation_test_actor(manufacturer.id)

    _, _, evaluation = run_simulation(
        postgres_db_session,
        scenario_type=ScenarioType.LEGITIMATE_BASELINE,
        actor=actor,
        seed=1,
        identity_count=4,
    )

    assert evaluation.true_positive_count == 0
    assert evaluation.false_positive_count == 0
    assert evaluation.true_positive_count + evaluation.false_negative_count == 0
    assert evaluation.precision is None
    assert evaluation.recall is None
    assert evaluation.detection_rate is None
    assert evaluation.missed_fraud_rate is None


def test_evaluation_math_is_consistent_for_an_injected_scenario(postgres_db_session):
    manufacturer = make_simulation_manufacturer(postgres_db_session)
    actor = simulation_test_actor(manufacturer.id)

    _, ground_truth, evaluation = run_simulation(
        postgres_db_session,
        scenario_type=ScenarioType.DIVERSION,
        actor=actor,
        seed=5,
        identity_count=6,
    )

    tp = evaluation.true_positive_count
    fp = evaluation.false_positive_count
    fn = evaluation.false_negative_count

    if (tp + fp) > 0:
        assert evaluation.precision == pytest.approx(tp / (tp + fp))
    if (tp + fn) > 0:
        assert evaluation.recall == pytest.approx(tp / (tp + fn))
        assert evaluation.missed_fraud_rate == pytest.approx(fn / (tp + fn))
    assert evaluation.detection_rate == evaluation.recall

    total = evaluation.true_positive_count + evaluation.false_positive_count
    total += evaluation.true_negative_count + evaluation.false_negative_count
    assert total == len(ground_truth)


def test_recomputing_evaluation_appends_a_new_sequenced_row(postgres_db_session):
    manufacturer = make_simulation_manufacturer(postgres_db_session)
    actor = simulation_test_actor(manufacturer.id)

    run, _, first_evaluation = run_simulation(
        postgres_db_session,
        scenario_type=ScenarioType.DIVERSION,
        actor=actor,
        seed=6,
        identity_count=6,
    )

    second_evaluation = recompute_evaluation(postgres_db_session, run=run, actor=actor)

    assert second_evaluation.id != first_evaluation.id
    assert second_evaluation.sequence == first_evaluation.sequence + 1
    assert second_evaluation.previous_event_hash == first_evaluation.event_hash

    history = evaluation_history(postgres_db_session, run_id=run.id)
    assert [row.sequence for row in history] == [1, 2]
    assert latest_evaluation(postgres_db_session, run_id=run.id).id == second_evaluation.id


def test_evaluation_cannot_be_recomputed_for_a_run_that_never_completed(postgres_db_session):
    manufacturer = make_simulation_manufacturer(postgres_db_session)
    actor = simulation_test_actor(manufacturer.id)

    run, _, _ = run_simulation(
        postgres_db_session,
        scenario_type=ScenarioType.LEGITIMATE_BASELINE,
        actor=actor,
        seed=7,
        identity_count=2,
    )
    run.status = SimulationRunStatus.FAILED
    postgres_db_session.flush()

    with pytest.raises(SimulationRunNotCompletedError):
        recompute_evaluation(postgres_db_session, run=run, actor=actor)
