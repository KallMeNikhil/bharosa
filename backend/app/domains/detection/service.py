from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import bindparam, select, text
from sqlalchemy.orm import Session

from app.core.authorization import ActorContext, Capability
from app.core.event_chain import compute_event_hash, next_chain_link
from app.domains.detection.context import DetectionContext
from app.domains.detection.detectors import DETECTOR_REGISTRY, RegisteredDetector
from app.domains.detection.models import DetectionEvidence, DetectionEvidenceSource
from app.domains.detection.signals import Signal
from app.domains.detection.thresholds import DEFAULT_THRESHOLDS, DetectorThresholds
from app.domains.identity import IdentityIssuanceEvent, ProductIdentity
from app.domains.supply_chain import ParticipantRole, SupplyChainEvent
from app.domains.verification import VerificationEvent

CHANNEL_GOVERNED_ROLES = (ParticipantRole.DISTRIBUTOR.value, ParticipantRole.RETAILER.value)

_SCAN_COORDINATES = text(
    "SELECT id, ST_X(location::geometry) AS longitude, ST_Y(location::geometry) AS latitude "
    "FROM verification_event "
    "WHERE identity_id = :identity_id AND location IS NOT NULL "
    "AND occurred_at >= :window_start"
)

_SCAN_TERRITORY_CONTAINMENT = text(
    "SELECT ve.id, EXISTS ("
    "  SELECT 1 FROM supply_chain_territory t"
    "  JOIN supply_chain_channel_authorization ca"
    "    ON ca.territory_id = t.id AND ca.manufacturer_id = t.manufacturer_id"
    "  WHERE t.manufacturer_id = :manufacturer_id"
    "    AND ca.valid_from <= ve.occurred_at"
    "    AND (ca.valid_until IS NULL OR ca.valid_until > ve.occurred_at)"
    "    AND ST_Contains(t.boundary::geometry, ve.location::geometry)"
    ") AS inside "
    "FROM verification_event ve "
    "WHERE ve.identity_id = :identity_id AND ve.location IS NOT NULL "
    "AND ve.occurred_at >= :window_start"
)

_CUSTODIAN_AUTHORIZATION = text(
    "SELECT e.id, EXISTS ("
    "  SELECT 1 FROM supply_chain_channel_authorization ca"
    "  WHERE ca.participant_id = e.destination_participant_id"
    "    AND ca.manufacturer_id = e.manufacturer_id"
    "    AND ca.valid_from <= e.occurred_at"
    "    AND (ca.valid_until IS NULL OR ca.valid_until > e.occurred_at)"
    ") AS authorized "
    "FROM supply_chain_event e "
    "JOIN supply_chain_participant p ON p.id = e.destination_participant_id "
    "WHERE e.identity_id = :identity_id AND e.occurred_at >= :window_start "
    "AND p.role IN :governed_roles"
).bindparams(bindparam("governed_roles", expanding=True))


def signal_fingerprint(detector: RegisteredDetector, signal: Signal) -> bytes:
    digest = hashlib.sha256()
    digest.update(detector.detector_id.encode("utf-8"))
    digest.update(str(detector.detector_version).encode("utf-8"))
    digest.update(signal.signal_type.value.encode("utf-8"))
    for group in (
        signal.sources.verification_event_ids,
        signal.sources.supply_chain_event_ids,
        signal.sources.identity_issuance_event_ids,
    ):
        digest.update(b"|")
        for source_id in sorted(str(value) for value in group):
            digest.update(source_id.encode("utf-8"))
    return digest.digest()


def build_context(
    db: Session,
    *,
    identity: ProductIdentity,
    thresholds: DetectorThresholds = DEFAULT_THRESHOLDS,
    now: datetime | None = None,
) -> DetectionContext:
    now = (now or datetime.now(UTC)).astimezone(UTC)
    window_start = now - timedelta(days=thresholds.analysis_window_days)
    parameters = {"identity_id": identity.id, "window_start": window_start}

    verification_events = tuple(
        db.execute(
            select(VerificationEvent)
            .where(
                VerificationEvent.identity_id == identity.id,
                VerificationEvent.occurred_at >= window_start,
            )
            .order_by(VerificationEvent.occurred_at)
        )
        .scalars()
        .all()
    )
    supply_chain_events = tuple(
        db.execute(
            select(SupplyChainEvent)
            .where(
                SupplyChainEvent.identity_id == identity.id,
                SupplyChainEvent.occurred_at >= window_start,
            )
            .order_by(SupplyChainEvent.occurred_at)
        )
        .scalars()
        .all()
    )
    identity_issuance_events = tuple(
        db.execute(
            select(IdentityIssuanceEvent)
            .where(IdentityIssuanceEvent.identity_id == identity.id)
            .order_by(IdentityIssuanceEvent.sequence)
        )
        .scalars()
        .all()
    )

    coordinates = {
        row.id: (float(row.longitude), float(row.latitude))
        for row in db.execute(_SCAN_COORDINATES, parameters)
    }
    inside_territory = {
        row.id: bool(row.inside)
        for row in db.execute(
            _SCAN_TERRITORY_CONTAINMENT,
            {**parameters, "manufacturer_id": identity.manufacturer_id},
        )
    }
    custodian_authorized = {
        row.id: bool(row.authorized)
        for row in db.execute(
            _CUSTODIAN_AUTHORIZATION,
            {**parameters, "governed_roles": list(CHANNEL_GOVERNED_ROLES)},
        )
    }

    return DetectionContext(
        identity=identity,
        now=now,
        verification_events=verification_events,
        supply_chain_events=supply_chain_events,
        identity_issuance_events=identity_issuance_events,
        scan_coordinates=coordinates,
        scan_inside_authorized_territory=inside_territory,
        custodian_authorized_at_event=custodian_authorized,
        thresholds=thresholds,
    )


