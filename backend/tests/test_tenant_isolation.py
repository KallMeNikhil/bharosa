import os
import uuid

import psycopg
import pytest

pytestmark = pytest.mark.db_privilege

APP_URL = os.environ.get(
    "TEST_DATABASE_URL_PSYCOPG",
    "postgresql://bharosa_app:bharosa_app@localhost:5432/bharosa",
)
VERIFIER_URL = os.environ.get(
    "TEST_VERIFICATION_DATABASE_URL_PSYCOPG",
    "postgresql://bharosa_verifier:bharosa_verifier@localhost:5432/bharosa",
)
OWNER_URL = os.environ.get(
    "TEST_MIGRATION_DATABASE_URL_PSYCOPG",
    "postgresql://bharosa_owner:bharosa_owner@localhost:5432/bharosa",
)

TENANT_TABLES = [
    "identity_manufacturer_key",
    "identity_product",
    "identity_batch",
    "identity_product_identity",
    "identity_issuance_event",
    "supply_chain_participant",
    "supply_chain_territory",
    "supply_chain_channel_authorization",
    "supply_chain_event",
    "verification_event",
    "detection_evidence",
    "risk_assessment",
    "investigation_fraud_incident",
]

VERIFIER_FORBIDDEN_TABLES = [
    "identity_product",
    "identity_batch",
    "supply_chain_participant",
    "supply_chain_territory",
    "supply_chain_event",
    "detection_evidence",
    "risk_assessment",
    "investigation_fraud_incident",
]


@pytest.fixture()
def app_connection():
    conn = psycopg.connect(APP_URL)
    try:
        yield conn
    finally:
        conn.rollback()
        conn.close()


@pytest.fixture()
def verifier_connection():
    conn = psycopg.connect(VERIFIER_URL)
    try:
        yield conn
    finally:
        conn.rollback()
        conn.close()


def _seed_manufacturer(name: str) -> uuid.UUID:
    manufacturer_id = uuid.uuid4()
    with psycopg.connect(OWNER_URL) as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO identity_manufacturer (id, name, status) VALUES (%s, %s, 'ACTIVE')",
            (manufacturer_id, name),
        )
        cur.execute(
            "INSERT INTO identity_product (id, manufacturer_id, product_ref, name, status) "
            "VALUES (%s, %s, %s, 'RLS Test', 'ACTIVE')",
            (uuid.uuid4(), manufacturer_id, f"RLS-{manufacturer_id}"),
        )
        conn.commit()
    return manufacturer_id


def _scope(cur, manufacturer_id: uuid.UUID | None) -> None:
    cur.execute(
        "SELECT set_config('bharosa.manufacturer_id', %s, true)",
        (str(manufacturer_id) if manufacturer_id else "",),
    )


@pytest.mark.parametrize("table", TENANT_TABLES)
def test_every_multi_tenant_table_has_row_level_security_enabled(table):
    with psycopg.connect(OWNER_URL) as conn, conn.cursor() as cur:
        cur.execute("SELECT relrowsecurity FROM pg_class WHERE relname = %s", (table,))
        assert cur.fetchone()[0] is True, f"{table} has no row-level security"


@pytest.mark.parametrize("table", TENANT_TABLES)
def test_every_multi_tenant_table_has_a_tenant_isolation_policy(table):
    with psycopg.connect(OWNER_URL) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM pg_policies "
            "WHERE tablename = %s AND policyname = 'tenant_isolation'",
            (table,),
        )
        assert cur.fetchone()[0] == 1, f"{table} has no tenant_isolation policy"


def test_a_session_with_no_tenant_context_sees_nothing(app_connection):
    _seed_manufacturer("RLS No Context")
    with app_connection.cursor() as cur:
        _scope(cur, None)
        cur.execute("SELECT count(*) FROM identity_product")
        assert cur.fetchone()[0] == 0


