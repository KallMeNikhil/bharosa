from __future__ import annotations

import enum
import math
import uuid
from dataclasses import dataclass, field

from app.domains.detection import FraudFamily, SignalType

RULESET_VERSION = 1

"""Likelihood-ratio evidence accumulation.

Each detector reports how many times more likely its observation is under
fraud than under legitimate use, as a natural log. Accumulating those in
log-odds space is addition, which is why detectors emit logs in the first
place.

Straight addition would let a pile of weak, mutually dependent signals from
one detector family out-argue a single strong signal from another, which is
the failure the architecture calls out. Signals inside a family are therefore
discounted geometrically -- the strongest counts in full, the next counts for
half of that, and so on -- while families are summed without discount, since
a geographic signal and a lifecycle signal are far closer to independent than
two geographic signals are.

The prior, the discount and the confidence bands are calibration parameters.
None of them are settled, and none of them are architecture.
"""

DEFAULT_PRIOR_LOG_ODDS = -6.9
DEFAULT_WITHIN_FAMILY_DISCOUNT = 0.5

LOW_CONFIDENCE_LOG_ODDS = -3.0
MODERATE_CONFIDENCE_LOG_ODDS = -1.0
HIGH_CONFIDENCE_LOG_ODDS = 1.5

BENIGN_EXPLANATIONS: dict[SignalType, str] = {
    SignalType.SIGNATURE_INVALID: (
        "A damaged, worn or misread code produces the same result as a forged one."
    ),
    SignalType.UNTRUSTED_KEY_AT_SCAN: (
        "A genuine pack signed before a key was rotated or withdrawn still carries "
        "the older key version."
    ),
    SignalType.PRE_ACTIVATION_SCAN: (
        "An internal test scan, or a print reconciliation that had not yet been "
        "synced when the pack was scanned."
    ),
    SignalType.IMPOSSIBLE_TRAVEL: (
        "Phone-reported locations can be badly wrong indoors, and a scan may be "
        "uploaded long after it was taken on a poor connection."
    ),
    SignalType.GEOGRAPHIC_SPREAD: (
        "Legitimate cross-territory sourcing, or a farmer who bought the pack "
        "while travelling."
    ),
    SignalType.SCAN_VELOCITY: (
        "A retailer sweeping inventory, or a household checking the same pack "
        "several times before use."
    ),
    SignalType.POST_SALE_SCAN_RESURGENCE: (
        "A genuine pack rechecked after purchase, or an empty container kept and "
        "rescanned by the farmer."
    ),
    SignalType.DORMANCY_REACTIVATION: (
        "Slow-moving genuine stock found at the back of a shelf a season later."
    ),
    SignalType.TERRITORY_VIOLATION: (
        "Territory is a commercial boundary, not a physical one; authorised "
        "cross-territory sale looks identical from the outside."
    ),
    SignalType.CHANNEL_VIOLATION: (
        "A channel authorisation recorded late, or allowed to lapse "
        "administratively while trading continued legitimately."
    ),
}


class ConfidenceLevel(str, enum.Enum):
    NEGLIGIBLE = "NEGLIGIBLE"
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"


@dataclass(frozen=True)
class EvidenceInput:
    evidence_id: uuid.UUID
    signal_type: SignalType
    fraud_family: FraudFamily
    log_likelihood_ratio: float
    explanation: str


@dataclass(frozen=True)
class Contribution:
    evidence_id: uuid.UUID
    signal_type: SignalType
    fraud_family: FraudFamily
    raw_log_likelihood_ratio: float
    weight: float
    contributed_log_odds: float
    explanation: str
    benign_explanation: str


@dataclass(frozen=True)
class CorrelationResult:
    prior_log_odds: float
    posterior_log_odds: float
    confidence: ConfidenceLevel
    contributions: tuple[Contribution, ...] = field(default_factory=tuple)

    @property
    def probability(self) -> float:
        return 1.0 / (1.0 + math.exp(-self.posterior_log_odds))

    @property
    def alternative_explanations(self) -> tuple[str, ...]:
        seen: dict[str, None] = {}
        for contribution in self.contributions:
            seen.setdefault(contribution.benign_explanation, None)
        return tuple(seen)


def classify(posterior_log_odds: float) -> ConfidenceLevel:
    if posterior_log_odds >= HIGH_CONFIDENCE_LOG_ODDS:
        return ConfidenceLevel.HIGH
    if posterior_log_odds >= MODERATE_CONFIDENCE_LOG_ODDS:
        return ConfidenceLevel.MODERATE
    if posterior_log_odds >= LOW_CONFIDENCE_LOG_ODDS:
        return ConfidenceLevel.LOW
    return ConfidenceLevel.NEGLIGIBLE


def accumulate(
    evidence: list[EvidenceInput],
    *,
    prior_log_odds: float = DEFAULT_PRIOR_LOG_ODDS,
    within_family_discount: float = DEFAULT_WITHIN_FAMILY_DISCOUNT,
) -> CorrelationResult:
    by_family: dict[FraudFamily, list[EvidenceInput]] = {}
    for item in evidence:
        by_family.setdefault(item.fraud_family, []).append(item)

    contributions: list[Contribution] = []
    posterior = prior_log_odds

    for family in sorted(by_family, key=lambda f: f.value):
        ranked = sorted(
            by_family[family], key=lambda e: e.log_likelihood_ratio, reverse=True
        )
        for rank, item in enumerate(ranked):
            weight = within_family_discount**rank
            contributed = item.log_likelihood_ratio * weight
            posterior += contributed
            contributions.append(
                Contribution(
                    evidence_id=item.evidence_id,
                    signal_type=item.signal_type,
                    fraud_family=item.fraud_family,
                    raw_log_likelihood_ratio=item.log_likelihood_ratio,
                    weight=weight,
                    contributed_log_odds=contributed,
                    explanation=item.explanation,
                    benign_explanation=BENIGN_EXPLANATIONS[item.signal_type],
                )
            )

    return CorrelationResult(
        prior_log_odds=prior_log_odds,
        posterior_log_odds=posterior,
        confidence=classify(posterior),
        contributions=tuple(contributions),
    )
