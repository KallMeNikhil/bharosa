import os
import uuid

import psycopg
import pytest

DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL_PSYCOPG",
    "postgresql://bharosa_app:bharosa_app@localhost:5432/bharosa",
)

pytestmark = pytest.mark.db_privilege


@pytest.fixture()
def real_postgres_connection():
    conn = psycopg.connect(DATABASE_URL)
    try:
        yield conn
    finally:
        conn.rollback()
        conn.close()


def _seed_minimal_identity_chain(conn) -> uuid.UUID:
    manufacturer_id = uuid.uuid4()
    product_id = uuid.uuid4()
    batch_id = uuid.uuid4()
    identity_id = uuid.uuid4()

    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO identity_manufacturer (id, name, status) VALUES (%s, %s, %s)",
            (manufacturer_id, "Privilege Test Manufacturer", "ACTIVE"),
        )
        cur.execute(
            "INSERT INTO identity_product (id, manufacturer_id, product_ref, name, status) "
            "VALUES (%s, %s, %s, %s, %s)",
            (
                product_id,
                manufacturer_id,
                f"PRIV-TEST-PRODUCT-{product_id}",
                "Privilege Test",
                "ACTIVE",
            ),
        )
        cur.execute(
            "INSERT INTO identity_batch (id, product_id, batch_ref, status) "
            "VALUES (%s, %s, %s, %s)",
            (batch_id, product_id, f"PRIV-TEST-BATCH-{batch_id}", "OPEN"),
        )
        cur.execute(
            "INSERT INTO identity_product_identity "
            "(id, batch_id, serial, manufacturer_id, lifecycle_state) "
            "VALUES (%s, %s, %s, %s, %s)",
            (identity_id, batch_id, f"PRIV-TEST-SERIAL-{identity_id}", manufacturer_id, "RESERVED"),
        )
    conn.commit()
    return identity_id


def _insert_issuance_event(conn, identity_id: uuid.UUID) -> uuid.UUID:
    event_id = uuid.uuid4()
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO identity_issuance_event "
            "(id, identity_id, sequence, event_type, previous_state, new_state) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (event_id, identity_id, 1, "RESERVED", None, "RESERVED"),
        )
    conn.commit()
    return event_id


def test_connection_is_the_actual_nonsuperuser_application_role(real_postgres_connection):
    with real_postgres_connection.cursor() as cur:
        cur.execute("SELECT current_user")
        current_user = cur.fetchone()[0]
        cur.execute("SELECT rolsuper FROM pg_roles WHERE rolname = %s", (current_user,))
        is_superuser = cur.fetchone()[0]

    assert current_user == "bharosa_app"
    assert is_superuser is False


def test_bharosa_app_can_insert_identity_issuance_event(real_postgres_connection):
    identity_id = _seed_minimal_identity_chain(real_postgres_connection)
    event_id = _insert_issuance_event(real_postgres_connection, identity_id)

    with real_postgres_connection.cursor() as cur:
        cur.execute("SELECT id FROM identity_issuance_event WHERE id = %s", (event_id,))
        assert cur.fetchone() is not None


def test_bharosa_app_cannot_update_identity_issuance_event(real_postgres_connection):
    identity_id = _seed_minimal_identity_chain(real_postgres_connection)
    event_id = _insert_issuance_event(real_postgres_connection, identity_id)

    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with real_postgres_connection.cursor() as cur:
            cur.execute(
                "UPDATE identity_issuance_event SET event_type = %s WHERE id = %s",
                ("SIGNED", event_id),
            )
    real_postgres_connection.rollback()

    with real_postgres_connection.cursor() as cur:
        cur.execute("SELECT event_type FROM identity_issuance_event WHERE id = %s", (event_id,))
        assert cur.fetchone()[0] == "RESERVED"


def test_bharosa_app_cannot_delete_identity_issuance_event(real_postgres_connection):
    identity_id = _seed_minimal_identity_chain(real_postgres_connection)
    event_id = _insert_issuance_event(real_postgres_connection, identity_id)

    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with real_postgres_connection.cursor() as cur:
            cur.execute("DELETE FROM identity_issuance_event WHERE id = %s", (event_id,))
    real_postgres_connection.rollback()

    with real_postgres_connection.cursor() as cur:
        cur.execute("SELECT id FROM identity_issuance_event WHERE id = %s", (event_id,))
        assert cur.fetchone() is not None


def test_bharosa_app_cannot_truncate_identity_issuance_event(real_postgres_connection):
    identity_id = _seed_minimal_identity_chain(real_postgres_connection)
    event_id = _insert_issuance_event(real_postgres_connection, identity_id)

    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with real_postgres_connection.cursor() as cur:
            cur.execute("TRUNCATE TABLE identity_issuance_event")
    real_postgres_connection.rollback()

    with real_postgres_connection.cursor() as cur:
        cur.execute("SELECT id FROM identity_issuance_event WHERE id = %s", (event_id,))
        assert cur.fetchone() is not None
