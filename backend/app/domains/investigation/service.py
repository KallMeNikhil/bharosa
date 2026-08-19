from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.authorization import ActorContext, Capability
from app.core.event_chain import compute_event_hash, next_chain_link
from app.domains.detection import DetectionEvidence
from app.domains.investigation.models import (
    FraudIncident,
    IncidentEvent,
    IncidentEvidenceCitation,
    IncidentStatus,
)
from app.domains.risk import RiskAssessment

_LEGAL_STATUS_TRANSITIONS: dict[IncidentStatus, set[IncidentStatus]] = {
    IncidentStatus.OPEN: {IncidentStatus.UNDER_REVIEW, IncidentStatus.DISMISSED},
    IncidentStatus.UNDER_REVIEW: {
        IncidentStatus.SUBSTANTIATED,
        IncidentStatus.DISMISSED,
    },
    IncidentStatus.SUBSTANTIATED: set(),
    IncidentStatus.DISMISSED: set(),
}

RESOLVED_STATUSES = frozenset({IncidentStatus.SUBSTANTIATED, IncidentStatus.DISMISSED})
OPEN_STATUSES = frozenset({IncidentStatus.OPEN, IncidentStatus.UNDER_REVIEW})


class UncitedIncidentError(ValueError):
    def __init__(self, identity_id: uuid.UUID) -> None:
        self.identity_id = identity_id
        super().__init__(
            f"An incident for identity {identity_id} was requested without any "
            f"detection evidence. A fraud incident is a conclusion and can "
            f"never exist without citing the evidence that supports it."
        )


class EvidenceNotForIdentityError(ValueError):
    def __init__(self, evidence_id: uuid.UUID, identity_id: uuid.UUID) -> None:
        self.evidence_id = evidence_id
        self.identity_id = identity_id
        super().__init__(
            f"Evidence {evidence_id} does not belong to identity {identity_id}."
        )


class IllegalIncidentTransitionError(ValueError):
    def __init__(self, current: IncidentStatus, requested: IncidentStatus) -> None:
        self.current = current
        self.requested = requested
        super().__init__(
            f"Illegal incident status transition: {current.value} -> {requested.value}"
        )


def _record_incident_event(
    db: Session,
    incident: FraudIncident,
    *,
    previous_status: IncidentStatus | None,
    new_status: IncidentStatus,
    actor: ActorContext,
    note: str | None,
) -> IncidentEvent:
    sequence, previous_event_hash = next_chain_link(
        db,
        sequence_column=IncidentEvent.sequence,
        event_hash_column=IncidentEvent.event_hash,
        scope_clause=IncidentEvent.incident_id == incident.id,
    )
    event_hash = compute_event_hash(
        previous_event_hash=previous_event_hash,
        event_kind="investigation_incident_event",
        fields=[
            str(incident.manufacturer_id),
            str(incident.id),
            str(sequence),
            previous_status.value if previous_status else None,
            new_status.value,
            actor.actor_id,
            note,
        ],
    )
    event = IncidentEvent(
        incident_id=incident.id,
        manufacturer_id=incident.manufacturer_id,
        sequence=sequence,
        previous_status=previous_status,
        new_status=new_status,
        note=note,
        actor=actor.actor_id,
        previous_event_hash=previous_event_hash,
        event_hash=event_hash,
    )
    db.add(event)
    db.flush()
    return event


def open_incident(
    db: Session,
    *,
    assessment: RiskAssessment,
    evidence: list[DetectionEvidence],
    summary: str,
    actor: ActorContext,
) -> FraudIncident:
    """Open an incident against a risk assessment.

    The evidence list is not optional and is not a convenience. An incident is
    the point at which the system asserts something about a real business, so
    the citation is checked here, before the row exists, rather than being
    left to a caller to remember.
    """
    actor.require(Capability.MANAGE_INVESTIGATION)

    if not evidence:
        raise UncitedIncidentError(assessment.identity_id)

    for row in evidence:
        if row.identity_id != assessment.identity_id:
            raise EvidenceNotForIdentityError(row.id, assessment.identity_id)

    incident = FraudIncident(
        manufacturer_id=assessment.manufacturer_id,
        identity_id=assessment.identity_id,
        risk_assessment_id=assessment.id,
        status=IncidentStatus.OPEN,
        summary=summary,
        opened_by=actor.actor_id,
    )
    db.add(incident)
    db.flush()

    for row in evidence:
        db.add(
            IncidentEvidenceCitation(
                incident_id=incident.id,
                manufacturer_id=assessment.manufacturer_id,
                evidence_id=row.id,
            )
        )
    db.flush()

    _record_incident_event(
        db,
        incident,
        previous_status=None,
        new_status=IncidentStatus.OPEN,
        actor=actor,
        note=summary,
    )
    return incident


def transition_incident(
    db: Session,
    *,
    incident: FraudIncident,
    new_status: IncidentStatus,
    actor: ActorContext,
    note: str | None = None,
) -> FraudIncident:
    actor.require(Capability.MANAGE_INVESTIGATION)

    allowed = _LEGAL_STATUS_TRANSITIONS.get(incident.status, set())
    if new_status not in allowed:
        raise IllegalIncidentTransitionError(incident.status, new_status)

    previous_status = incident.status
    incident.status = new_status
    if new_status in RESOLVED_STATUSES:
        incident.resolved_at = datetime.now(UTC)
    db.flush()

    _record_incident_event(
        db,
        incident,
        previous_status=previous_status,
        new_status=new_status,
        actor=actor,
        note=note,
    )
    return incident


def cited_evidence(db: Session, *, incident_id: uuid.UUID) -> list[DetectionEvidence]:
    return list(
        db.execute(
            select(DetectionEvidence)
            .join(
                IncidentEvidenceCitation,
                IncidentEvidenceCitation.evidence_id == DetectionEvidence.id,
            )
            .where(IncidentEvidenceCitation.incident_id == incident_id)
            .order_by(DetectionEvidence.sequence)
        )
        .scalars()
        .all()
    )


def open_incidents_for_identity(
    db: Session, *, identity_id: uuid.UUID
) -> list[FraudIncident]:
    return list(
        db.execute(
            select(FraudIncident).where(
                FraudIncident.identity_id == identity_id,
                FraudIncident.status.in_(OPEN_STATUSES),
            )
        )
        .scalars()
        .all()
    )


def has_open_incident(db: Session, identity_id: uuid.UUID) -> bool:
    return bool(open_incidents_for_identity(db, identity_id=identity_id))
