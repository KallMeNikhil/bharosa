from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api import schemas
from app.api.deps import current_actor, owned_or_404, requires, tenant_db
from app.core.authorization import ActorContext, Capability
from app.domains.detection import DetectionEvidence, identity_evidence, run_detection
from app.domains.identity import ProductIdentity
from app.domains.investigation import (
    FraudIncident,
    build_custody_graph,
    cited_evidence,
    common_divergence_point,
    first_divergence,
    open_incident,
    transition_incident,
)
from app.domains.risk import RiskAssessment, assess_identity, assessment_history
from app.domains.verification import identity_verification_history

router = APIRouter(tags=["intelligence"])


def _identity(db: Session, actor: ActorContext, identity_id: uuid.UUID) -> ProductIdentity:
    return owned_or_404(
        db.get(ProductIdentity, identity_id), actor.manufacturer_id, name="Identity"
    )


@router.get(
    "/identities/{identity_id}/verification-events",
    response_model=list[schemas.VerificationEventView],
    tags=["verification"],
)
def verification_events(
    identity_id: uuid.UUID,
    actor: ActorContext = Depends(current_actor),
    db: Session = Depends(tenant_db),
):
    _identity(db, actor, identity_id)
    return identity_verification_history(db, identity_id=identity_id)


@router.post(
    "/identities/{identity_id}/detection-runs",
    response_model=list[schemas.EvidenceView],
    status_code=status.HTTP_201_CREATED,
    tags=["detection"],
)
def run_detection_for_identity(
    identity_id: uuid.UUID,
    actor: ActorContext = Depends(requires(Capability.RUN_DETECTION)),
    db: Session = Depends(tenant_db),
) -> list[DetectionEvidence]:
    identity = _identity(db, actor, identity_id)
    evidence = run_detection(db, identity=identity, actor=actor)
    db.commit()
    return evidence


@router.get(
    "/identities/{identity_id}/evidence",
    response_model=list[schemas.EvidenceView],
    tags=["detection"],
)
def list_evidence(
    identity_id: uuid.UUID,
    actor: ActorContext = Depends(current_actor),
    db: Session = Depends(tenant_db),
) -> list[DetectionEvidence]:
    _identity(db, actor, identity_id)
    return identity_evidence(db, identity_id=identity_id)


@router.post(
    "/identities/{identity_id}/risk-assessments",
    response_model=schemas.RiskAssessmentView,
    status_code=status.HTTP_201_CREATED,
    tags=["risk"],
)
def assess(
    identity_id: uuid.UUID,
    actor: ActorContext = Depends(requires(Capability.REVIEW_RISK)),
    db: Session = Depends(tenant_db),
) -> RiskAssessment:
    identity = _identity(db, actor, identity_id)
    assessment = assess_identity(db, identity=identity, actor=actor)
    db.commit()
    return assessment


@router.get(
    "/identities/{identity_id}/risk-assessments",
    response_model=list[schemas.RiskAssessmentView],
    tags=["risk"],
)
def list_assessments(
    identity_id: uuid.UUID,
    actor: ActorContext = Depends(current_actor),
    db: Session = Depends(tenant_db),
) -> list[RiskAssessment]:
    _identity(db, actor, identity_id)
    return assessment_history(db, identity_id=identity_id)


@router.post(
    "/investigations",
    response_model=schemas.IncidentView,
    status_code=status.HTTP_201_CREATED,
    tags=["investigation"],
)
def open_investigation(
    body: schemas.IncidentOpen,
    actor: ActorContext = Depends(requires(Capability.MANAGE_INVESTIGATION)),
    db: Session = Depends(tenant_db),
) -> FraudIncident:
    assessment = owned_or_404(
        db.get(RiskAssessment, body.risk_assessment_id),
        actor.manufacturer_id,
        name="Risk assessment",
    )
    evidence = list(
        db.execute(
            select(DetectionEvidence).where(DetectionEvidence.id.in_(body.evidence_ids))
        )
        .scalars()
        .all()
    )
    if len(evidence) != len(set(body.evidence_ids)):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more cited evidence records were not found.",
        )

    incident = open_incident(
        db,
        assessment=assessment,
        evidence=evidence,
        summary=body.summary,
        actor=actor,
    )
    db.commit()
    return incident


