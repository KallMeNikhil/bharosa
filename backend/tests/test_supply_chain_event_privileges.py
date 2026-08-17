import os
import uuid
from datetime import UTC, datetime

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


def _seed_minimal_identity_and_participant(conn) -> tuple[uuid.UUID, uuid.UUID]:
    manufacturer_id = uuid.uuid4()
    product_id = uuid.uuid4()
    batch_id = uuid.uuid4()
    identity_id = uuid.uuid4()
    participant_id = uuid.uuid4()

    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO identity_manufacturer (id, name, status) VALUES (%s, %s, %s)",
            (manufacturer_id, "SC Privilege Test Manufacturer", "ACTIVE"),
        )
        cur.execute(
            "INSERT INTO identity_product (id, manufacturer_id, product_ref, name, status) "
            "VALUES (%s, %s, %s, %s, %s)",
            (
                product_id,
                manufacturer_id,
                f"SC-PRIV-PRODUCT-{product_id}",
                "SC Privilege Test",
                "ACTIVE",
            ),
        )
        cur.execute(
            "INSERT INTO identity_batch (id, product_id, batch_ref, status) "
            "VALUES (%s, %s, %s, %s)",
            (batch_id, product_id, f"SC-PRIV-BATCH-{batch_id}", "OPEN"),
        )
        cur.execute(
            "INSERT INTO identity_product_identity "
            "(id, batch_id, serial, manufacturer_id, lifecycle_state) "
            "VALUES (%s, %s, %s, %s, %s)",
            (
                identity_id,
                batch_id,
                f"SC-PRIV-SERIAL-{identity_id}",
                manufacturer_id,
                "RESERVED",
            ),
        )
        cur.execute(
            "INSERT INTO supply_chain_participant "
            "(id, manufacturer_id, participant_ref, name, role) "
            "VALUES (%s, %s, %s, %s, %s)",
            (participant_id, manufacturer_id, f"SC-PRIV-PART-{participant_id}", "Depot", "DEPOT"),
        )
    conn.commit()
    return identity_id, participant_id


def _insert_supply_chain_event(
    conn, identity_id: uuid.UUID, participant_id: uuid.UUID
) -> uuid.UUID:
    event_id = uuid.uuid4()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT manufacturer_id FROM identity_product_identity WHERE id = %s",
            (identity_id,),
        )
        manufacturer_id = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO supply_chain_event "
            "(id, manufacturer_id, identity_id, event_type, destination_participant_id, "
            "occurred_at) VALUES (%s, %s, %s, %s, %s, %s)",
            (
                event_id,
                manufacturer_id,
                identity_id,
                "DISPATCH",
                participant_id,
                datetime.now(UTC),
            ),
        )
    conn.commit()
    return event_id


def test_bharosa_app_can_insert_supply_chain_event(real_postgres_connection):
    identity_id, participant_id = _seed_minimal_identity_and_participant(
        real_postgres_connection
    )
    event_id = _insert_supply_chain_event(real_postgres_connection, identity_id, participant_id)

    with real_postgres_connection.cursor() as cur:
        cur.execute("SELECT id FROM supply_chain_event WHERE id = %s", (event_id,))
        assert cur.fetchone() is not None


def test_bharosa_app_cannot_update_supply_chain_event(real_postgres_connection):
    identity_id, participant_id = _seed_minimal_identity_and_participant(
        real_postgres_connection
    )
    event_id = _insert_supply_chain_event(real_postgres_connection, identity_id, participant_id)

    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with real_postgres_connection.cursor() as cur:
            cur.execute(
                "UPDATE supply_chain_event SET reason = %s WHERE id = %s",
                ("tampered", event_id),
            )
    real_postgres_connection.rollback()


def test_bharosa_app_cannot_delete_supply_chain_event(real_postgres_connection):
    identity_id, participant_id = _seed_minimal_identity_and_participant(
        real_postgres_connection
    )
    event_id = _insert_supply_chain_event(real_postgres_connection, identity_id, participant_id)

    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with real_postgres_connection.cursor() as cur:
            cur.execute("DELETE FROM supply_chain_event WHERE id = %s", (event_id,))
    real_postgres_connection.rollback()

    with real_postgres_connection.cursor() as cur:
        cur.execute("SELECT id FROM supply_chain_event WHERE id = %s", (event_id,))
        assert cur.fetchone() is not None


def test_bharosa_app_cannot_truncate_supply_chain_event(real_postgres_connection):
    identity_id, participant_id = _seed_minimal_identity_and_participant(
        real_postgres_connection
    )
    event_id = _insert_supply_chain_event(real_postgres_connection, identity_id, participant_id)

    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with real_postgres_connection.cursor() as cur:
            cur.execute("TRUNCATE TABLE supply_chain_event")
    real_postgres_connection.rollback()

    with real_postgres_connection.cursor() as cur:
        cur.execute("SELECT id FROM supply_chain_event WHERE id = %s", (event_id,))
        assert cur.fetchone() is not None
