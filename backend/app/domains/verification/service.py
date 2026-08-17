from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.event_chain import compute_event_hash, next_chain_link
from app.domains.identity import (
    KeyStatus,
    LifecycleState,
    ProductIdentity,
    is_well_formed_serial,
    verify_cryptographic_authenticity,
)
from app.domains.verification.gs1 import (
    MalformedDigitalLinkError,
    parse_digital_link,
)
from app.domains.verification.location import ScanLocation
from app.domains.verification.models import (
    PhysicalCheckResult,
    UnresolvedScanTally,
    VerificationChannel,
    VerificationEvent,
    VerificationState,
)


class RiskSignals(Protocol):
    def has_open_incident(self, db: Session, identity_id: uuid.UUID) -> bool: ...

    def has_elevated_risk(self, db: Session, identity_id: uuid.UUID) -> bool: ...


class NoRiskSignals:
    def has_open_incident(self, db: Session, identity_id: uuid.UUID) -> bool:
        return False

    def has_elevated_risk(self, db: Session, identity_id: uuid.UUID) -> bool:
        return False


NO_RISK_SIGNALS = NoRiskSignals()


@dataclass(frozen=True)
class VerificationRequest:
    channel: VerificationChannel
    occurred_at: datetime
    serial: str | None = None
    digital_link: str | None = None
    location: ScanLocation | None = None
    client_reference_hash: bytes | None = None


@dataclass(frozen=True)
class VerificationResult:
    state: VerificationState
    event_id: uuid.UUID | None


def resolve_requested_serial(request: VerificationRequest) -> str | None:
    if request.serial is not None:
        return request.serial
    if request.digital_link is None:
        return None
    try:
        return parse_digital_link(request.digital_link).bharosa_serial
    except MalformedDigitalLinkError:
        return None


def _lookup_identity(db: Session, serial: str | None) -> ProductIdentity | None:
    if serial is None or not is_well_formed_serial(serial):
        return None
    return db.execute(
        select(ProductIdentity).where(ProductIdentity.serial == serial)
    ).scalar_one_or_none()


def _evaluate_state(
    db: Session,
    identity: ProductIdentity | None,
    *,
    risk_signals: RiskSignals,
) -> tuple[VerificationState, bool, KeyStatus | None]:
    if identity is None:
        return VerificationState.INVALID, False, None

    authenticity = verify_cryptographic_authenticity(identity)
    key_status = authenticity.key_status

    if not authenticity.signature_valid:
        return VerificationState.INVALID, False, key_status

    if identity.lifecycle_state is not LifecycleState.ACTIVATED:
        return VerificationState.INVALID, True, key_status

    if key_status is KeyStatus.REVOKED:
        return VerificationState.INVALID, True, key_status

    if risk_signals.has_open_incident(db, identity.id):
        return VerificationState.ALREADY_REPORTED, True, key_status

    if key_status is KeyStatus.COMPROMISED:
        return VerificationState.CAUTION, True, key_status

    if risk_signals.has_elevated_risk(db, identity.id):
        return VerificationState.CAUTION, True, key_status

    return VerificationState.GENUINE, True, key_status


def _record_verification_event(
    db: Session,
    identity: ProductIdentity,
    request: VerificationRequest,
    *,
    state: VerificationState,
    signature_valid: bool,
    key_status: KeyStatus | None,
    physical_check_result: PhysicalCheckResult,
) -> VerificationEvent:
    occurred_at = request.occurred_at.astimezone(UTC)
    location = request.location

    sequence, previous_event_hash = next_chain_link(
        db,
        sequence_column=VerificationEvent.sequence,
        event_hash_column=VerificationEvent.event_hash,
        scope_clause=VerificationEvent.identity_id == identity.id,
    )
    event_hash = compute_event_hash(
        previous_event_hash=previous_event_hash,
        event_kind="verification_event",
        fields=[
            str(identity.manufacturer_id),
            str(identity.id),
            str(sequence),
            state.value,
            request.channel.value,
            str(signature_valid),
            key_status.value if key_status else None,
            identity.lifecycle_state.value,
            physical_check_result.value,
            location.coarse_cell if location else None,
            occurred_at.isoformat(),
        ],
    )

    event = VerificationEvent(
        manufacturer_id=identity.manufacturer_id,
        identity_id=identity.id,
        sequence=sequence,
        state=state,
        channel=request.channel,
        signature_valid=signature_valid,
        key_status_at_scan=key_status.value if key_status else None,
        lifecycle_state_at_scan=identity.lifecycle_state.value,
        physical_check_result=physical_check_result,
        location=location.point_wkt if location else None,
        coarse_cell=location.coarse_cell if location else None,
        reported_accuracy_m=location.reported_accuracy_m if location else None,
        client_reference_hash=request.client_reference_hash,
        occurred_at=occurred_at,
        previous_event_hash=previous_event_hash,
        event_hash=event_hash,
    )
    db.add(event)
    db.flush()
    return event


def _tally_unresolved_scan(db: Session, request: VerificationRequest) -> None:
    if request.location is None:
        return

    occurred_at = request.occurred_at.astimezone(UTC)
    statement = (
        pg_insert(UnresolvedScanTally)
        .values(
            scan_date=occurred_at.date(),
            coarse_cell=request.location.coarse_cell,
            scan_count=1,
        )
        .on_conflict_do_update(
            constraint="uq_unresolved_scan_day_cell",
            set_={
                "scan_count": UnresolvedScanTally.scan_count + 1,
                "updated_at": occurred_at,
            },
        )
    )
    db.execute(statement)


def verify(
    db: Session,
    request: VerificationRequest,
    *,
    risk_signals: RiskSignals = NO_RISK_SIGNALS,
    physical_check_result: PhysicalCheckResult = PhysicalCheckResult.NOT_PRESENTED,
) -> VerificationResult:
    serial = resolve_requested_serial(request)
    identity = _lookup_identity(db, serial)
    state, signature_valid, key_status = _evaluate_state(
        db, identity, risk_signals=risk_signals
    )

    if identity is None:
        _tally_unresolved_scan(db, request)
        return VerificationResult(state=state, event_id=None)

    event = _record_verification_event(
        db,
        identity,
        request,
        state=state,
        signature_valid=signature_valid,
        key_status=key_status,
        physical_check_result=physical_check_result,
    )
    return VerificationResult(state=state, event_id=event.id)


def identity_verification_history(
    db: Session, *, identity_id: uuid.UUID
) -> list[VerificationEvent]:
    return list(
        db.execute(
            select(VerificationEvent)
            .where(VerificationEvent.identity_id == identity_id)
            .order_by(VerificationEvent.sequence)
        )
        .scalars()
        .all()
    )