@router.get(
    "/investigations", response_model=list[schemas.IncidentView], tags=["investigation"]
)
def list_investigations(
    identity_id: uuid.UUID | None = None, db: Session = Depends(tenant_db)
) -> list[FraudIncident]:
    statement = select(FraudIncident).order_by(FraudIncident.opened_at.desc())
    if identity_id is not None:
        statement = statement.where(FraudIncident.identity_id == identity_id)
    return list(db.execute(statement).scalars().all())


@router.get(
    "/investigations/{incident_id}",
    response_model=schemas.IncidentDetailView,
    tags=["investigation"],
)
def get_investigation(
    incident_id: uuid.UUID,
    actor: ActorContext = Depends(current_actor),
    db: Session = Depends(tenant_db),
) -> schemas.IncidentDetailView:
    incident = owned_or_404(
        db.get(FraudIncident, incident_id), actor.manufacturer_id, name="Incident"
    )
    return schemas.IncidentDetailView(
        **schemas.IncidentView.model_validate(incident).model_dump(),
        cited_evidence=[
            schemas.EvidenceView.model_validate(row)
            for row in cited_evidence(db, incident_id=incident.id)
        ],
        events=[schemas.IncidentEventView.model_validate(e) for e in incident.events],
    )


@router.post(
    "/investigations/{incident_id}/transitions",
    response_model=schemas.IncidentView,
    tags=["investigation"],
)
def transition_investigation(
    incident_id: uuid.UUID,
    body: schemas.IncidentTransition,
    actor: ActorContext = Depends(requires(Capability.MANAGE_INVESTIGATION)),
    db: Session = Depends(tenant_db),
) -> FraudIncident:
    incident = owned_or_404(
        db.get(FraudIncident, incident_id), actor.manufacturer_id, name="Incident"
    )
    updated = transition_incident(
        db, incident=incident, new_status=body.new_status, actor=actor, note=body.note
    )
    db.commit()
    return updated


@router.get(
    "/investigations/{incident_id}/divergence",
    response_model=schemas.DivergenceView,
    tags=["investigation"],
)
def incident_divergence(
    incident_id: uuid.UUID,
    actor: ActorContext = Depends(current_actor),
    db: Session = Depends(tenant_db),
) -> schemas.DivergenceView:
    incident = owned_or_404(
        db.get(FraudIncident, incident_id), actor.manufacturer_id, name="Incident"
    )
    divergence = first_divergence(db, identity_id=incident.identity_id)
    if divergence is None:
        return schemas.DivergenceView(
            identity_id=incident.identity_id,
            event_id=None,
            expected_custodian=None,
            observed_custodian=None,
            description=None,
        )
    return schemas.DivergenceView(
        identity_id=incident.identity_id,
        event_id=divergence.event_id,
        expected_custodian=divergence.expected_custodian,
        observed_custodian=divergence.observed_custodian,
        description=divergence.description,
    )


@router.get(
    "/custody-graph", response_model=schemas.CustodyGraphView, tags=["investigation"]
)
def custody_graph(
    identity_ids: list[uuid.UUID] = Query(min_length=1, max_length=200),
    actor: ActorContext = Depends(current_actor),
    db: Session = Depends(tenant_db),
) -> schemas.CustodyGraphView:
    """A custody graph derived from the event log at request time.

    Nothing is cached or stored. Asking twice recomputes it, which is the
    point: the event log stays the only account of what happened.
    """
    for identity_id in identity_ids:
        _identity(db, actor, identity_id)

    graph = build_custody_graph(db, identity_ids=identity_ids)
    return schemas.CustodyGraphView(
        edges=[
            schemas.CustodyEdgeView(
                source=source, destination=destination, identity_count=data["identity_count"]
            )
            for source, destination, data in graph.edges(data=True)
        ],
        common_divergence_point=common_divergence_point(db, identity_ids=identity_ids),
    )
