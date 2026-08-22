import uuid

import pytest

from app.core.authorization import ActorContext, Capability, CapabilityNotHeldError
from app.domains.simulation import (
    MAX_IDENTITY_COUNT,
    MIN_IDENTITY_COUNT,
    InvalidIdentityCountError,
    ManufacturerNotOnboardedError,
    ScenarioType,
    run_simulation,
)
from tests.simulation_fixtures import make_simulation_manufacturer, simulation_test_actor
from tests.tenancy_helpers import scope_to


def test_run_simulation_requires_the_run_simulation_capability(postgres_db_session):
    manufacturer = make_simulation_manufacturer(postgres_db_session)
    powerless = ActorContext(actor_id="no-capabilities", manufacturer_id=manufacturer.id)

    with pytest.raises(CapabilityNotHeldError):
        run_simulation(
            postgres_db_session,
            scenario_type=ScenarioType.LEGITIMATE_BASELINE,
            actor=powerless,
            seed=1,
            identity_count=2,
        )


def test_identity_count_below_the_minimum_is_rejected(postgres_db_session):
    manufacturer = make_simulation_manufacturer(postgres_db_session)
    actor = simulation_test_actor(manufacturer.id)

    with pytest.raises(InvalidIdentityCountError):
        run_simulation(
            postgres_db_session,
            scenario_type=ScenarioType.LEGITIMATE_BASELINE,
            actor=actor,
            seed=1,
            identity_count=MIN_IDENTITY_COUNT - 1,
        )


def test_identity_count_above_the_maximum_is_rejected(postgres_db_session):
    manufacturer = make_simulation_manufacturer(postgres_db_session)
    actor = simulation_test_actor(manufacturer.id)

    with pytest.raises(InvalidIdentityCountError):
        run_simulation(
            postgres_db_session,
            scenario_type=ScenarioType.LEGITIMATE_BASELINE,
            actor=actor,
            seed=1,
            identity_count=MAX_IDENTITY_COUNT + 1,
        )


def test_a_manufacturer_that_was_never_onboarded_is_rejected(postgres_db_session):
    manufacturer_id = uuid.uuid4()
    scope_to(postgres_db_session, manufacturer_id)
    actor = ActorContext(
        actor_id="unknown-tenant",
        manufacturer_id=manufacturer_id,
        capabilities=frozenset(Capability),
    )

    with pytest.raises(ManufacturerNotOnboardedError):
        run_simulation(
            postgres_db_session,
            scenario_type=ScenarioType.LEGITIMATE_BASELINE,
            actor=actor,
            seed=1,
            identity_count=2,
        )


def test_a_failed_run_records_its_status_and_error_rather_than_leaving_a_partial_row(
    postgres_db_session, monkeypatch
):
    manufacturer = make_simulation_manufacturer(postgres_db_session)
    actor = simulation_test_actor(manufacturer.id)

    import app.domains.simulation.service as service_module

    def _boom(*args, **kwargs):  # noqa: ARG001
        raise RuntimeError("synthetic failure for test coverage")

    monkeypatch.setattr(service_module, "generate_population", _boom)

    with pytest.raises(RuntimeError):
        run_simulation(
            postgres_db_session,
            scenario_type=ScenarioType.LEGITIMATE_BASELINE,
            actor=actor,
            seed=1,
            identity_count=2,
        )

    from app.domains.simulation.models import SimulationRun, SimulationRunStatus

    runs = (
        postgres_db_session.query(SimulationRun)
        .filter(SimulationRun.manufacturer_id == manufacturer.id)
        .all()
    )
    assert len(runs) == 1
    assert runs[0].status is SimulationRunStatus.FAILED
    assert "synthetic failure" in runs[0].error_message
