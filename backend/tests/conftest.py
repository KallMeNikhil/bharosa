import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.domains.identity import models as identity_models  # noqa: F401
from app.domains.supply_chain import models as supply_chain_models  # noqa: F401
from app.main import app

TEST_DB_URL = "sqlite:///:memory:"

POSTGRES_TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://bharosa_app:bharosa_app@localhost:5432/bharosa",
)

POSTGRES_TEST_MIGRATION_DATABASE_URL = os.environ.get(
    "TEST_MIGRATION_DATABASE_URL",
    "postgresql+psycopg://bharosa_owner:bharosa_owner@localhost:5432/bharosa",
)


def _identity_only_tables():
    return [t for t in Base.metadata.tables.values() if t.name.startswith("identity_")]


@pytest.fixture()
def client():
    engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def identity_db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _enable_sqlite_fk(dbapi_connection, connection_record):  # noqa: ARG001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # SQLite has no PostGIS support, so only the identity domain's tables are
    # created here. The supply_chain domain (PostGIS geometry, ST_IsValid check
    # constraints) is exercised against real PostgreSQL via
    # `supply_chain_db_session` instead.
    Base.metadata.create_all(engine, tables=_identity_only_tables())
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture(scope="session")
def _supply_chain_postgres_engine():
    owner_engine = create_engine(POSTGRES_TEST_MIGRATION_DATABASE_URL, future=True)
    Base.metadata.create_all(owner_engine, checkfirst=True)
    owner_engine.dispose()

    app_engine = create_engine(POSTGRES_TEST_DATABASE_URL, future=True)
    yield app_engine
    app_engine.dispose()


@pytest.fixture()
def supply_chain_db_session(_supply_chain_postgres_engine):
    connection = _supply_chain_postgres_engine.connect()
    outer_transaction = connection.begin()
    Session = sessionmaker(
        bind=connection,
        autoflush=False,
        autocommit=False,
        future=True,
        join_transaction_mode="create_savepoint",
    )
    session = Session()
    try:
        yield session
    finally:
        session.close()
        outer_transaction.rollback()
        connection.close()
