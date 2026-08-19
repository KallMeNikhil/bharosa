from __future__ import annotations

import time
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.risk_signals import PLATFORM_RISK_SIGNALS
from app.core.client_reference import client_reference_hash
from app.core.config import Settings, get_settings
from app.core.database import get_verification_db
from app.core.ratelimit import InProcessTokenBucketRateLimiter, RateLimiter
from app.domains.verification import (
    InvalidCoordinateError,
    ScanLocation,
    VerificationChannel,
    VerificationRequest,
    VerificationState,
    verify,
)

router = APIRouter(tags=["verification"])

PUBLIC_MESSAGES: dict[VerificationState, str] = {
    VerificationState.GENUINE: (
        "This pack is registered and its recent history looks normal."
    ),
    VerificationState.CAUTION: (
        "This pack needs a closer look before you use it. Please contact the "
        "manufacturer's support line."
    ),
    VerificationState.INVALID: (
        "We could not confirm this code. It may not be registered with Bharosa. "
        "Please contact the manufacturer's support line."
    ),
    VerificationState.ALREADY_REPORTED: (
        "This pack has already been reported to the manufacturer. Please contact "
        "the manufacturer's support line."
    ),
    VerificationState.UNAVAILABLE: (
        "We cannot check this code right now. Please try again shortly."
    ),
}

_rate_limiter: RateLimiter | None = None


def get_rate_limiter(settings: Settings = Depends(get_settings)) -> RateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = InProcessTokenBucketRateLimiter(
            rate_per_minute=settings.verification_rate_limit_per_minute,
            burst=settings.verification_rate_limit_burst,
        )
    return _rate_limiter


class VerifyRequestBody(BaseModel):
    serial: str | None = Field(default=None, max_length=64)
    digital_link: str | None = Field(default=None, max_length=512)
    longitude: float | None = None
    latitude: float | None = None
    reported_accuracy_m: int | None = Field(default=None, ge=0, le=100_000)
    channel: VerificationChannel = VerificationChannel.WEB


class VerifyResponse(BaseModel):
    state: VerificationState
    message: str
    checked_at: datetime


def _scan_location(body: VerifyRequestBody) -> ScanLocation | None:
    if body.longitude is None or body.latitude is None:
        return None
    try:
        return ScanLocation(
            longitude=body.longitude,
            latitude=body.latitude,
            reported_accuracy_m=body.reported_accuracy_m,
        )
    except InvalidCoordinateError:
        return None


def _respond(state: VerificationState, checked_at: datetime) -> VerifyResponse:
    return VerifyResponse(state=state, message=PUBLIC_MESSAGES[state], checked_at=checked_at)


@router.post("/verify", response_model=VerifyResponse)
def verify_product(
    body: VerifyRequestBody,
    request: Request,
    db: Session = Depends(get_verification_db),
    settings: Settings = Depends(get_settings),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> VerifyResponse:
    """Public verification.

    Every response carries the same field set, and every request is held to a
    minimum duration, so that the time and shape of a reply reveal nothing
    about whether the scanned code resolved to a real identity.
    """
    started_at = time.monotonic()
    checked_at = datetime.now(UTC)

    client_host = request.client.host if request.client else None
    reference_hash = client_reference_hash(settings, client_host)

    try:
        if not rate_limiter.allow(client_host or "unknown"):
            return _hold(_respond(VerificationState.UNAVAILABLE, checked_at), started_at, settings)

        result = verify(
            db,
            risk_signals=PLATFORM_RISK_SIGNALS,
            request=VerificationRequest(
                channel=body.channel,
                occurred_at=checked_at,
                serial=body.serial,
                digital_link=body.digital_link,
                location=_scan_location(body),
                client_reference_hash=reference_hash,
            ),
        )
        db.commit()
        response = _respond(result.state, checked_at)
    except SQLAlchemyError:
        db.rollback()
        response = _respond(VerificationState.UNAVAILABLE, checked_at)

    return _hold(response, started_at, settings)


def _hold(
    response: VerifyResponse, started_at: float, settings: Settings
) -> VerifyResponse:
    remaining = settings.verification_min_response_seconds - (time.monotonic() - started_at)
    if remaining > 0:
        time.sleep(remaining)
    return response
