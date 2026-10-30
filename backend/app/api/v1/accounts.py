from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api import schemas
from app.api.deps import _credential
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.ratelimit import InProcessTokenBucketRateLimiter, RateLimiter
from app.domains.accounts import (
    AccountError,
    EmailAlreadyRegisteredError,
    InvalidSignInError,
    SignedIn,
    register_account,
    sign_in,
    sign_out,
)

router = APIRouter(prefix="/auth", tags=["accounts"])

_rate_limiter: RateLimiter | None = None


def get_auth_rate_limiter(settings: Settings = Depends(get_settings)) -> RateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = InProcessTokenBucketRateLimiter(
            rate_per_minute=settings.auth_rate_limit_per_minute,
            burst=settings.auth_rate_limit_burst,
        )
    return _rate_limiter


def _throttle(request: Request, limiter: RateLimiter) -> None:
    client = request.client.host if request.client else "unknown"
    if not limiter.allow(client):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Wait a minute and try again.",
        )


class RegisterBody(BaseModel):
    company_name: str = Field(max_length=255)
    email: str = Field(max_length=320)
    password: str = Field(max_length=256)
    display_name: str | None = Field(default=None, max_length=255)


class SignInBody(BaseModel):
    email: str = Field(max_length=320)
    password: str = Field(max_length=256)


class AccountView(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str | None
    role: str


class SessionView(BaseModel):
    token: str
    expires_at: datetime
    account: AccountView
    manufacturer: schemas.ManufacturerView


def _session_view(signed_in: SignedIn) -> SessionView:
    account = signed_in.account
    return SessionView(
        token=signed_in.token,
        expires_at=signed_in.expires_at,
        account=AccountView(
            id=account.id,
            email=account.email,
            display_name=account.display_name,
            role=account.role,
        ),
        manufacturer=schemas.ManufacturerView.model_validate(signed_in.manufacturer),
    )


@router.post("/register", response_model=SessionView, status_code=status.HTTP_201_CREATED)
def register(
    body: RegisterBody,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    limiter: RateLimiter = Depends(get_auth_rate_limiter),
) -> SessionView:
    """Create a manufacturer and its owner account, and sign the owner in."""
    _throttle(request, limiter)
    try:
        signed_in = register_account(
            db,
            company_name=body.company_name,
            email=body.email,
            password=body.password,
            display_name=body.display_name,
            session_ttl=timedelta(hours=settings.session_ttl_hours),
        )
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except AccountError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    view = _session_view(signed_in)
    db.commit()
    return view


@router.post("/sign-in", response_model=SessionView)
def sign_in_route(
    body: SignInBody,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    limiter: RateLimiter = Depends(get_auth_rate_limiter),
) -> SessionView:
    _throttle(request, limiter)
    try:
        signed_in = sign_in(
            db,
            email=body.email,
            password=body.password,
            session_ttl=timedelta(hours=settings.session_ttl_hours),
        )
    except InvalidSignInError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    view = _session_view(signed_in)
    db.commit()
    return view


@router.post("/sign-out", status_code=status.HTTP_204_NO_CONTENT)
def sign_out_route(request: Request, db: Session = Depends(get_db)) -> Response:
    token = _credential(request)
    if token:
        sign_out(db, token)
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
