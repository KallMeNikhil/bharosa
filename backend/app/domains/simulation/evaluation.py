from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.domains.detection import identity_evidence
from app.domains.investigation import open_incidents_for_identity
from app.domains.simulation.models import GroundTruthClassification
from app.domains.simulation.runner import GeneratedIdentity


@dataclass(frozen=True)
class EvaluationResult:
    true_positive_count: int
    false_positive_count: int
    true_negative_count: int
    false_negative_count: int
    precision: float | None
    recall: float | None
    detection_rate: float | None
    missed_fraud_rate: float | None
    investigation_true_positive_count: int
    investigation_false_positive_count: int
    per_detector_breakdown: dict[str, dict[str, int]]


def evaluate(db: Session, *, generated: list[GeneratedIdentity]) -> EvaluationResult:
    """Compare independently-recorded ground truth against the real pipeline's output.

    Ground truth is read from what the generator/injector deliberately did,
    never from detector output, so a detector that fails to fire cannot
    retroactively make its own miss disappear from the count.
    """
    true_positive = false_positive = true_negative = false_negative = 0
    investigation_true_positive = investigation_false_positive = 0
    detector_breakdown: dict[str, dict[str, int]] = {}

    for entry in generated:
        evidence = identity_evidence(db, identity_id=entry.identity.id)
        predicted_positive = bool(evidence)
        ground_truth_positive = (
            entry.draft.classification is GroundTruthClassification.INJECTED_FRAUD
        )

        if predicted_positive and ground_truth_positive:
            true_positive += 1
        elif predicted_positive and not ground_truth_positive:
            false_positive += 1
        elif not predicted_positive and ground_truth_positive:
            false_negative += 1
        else:
            true_negative += 1

        has_incident = bool(open_incidents_for_identity(db, identity_id=entry.identity.id))
        if has_incident and ground_truth_positive:
            investigation_true_positive += 1
        elif has_incident and not ground_truth_positive:
            investigation_false_positive += 1

        for row in evidence:
            detector_entry = detector_breakdown.setdefault(row.detector_id, {})
            signal_key = row.signal_type.value
            detector_entry[signal_key] = detector_entry.get(signal_key, 0) + 1

    precision = (
        true_positive / (true_positive + false_positive)
        if (true_positive + false_positive) > 0
        else None
    )
    recall = (
        true_positive / (true_positive + false_negative)
        if (true_positive + false_negative) > 0
        else None
    )
    missed_fraud_rate = (
        false_negative / (true_positive + false_negative)
        if (true_positive + false_negative) > 0
        else None
    )

    return EvaluationResult(
        true_positive_count=true_positive,
        false_positive_count=false_positive,
        true_negative_count=true_negative,
        false_negative_count=false_negative,
        precision=precision,
        recall=recall,
        detection_rate=recall,
        missed_fraud_rate=missed_fraud_rate,
        investigation_true_positive_count=investigation_true_positive,
        investigation_false_positive_count=investigation_false_positive,
        per_detector_breakdown=detector_breakdown,
    )
