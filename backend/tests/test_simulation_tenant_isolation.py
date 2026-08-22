from sqlalchemy.orm import Session as SQLAlchemySession

from app.core.tenancy import set_tenant_context
from app.domains.simulation import (
    ScenarioType,
    get_run,
    ground_truth_for_run,
    list_runs,
    run_simulation,
)
from tests.simulation_fixtures import make_simulation_manufacturer, simulation_test_actor


def _fresh_view(db):
    """A second Session on the same connection/transaction, with an empty identity map.

    Session.get() short-circuits through the identity map for an object the
    session already holds, which would make a cross-tenant read look
    RLS-safe even when it isn't. A fresh Session sharing the same
    transaction forces a real SELECT to be evaluated against whatever tenant
    GUC is currently set on that connection.
    """
    return SQLAlchemySession(bind=db.connection(), autoflush=False, expire_on_commit=False)


def test_a_simulation_run_is_invisible_to_a_different_tenant(postgres_db_session):
    manufacturer_a = make_simulation_manufacturer(postgres_db_session, name="Tenant A")
    actor_a = simulation_test_actor(manufacturer_a.id)
    run, _, _ = run_simulation(
        postgres_db_session,
        scenario_type=ScenarioType.LEGITIMATE_BASELINE,
        actor=actor_a,
        seed=1,
        identity_count=2,
    )
    run_id = run.id

    make_simulation_manufacturer(postgres_db_session, name="Tenant B")

    other_tenant_view = _fresh_view(postgres_db_session)
    assert get_run(other_tenant_view, run_id=run_id) is None
    assert list_runs(other_tenant_view) == []
    assert ground_truth_for_run(other_tenant_view, run_id=run_id) == []
    other_tenant_view.close()

    set_tenant_context(postgres_db_session, manufacturer_a.id)
    own_tenant_view = _fresh_view(postgres_db_session)
    own_run = get_run(own_tenant_view, run_id=run_id)
    assert own_run is not None
    assert own_run.id == run_id
    own_tenant_view.close()


def test_list_runs_only_returns_the_current_tenants_runs(postgres_db_session):
    manufacturer_a = make_simulation_manufacturer(postgres_db_session, name="List Tenant A")
    actor_a = simulation_test_actor(manufacturer_a.id)
    run_simulation(
        postgres_db_session,
        scenario_type=ScenarioType.LEGITIMATE_BASELINE,
        actor=actor_a,
        seed=1,
        identity_count=2,
    )
    run_simulation(
        postgres_db_session,
        scenario_type=ScenarioType.LEGITIMATE_BASELINE,
        actor=actor_a,
        seed=2,
        identity_count=2,
    )

    manufacturer_b = make_simulation_manufacturer(postgres_db_session, name="List Tenant B")
    actor_b = simulation_test_actor(manufacturer_b.id)
    run_simulation(
        postgres_db_session,
        scenario_type=ScenarioType.LEGITIMATE_BASELINE,
        actor=actor_b,
        seed=3,
        identity_count=2,
    )

    tenant_b_view = _fresh_view(postgres_db_session)
    tenant_b_runs = list_runs(tenant_b_view)
    assert len(tenant_b_runs) == 1
    assert all(run.manufacturer_id == manufacturer_b.id for run in tenant_b_runs)
    tenant_b_view.close()

    set_tenant_context(postgres_db_session, manufacturer_a.id)
    tenant_a_view = _fresh_view(postgres_db_session)
    tenant_a_runs = list_runs(tenant_a_view)
    assert len(tenant_a_runs) == 2
    assert all(run.manufacturer_id == manufacturer_a.id for run in tenant_a_runs)
    tenant_a_view.close()
