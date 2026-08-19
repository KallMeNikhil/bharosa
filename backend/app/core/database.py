from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)

verification_engine = create_engine(
    settings.verification_database_url, pool_pre_ping=True, future=True
)

# expire_on_commit is off because the tenant scope is a transaction-local
# setting. A route that commits and then touches a returned object would
# otherwise trigger a refresh SELECT after the scope had already been
# discarded by the commit, and row-level security would correctly hide the
# row the route had just written.
SessionLocal = sessionmaker(
    bind=engine, autoflush=False, autocommit=False, future=True, expire_on_commit=False
)

VerificationSessionLocal = sessionmaker(
    bind=verification_engine,
    autoflush=False,
    autocommit=False,
    future=True,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_verification_db() -> Generator[Session, None, None]:
    db = VerificationSessionLocal()
    try:
        yield db
    finally:
        db.close()