def test_a_scoped_session_sees_only_its_own_tenant(app_connection):
    first = _seed_manufacturer("RLS Tenant A")
    second = _seed_manufacturer("RLS Tenant B")

    with app_connection.cursor() as cur:
        _scope(cur, first)
        cur.execute("SELECT DISTINCT manufacturer_id FROM identity_product")
        visible = {row[0] for row in cur.fetchall()}

    assert first in visible
    assert second not in visible


def test_a_scoped_session_cannot_write_a_row_belonging_to_another_tenant(app_connection):
    first = _seed_manufacturer("RLS Write A")
    second = _seed_manufacturer("RLS Write B")

    with pytest.raises(psycopg.errors.InsufficientPrivilege), app_connection.cursor() as cur:
        _scope(cur, first)
        cur.execute(
            "INSERT INTO identity_product (id, manufacturer_id, product_ref, name, status) "
            "VALUES (%s, %s, 'CROSS-TENANT', 'Should not persist', 'ACTIVE')",
            (uuid.uuid4(), second),
        )
    app_connection.rollback()


@pytest.mark.parametrize("table", VERIFIER_FORBIDDEN_TABLES)
def test_the_public_verification_role_cannot_read_manufacturer_business_data(
    verifier_connection, table
):
    with pytest.raises(psycopg.errors.InsufficientPrivilege), verifier_connection.cursor() as cur:
        cur.execute(f"SELECT * FROM {table} LIMIT 1")
    verifier_connection.rollback()


def test_the_public_verification_role_can_read_the_two_tables_it_needs(
    verifier_connection,
):
    with verifier_connection.cursor() as cur:
        cur.execute("SELECT count(*) FROM identity_product_identity")
        cur.execute("SELECT count(*) FROM identity_manufacturer_key")


def test_the_public_verification_role_can_read_only_boolean_risk_flags(
    verifier_connection,
):
    with verifier_connection.cursor() as cur:
        cur.execute("SELECT * FROM verification_identity_risk_flag LIMIT 1")
        assert {d.name for d in cur.description} == {"identity_id", "elevated"}
        cur.execute("SELECT * FROM verification_identity_incident_flag LIMIT 1")
        assert {d.name for d in cur.description} == {"identity_id", "reported"}


def test_the_public_verification_role_cannot_modify_verification_history(
    verifier_connection,
):
    for statement in (
        "UPDATE verification_event SET state = 'GENUINE'",
        "DELETE FROM verification_event",
    ):
        with pytest.raises(
            psycopg.errors.InsufficientPrivilege
        ), verifier_connection.cursor() as cur:
            cur.execute(statement)
        verifier_connection.rollback()


@pytest.mark.parametrize(
    "table",
    [
        "identity_issuance_event",
        "identity_manufacturer_key_event",
        "supply_chain_event",
        "verification_event",
        "detection_evidence",
        "risk_assessment",
        "investigation_incident_event",
    ],
)
def test_the_application_role_cannot_rewrite_any_event_table(app_connection, table):
    for statement in (
        f"UPDATE {table} SET manufacturer_id = manufacturer_id",
        f"DELETE FROM {table}",
        f"TRUNCATE TABLE {table}",
    ):
        with pytest.raises(
            psycopg.errors.InsufficientPrivilege
        ), app_connection.cursor() as cur:
            cur.execute(statement)
        app_connection.rollback()


def test_the_application_role_is_not_a_superuser_and_cannot_bypass_row_security(
    app_connection,
):
    with app_connection.cursor() as cur:
        cur.execute(
            "SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user"
        )
        is_superuser, bypasses_rls = cur.fetchone()
    assert is_superuser is False
    assert bypasses_rls is False


def test_the_verification_role_is_not_a_superuser_and_cannot_bypass_row_security(
    verifier_connection,
):
    with verifier_connection.cursor() as cur:
        cur.execute(
            "SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user"
        )
        is_superuser, bypasses_rls = cur.fetchone()
    assert is_superuser is False
    assert bypasses_rls is False
