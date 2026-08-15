from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db

router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict:
    """Liveness check. Must not depend on external systems."""
    return {"status": "ok"}


@router.get("/ready")
def ready(db: Session = Depends(get_db)) -> dict:
    """Readiness check. Verifies the database connection is usable."""
    db.execute(text("SELECT 1"))
    return {"status": "ready"}