def _existing_fingerprints(db: Session, identity_id: uuid.UUID) -> set[bytes]:
    return set(
        db.execute(
            select(DetectionEvidence.signal_fingerprint).where(
                DetectionEvidence.identity_id == identity_id
            )
        )
        .scalars()
        .all()
    )


def _persist(
    db: Session,
    context: DetectionContext,
    detector: RegisteredDetector,
    signal: Signal,
    fingerprint: bytes,
    window_start: datetime,
) -> DetectionEvidence:
    identity = context.identity
    sequence, previous_event_hash = next_chain_link(
        db,
        sequence_column=DetectionEvidence.sequence,
        event_hash_column=DetectionEvidence.event_hash,
        scope_clause=DetectionEvidence.identity_id == identity.id,
    )
    event_hash = compute_event_hash(
        previous_event_hash=previous_event_hash,
        event_kind="detection_evidence",
        fields=[
            str(identity.manufacturer_id),
            str(identity.id),
            str(sequence),
            detector.detector_id,
            str(detector.detector_version),
            signal.signal_type.value,
            repr(signal.log_likelihood_ratio),
            signal.explanation,
            fingerprint.hex(),
        ],
    )

    evidence = DetectionEvidence(
        manufacturer_id=identity.manufacturer_id,
        identity_id=identity.id,
        sequence=sequence,
        detector_id=detector.detector_id,
        detector_version=detector.detector_version,
        signal_type=signal.signal_type,
        fraud_family=signal.family,
        log_likelihood_ratio=signal.log_likelihood_ratio,
        explanation=signal.explanation,
        signal_fingerprint=fingerprint,
        window_start=window_start,
        window_end=context.now,
        previous_event_hash=previous_event_hash,
        event_hash=event_hash,
    )
    db.add(evidence)
    db.flush()

    for source_id in signal.sources.verification_event_ids:
        db.add(
            DetectionEvidenceSource(
                evidence_id=evidence.id,
                manufacturer_id=identity.manufacturer_id,
                verification_event_id=source_id,
            )
        )
    for source_id in signal.sources.supply_chain_event_ids:
        db.add(
            DetectionEvidenceSource(
                evidence_id=evidence.id,
                manufacturer_id=identity.manufacturer_id,
                supply_chain_event_id=source_id,
            )
        )
    for source_id in signal.sources.identity_issuance_event_ids:
        db.add(
            DetectionEvidenceSource(
                evidence_id=evidence.id,
                manufacturer_id=identity.manufacturer_id,
                identity_issuance_event_id=source_id,
            )
        )
    db.flush()
    return evidence


def run_detection(
    db: Session,
    *,
    identity: ProductIdentity,
    actor: ActorContext,
    thresholds: DetectorThresholds = DEFAULT_THRESHOLDS,
    now: datetime | None = None,
) -> list[DetectionEvidence]:
    actor.require(Capability.RUN_DETECTION)

    context = build_context(db, identity=identity, thresholds=thresholds, now=now)
    window_start = context.now - timedelta(days=thresholds.analysis_window_days)
    already_recorded = _existing_fingerprints(db, identity.id)

    recorded: list[DetectionEvidence] = []
    for detector in DETECTOR_REGISTRY:
        for signal in detector.evaluate(context):
            fingerprint = signal_fingerprint(detector, signal)
            if fingerprint in already_recorded:
                continue
            already_recorded.add(fingerprint)
            recorded.append(
                _persist(db, context, detector, signal, fingerprint, window_start)
            )
    return recorded


def identity_evidence(db: Session, *, identity_id: uuid.UUID) -> list[DetectionEvidence]:
    return list(
        db.execute(
            select(DetectionEvidence)
            .where(DetectionEvidence.identity_id == identity_id)
            .order_by(DetectionEvidence.sequence)
        )
        .scalars()
        .all()
    )
