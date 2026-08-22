import pytest

from app.domains.simulation import ScenarioType, run_simulation
from tests.simulation_fixtures import make_simulation_manufacturer, simulation_test_actor

_EXPECTED_FAMILIES = {
    ScenarioType.FULL_COUNTERFEIT: {"counterfeit"},
    ScenarioType.CODE_CLONING: {"cloning"},
    ScenarioType.REFILLING: {"refilling"},
    ScenarioType.DIVERSION: {"diversion"},
    ScenarioType.COMBINED_MULTI_SIGNAL: {"cloning", "diversion"},
}


def test_legitimate_baseline_produces_only_true_negatives(postgres_db_session):
    manufacturer = make_simulation_manufacturer(postgres_db_session)
    actor = simulation_test_actor(manufacturer.id)

    run, ground_truth, evaluation = run_simulation(
        postgres_db_session,
        scenario_type=ScenarioType.LEGITIMATE_BASELINE,
        actor=actor,
        seed=1,
        identity_count=6,
    )

    assert evaluation.true_negative_count == 6
    assert evaluation.true_positive_count == 0
    assert evaluation.false_positive_count == 0
    assert evaluation.false_negative_count == 0
    assert evaluation.per_detector_breakdown == {}


def test_benign_anomaly_scenario_does_not_trigger_any_detector(postgres_db_session):
    manufacturer = make_simulation_manufacturer(postgres_db_session)
    actor = simulation_test_actor(manufacturer.id)

    run, ground_truth, evaluation = run_simulation(
        postgres_db_session,
        scenario_type=ScenarioType.BENIGN_ANOMALY,
        actor=actor,
        seed=2,
        identity_count=6,
    )

    assert all(entry.classification.value == "LEGITIMATE" for entry in ground_truth)
    assert evaluation.false_positive_count == 0, (
        "returns, reallocation and repeated same-territory scans below every "
        "threshold must never be treated as fraud by default"
    )
    assert evaluation.true_negative_count == 6


@pytest.mark.parametrize(
    "scenario_type",
    [
        ScenarioType.FULL_COUNTERFEIT,
        ScenarioType.CODE_CLONING,
        ScenarioType.REFILLING,
        ScenarioType.DIVERSION,
        ScenarioType.COMBINED_MULTI_SIGNAL,
    ],
)
def test_injected_scenarios_are_detected_by_the_expected_family(
    postgres_db_session, scenario_type
):
    manufacturer = make_simulation_manufacturer(
        postgres_db_session, name=f"Scenario {scenario_type.value}"
    )
    actor = simulation_test_actor(manufacturer.id)

    run, ground_truth, evaluation = run_simulation(
        postgres_db_session,
        scenario_type=scenario_type,
        actor=actor,
        seed=17,
        identity_count=6,
    )

    injected = [
        entry for entry in ground_truth if entry.classification.value == "INJECTED_FRAUD"
    ]
    legitimate = [
        entry for entry in ground_truth if entry.classification.value == "LEGITIMATE"
    ]

    assert injected, "scenario must inject at least one fraudulent identity"
    assert legitimate, "scenario must retain a legitimate population for contrast"

    assert evaluation.true_positive_count == len(injected)
    assert evaluation.false_negative_count == 0
    assert evaluation.false_positive_count == 0
    assert evaluation.true_negative_count == len(legitimate)

    detected_families = set(evaluation.per_detector_breakdown.keys())
    assert detected_families == _EXPECTED_FAMILIES[scenario_type]


def test_combined_scenario_escalates_to_an_open_incident(postgres_db_session):
    manufacturer = make_simulation_manufacturer(postgres_db_session)
    actor = simulation_test_actor(manufacturer.id)

    run, ground_truth, evaluation = run_simulation(
        postgres_db_session,
        scenario_type=ScenarioType.COMBINED_MULTI_SIGNAL,
        actor=actor,
        seed=1234,
        identity_count=9,
    )

    injected = [
        entry for entry in ground_truth if entry.classification.value == "INJECTED_FRAUD"
    ]
    assert evaluation.investigation_true_positive_count == len(injected)
    assert evaluation.investigation_false_positive_count == 0
