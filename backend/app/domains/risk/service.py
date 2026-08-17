from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.authorization import ActorContext, Capability
from app.core.event_chain import compute_event_hash, next_chain_link
from app.domains.detection import DetectionEvidence
from app.domains.identity import ProductIdentity
from app.domains.risk.correlation import (
    DEFAULT_PRIOR_LOG_ODDS,
    DEFAULT_WITHIN_FAMILY_DISCOUNT,
    RULESET_VERSION,
    ConfidenceLevel,
    CorrelationResult,
    EvidenceInput,
    accumulate,
)
from app.domains.risk.models import RiskAssessment, RiskAssessmentContribution

ELEVATED_CONFIDENCE_LEVELS = frozenset({ConfidenceLevel.MODERATE, ConfidenceLevel.HIGH})


class NoEvidenceToAssessError(ValueError):
    def __init__(self, identity_id: uuid.UUID) -> None:
        self.identity_id = identity_id
        super().__init__(
            f"Identity {identity_id} has no detection evidence. A risk "
            f"assessment is an aggregation of evidence and cannot be produced "
            f"without any."
        )


def _evidence_inputs(evidence: list[DetectionEvidence]) -> list[EvidenceInput]:
    return [
        EvidenceInput(
            evidence_id=row.id,
            signal_type=row.signal_type,
            fraud_family=row.fraud_family,
            log_likelihood_ratio=row.log_likelihood_ratio,
            explanation=row.explanation,
        )
        for row in evidence
    ]


def assess_identity(
    db: Session,
    *,
    identity: ProductIdentity,
    actor: ActorContext,
    prior_log_odds: float = DEFAULT_PRIOR_LOG_ODDS,
    within_family_discount: float = DEFAULT_WITHIN_FAMILY_DISCOUNT,
    now: datetime | None = None,
) -> RiskAssessment:
    actor.require(Capability.REVIEW_RISK)

    evidence = list(
        db.execute(
            select(DetectionEvidence)
            .where(DetectionEvidence.identity_id == identity.id)
            .order_by(DetectionEvidence.sequence)
        )
        .scalars()
        .all()
    )
    if not evidence:
        raise NoEvidenceToAssessError(identity.id)

    result = accumulate(
        _evidence_inputs(evidence),
        prior_log_odds=prior_log_odds,
        within_family_discount=within_family_discount,
    )

    generated_at = (now or datetime.now(UTC)).astimezone(UTC)
    window_start = min(row.window_start for row in evidence)
    window_end = max(row.window_end for row in evidence)

    sequence, previous_event_hash = next_chain_link(
        db,
        sequence_column=RiskAssessment.sequence,
        event_hash_column=RiskAssessment.event_hash,
        scope_clause=RiskAssessment.identity_id == identity.id,
    )
    event_hash = compute_event_hash(
        previous_event_hash=previous_event_hash,
        event_kind="risk_assessment",
        fields=[
            str(identity.manufacturer_id),
            str(identity.id),
            str(sequence),
            str(RULESET_VERSION),
            repr(result.prior_log_odds),
            repr(result.posterior_log_odds),
            result.confidence.value,
            *sorted(str(c.evidence_id) for c in result.contributions),
        ],
    )

    assessment = RiskAssessment(
        manufacturer_id=identity.manufacturer_id,
        identity_id=identity.id,
        sequence=sequence,
        ruleset_version=RULESET_VERSION,
        prior_log_odds=result.prior_log_odds,
        posterior_log_odds=result.posterior_log_odds,
        confidence=result.confidence,
        window_start=window_start,
        window_end=window_end,
        generated_at=generated_at,
        previous_event_hash=previous_event_hash,
        event_hash=event_hash,
    )
    db.add(assessment)
    db.flush()

    for contribution in result.contributions:
        db.add(
            RiskAssessmentContribution(
                assessment_id=assessment.id,
                manufacturer_id=identity.manufacturer_id,
                evidence_id=contribution.evidence_id,
                weight=contribution.weight,
                contributed_log_odds=contribution.contributed_log_odds,
                benign_explanation=contribution.benign_explanation,
            )
        )
    db.flush()
    return assessment


def latest_assessment(db: Session, *, identity_id: uuid.UUID) -> RiskAssessment | None:
    return db.execute(
        select(RiskAssessment)
        .where(RiskAssessment.identity_id == identity_id)
        .order_by(RiskAssessment.sequence.desc())
        .limit(1)
    ).scalar_one_or_none()


def assessment_history(db: Session, *, identity_id: uuid.UUID) -> list[RiskAssessment]:
    return list(
        db.execute(
            select(RiskAssessment)
            .where(RiskAssessment.identity_id == identity_id)
            .order_by(RiskAssessment.sequence)
        )
        .scalars()
        .all()
    )


def has_elevated_risk(db: Session, identity_id: uuid.UUID) -> bool:
    assessment = latest_assessment(db, identity_id=identity_id)
    return assessment is not None and assessment.confidence in ELEVATED_CONFIDENCE_LEVELS


def explain(result: CorrelationResult) -> list[str]:
    return [
        f"{c.signal_type.value}: {c.explanation} "
        f"(contributed {c.contributed_log_odds:+.2f} log-odds at weight {c.weight:.2f})"
        for c in result.contributions
    ]
