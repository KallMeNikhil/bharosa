from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.domains.identity import LifecycleState, ProductIdentity, transition_identity
from app.domains.verification import ScanLocation, VerificationChannel, VerificationRequest
from tests.identity_fixtures import FULLY_AUTHORIZED_TEST_ACTOR, full_signed_fixture

BENGALURU = ScanLocation(longitude=77.5946, latitude=12.9716)
MUMBAI = ScanLocation(longitude=72.8777, latitude=19.0760)


def activate(db: Session, identity: ProductIdentity) -> ProductIdentity:
    for state in [
        LifecycleState.PRINTED,
        LifecycleState.PRINT_VERIFIED,
        LifecycleState.RECONCILED,
        LifecycleState.ACTIVATED,
    ]:
        transition_identity(
            db, identity=identity, new_state=state, actor=FULLY_AUTHORIZED_TEST_ACTOR
        )
    return identity


def activated_identity_fixture(db: Session) -> dict:
    fixture = full_signed_fixture(db)
    activate(db, fixture["identity"])
    db.commit()
    return fixture


def scan_request(
    *,
    serial: str | None = None,
    digital_link: str | None = None,
    location: ScanLocation | None = None,
    occurred_at: datetime | None = None,
    channel: VerificationChannel = VerificationChannel.WEB,
) -> VerificationRequest:
    return VerificationRequest(
        channel=channel,
        occurred_at=occurred_at or datetime.now(UTC),
        serial=serial,
        digital_link=digital_link,
        location=location,
    )
