import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.domains.detection import models as detection_models  # noqa: F401
from app.domains.identity import models as identity_models  # noqa: F401
from app.domains.investigation import models as investigation_models  # noqa: F401
from app.domains.risk import models as risk_models  # noqa: F401
from app.domains.supply_chain import models as supply_chain_models  # noqa: F401
from app.domains.verification import models as verification_models  # noqa: F401
from app.main import app

TEST_DB_URL = "sqlite:///:memory:"

POSTGRES_TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://bharosa_app:bharosa_app@localhost:5432/bharosa",
)

POSTGRES_TEST_VERIFICATION_DATABASE_URL = os.environ.get(
    "TEST_VERIFICATION_DATABASE_URL",
    "postgresql+psycopg://bharosa_verifier:bharosa_verifier@localhost:5432/bharosa",
)

POSTGRES_TEST_MIGRATION_DATABASE_URL = os.environ.get(
    "TEST_MIGRATION_DATABASE_URL",
    "postgresql+psycopg://bharosa_owner:bharosa_owner@localhost:5432/bharosa",
)

MIGRATION_REQUIRED_MESSAGE = (
    "The test database is not at the current migration head. Row-level "
    "security policies and table grants are created by migrations, so tests "
    "run against an unmigrated database would silently pass without them. "
    "Run `alembic upgrade head` against the test database first."
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
    # created here. Domains carrying geometry columns, database grants or
    # row-level security policies are exercised against real PostgreSQL via
    # `postgres_db_session` instead.
    Base.metadata.create_all(engine, tables=_identity_only_tables())
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture(scope="session")
def _postgres_engine():
    owner_engine = create_engine(POSTGRES_TEST_MIGRATION_DATABASE_URL, future=True)
    with owner_engine.connect() as connection:
        existing = set(inspect(connection).get_table_names())
        required = set(Base.metadata.tables)
        if not required.issubset(existing):
            raise RuntimeError(
                f"{MIGRATION_REQUIRED_MESSAGE} Missing: {sorted(required - existing)}"
            )
    owner_engine.dispose()

    app_engine = create_engine(POSTGRES_TEST_DATABASE_URL, future=True)
    yield app_engine
    app_engine.dispose()


def _savepoint_session(engine):
    connection = engine.connect()
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


@pytest.fixture()
def postgres_db_session(_postgres_engine):
    yield from _savepoint_session(_postgres_engine)


@pytest.fixture()
def supply_chain_db_session(postgres_db_session):
    return postgres_db_session


@pytest.fixture()
def api_client(postgres_db_session):
    """A TestClient sharing the test transaction.

    Both the tenant session and the public verification session are bound to
    the same connection so that a request can see data the test just wrote and
    the whole thing rolls back afterwards. The separation between the two
    database roles is a property of deployment, and is asserted directly by
    the privilege tests rather than through this client.
    """
    from app.core.database import get_verification_db

    def _session():
        yield postgres_db_session

    app.dependency_overrides[get_db] = _session
    app.dependency_overrides[get_verification_db] = _session
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture(scope="session")
def _verifier_engine(_postgres_engine):
    engine = create_engine(POSTGRES_TEST_VERIFICATION_DATABASE_URL, future=True)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT current_user")).scalar() == "bharosa_verifier"
    yield engine
    engine.dispose()


@pytest.fixture()
def verifier_db_session(_verifier_engine):
    yield from _savepoint_session(_verifier_engine)
