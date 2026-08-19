import math
import uuid

from app.domains.detection import FraudFamily, SignalType
from app.domains.risk import (
    BENIGN_EXPLANATIONS,
    DEFAULT_PRIOR_LOG_ODDS,
    ConfidenceLevel,
    EvidenceInput,
    accumulate,
    classify,
)


def _evidence(signal_type: SignalType, log_lr: float) -> EvidenceInput:
    from app.domains.detection import FAMILY_FOR_SIGNAL

    return EvidenceInput(
        evidence_id=uuid.uuid4(),
        signal_type=signal_type,
        fraud_family=FAMILY_FOR_SIGNAL[signal_type],
        log_likelihood_ratio=log_lr,
        explanation=f"{signal_type.value} observed",
    )


def test_no_evidence_leaves_the_prior_untouched():
    result = accumulate([])
    assert result.posterior_log_odds == DEFAULT_PRIOR_LOG_ODDS
    assert result.confidence is ConfidenceLevel.NEGLIGIBLE


def test_a_single_weak_signal_does_not_reach_a_conclusion():
    result = accumulate([_evidence(SignalType.DORMANCY_REACTIVATION, 1.1)])
    assert result.confidence is ConfidenceLevel.NEGLIGIBLE


def test_evidence_accumulates_additively_in_log_odds():
    single = accumulate([_evidence(SignalType.IMPOSSIBLE_TRAVEL, 2.0)])
    assert single.posterior_log_odds == DEFAULT_PRIOR_LOG_ODDS + 2.0


def test_repeated_signals_in_one_family_are_discounted():
    three_same = accumulate(
        [
            _evidence(SignalType.IMPOSSIBLE_TRAVEL, 2.0),
            _evidence(SignalType.GEOGRAPHIC_SPREAD, 2.0),
            _evidence(SignalType.SCAN_VELOCITY, 2.0),
        ]
    )
    naive_sum = DEFAULT_PRIOR_LOG_ODDS + 6.0
    assert three_same.posterior_log_odds < naive_sum
    assert three_same.posterior_log_odds == DEFAULT_PRIOR_LOG_ODDS + 2.0 + 1.0 + 0.5


def test_signals_from_different_families_are_not_discounted_against_each_other():
    across = accumulate(
        [
            _evidence(SignalType.IMPOSSIBLE_TRAVEL, 2.0),
            _evidence(SignalType.CHANNEL_VIOLATION, 2.0),
            _evidence(SignalType.SIGNATURE_INVALID, 2.0),
        ]
    )
    assert across.posterior_log_odds == DEFAULT_PRIOR_LOG_ODDS + 6.0


def test_many_weak_signals_do_not_outweigh_one_strong_signal_across_families():
    many_weak = accumulate([_evidence(SignalType.IMPOSSIBLE_TRAVEL, 1.0) for _ in range(6)])
    one_strong = accumulate([_evidence(SignalType.SIGNATURE_INVALID, 3.9)])
    assert many_weak.posterior_log_odds < one_strong.posterior_log_odds


def test_the_strongest_signal_in_a_family_receives_full_weight():
    result = accumulate(
        [
            _evidence(SignalType.SCAN_VELOCITY, 0.7),
            _evidence(SignalType.IMPOSSIBLE_TRAVEL, 3.0),
        ]
    )
    strongest = max(result.contributions, key=lambda c: c.raw_log_likelihood_ratio)
    assert strongest.signal_type is SignalType.IMPOSSIBLE_TRAVEL
    assert strongest.weight == 1.0


def test_every_contribution_carries_a_benign_alternative_explanation():
    result = accumulate(
        [
            _evidence(SignalType.IMPOSSIBLE_TRAVEL, 2.0),
            _evidence(SignalType.TERRITORY_VIOLATION, 1.1),
        ]
    )
    for contribution in result.contributions:
        assert contribution.benign_explanation == BENIGN_EXPLANATIONS[contribution.signal_type]
    assert len(result.alternative_explanations) == 2


def test_every_signal_type_has_a_benign_explanation():
    assert set(BENIGN_EXPLANATIONS) == set(SignalType)


def test_confidence_bands_are_ordered():
    assert classify(-10.0) is ConfidenceLevel.NEGLIGIBLE
    assert classify(-2.0) is ConfidenceLevel.LOW
    assert classify(0.0) is ConfidenceLevel.MODERATE
    assert classify(5.0) is ConfidenceLevel.HIGH


def test_probability_is_the_logistic_of_the_posterior():
    result = accumulate([_evidence(SignalType.SIGNATURE_INVALID, 6.9)])
    expected = 1.0 / (1.0 + math.exp(-result.posterior_log_odds))
    assert result.probability == expected
    assert 0.0 < result.probability < 1.0


def test_accumulation_never_produces_a_boolean_verdict():
    result = accumulate([_evidence(SignalType.SIGNATURE_INVALID, 3.9)])
    assert isinstance(result.posterior_log_odds, float)
    assert isinstance(result.confidence, ConfidenceLevel)
    assert result.contributions


def test_family_grouping_covers_every_family_present():
    result = accumulate(
        [
            _evidence(SignalType.SIGNATURE_INVALID, 3.9),
            _evidence(SignalType.IMPOSSIBLE_TRAVEL, 2.3),
            _evidence(SignalType.DORMANCY_REACTIVATION, 1.1),
            _evidence(SignalType.CHANNEL_VIOLATION, 1.4),
        ]
    )
    assert {c.fraud_family for c in result.contributions} == set(FraudFamily)
