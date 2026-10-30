from __future__ import annotations

import uuid
from collections.abc import Callable, Generator

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.authorization import ActorContext, Capability, CapabilityNotHeldError
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.principal import (
    DEVELOPMENT_CREDENTIAL_PREFIX,
    DEVELOPMENT_ENVIRONMENTS,
    MalformedCredentialError,
    Principal,
    get_principal_resolver,
)
from app.core.tenancy import set_tenant_context
from app.domains.accounts import resolve_session

BEARER_PREFIX = "bearer "


def _credential(request: Request) -> str | None:
    header = request.headers.get("authorization")
    if header is None:
        return None
    if header.lower().startswith(BEARER_PREFIX):
        return header[len(BEARER_PREFIX) :].strip()
    return header.strip()


def current_principal(
    request: Request,
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> Principal:
    credential = _credential(request)
    if not credential:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This endpoint requires an authenticated actor.",
        )

    if credential.startswith(f"{DEVELOPMENT_CREDENTIAL_PREFIX}:"):
        if settings.environment not in DEVELOPMENT_ENVIRONMENTS:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Development credentials are not accepted here. Sign in instead.",
            )
        try:
            principal = get_principal_resolver(settings).resolve(credential)
        except MalformedCredentialError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
            ) from exc
    else:
        principal = resolve_session(db, credential)

    if principal is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session has ended or is not valid. Sign in again.",
        )
    return principal


def current_actor(principal: Principal = Depends(current_principal)) -> ActorContext:
    return principal.to_actor()


def tenant_db(
    principal: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
) -> Generator[Session, None, None]:
    set_tenant_context(db, principal.manufacturer_id)
    yield db


def requires(capability: Capability) -> Callable[[ActorContext], ActorContext]:
    def dependency(actor: ActorContext = Depends(current_actor)) -> ActorContext:
        try:
            actor.require(capability)
        except CapabilityNotHeldError as exc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
            ) from exc
        return actor

    return dependency


def development_only(settings: Settings = Depends(get_settings)) -> None:
    if settings.is_production:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


def owned_or_404(resource, manufacturer_id: uuid.UUID, *, name: str):
    if resource is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"{name} not found."
        )
    if getattr(resource, "manufacturer_id", None) != manufacturer_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"{name} not found."
        )
    return resource
