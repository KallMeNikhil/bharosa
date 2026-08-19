from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.authorization import CapabilityNotHeldError, TenantScopeViolationError
from app.core.config import get_settings
from app.domains.detection import UncitedSignalError
from app.domains.identity import (
    CanonicalPayloadError,
    CrossManufacturerKeyMismatchError,
    IllegalLifecycleTransitionError,
    KeyNotEligibleForSigningError,
    MalformedSerialError,
    UndatedBatchError,
)
from app.domains.investigation import (
    EvidenceNotForIdentityError,
    IllegalIncidentTransitionError,
    UncitedIncidentError,
)
from app.domains.risk import NoEvidenceToAssessError
from app.domains.supply_chain import (
    CrossManufacturerReferenceError,
    InvalidAuthorizationValidityError,
    InvalidTerritoryGeometryError,
    SupplyChainEventValidationError,
)
from app.domains.verification import InvalidCoordinateError, MalformedDigitalLinkError

settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.1.0")

app.include_router(api_router, prefix=settings.api_v1_prefix)

CONFLICT_ERRORS = (
    IllegalLifecycleTransitionError,
    IllegalIncidentTransitionError,
    KeyNotEligibleForSigningError,
)

BAD_REQUEST_ERRORS = (
    CanonicalPayloadError,
    CrossManufacturerKeyMismatchError,
    CrossManufacturerReferenceError,
    EvidenceNotForIdentityError,
    InvalidAuthorizationValidityError,
    InvalidCoordinateError,
    InvalidTerritoryGeometryError,
    MalformedDigitalLinkError,
    MalformedSerialError,
    NoEvidenceToAssessError,
    SupplyChainEventValidationError,
    UncitedIncidentError,
    UncitedSignalError,
    UndatedBatchError,
)


def _problem(status_code: int, detail: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": detail})


@app.exception_handler(CapabilityNotHeldError)
def _capability_not_held(request: Request, exc: CapabilityNotHeldError) -> JSONResponse:
    return _problem(status.HTTP_403_FORBIDDEN, str(exc))


@app.exception_handler(TenantScopeViolationError)
def _tenant_scope_violation(
    request: Request, exc: TenantScopeViolationError
) -> JSONResponse:
    return _problem(status.HTTP_404_NOT_FOUND, str(exc))


for _error in CONFLICT_ERRORS:
    app.add_exception_handler(
        _error,
        lambda request, exc: _problem(status.HTTP_409_CONFLICT, str(exc)),
    )

for _error in BAD_REQUEST_ERRORS:
    app.add_exception_handler(
        _error,
        lambda request, exc: _problem(status.HTTP_400_BAD_REQUEST, str(exc)),
    )
