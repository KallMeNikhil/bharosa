from datetime import timedelta

import pytest

from app.domains.detection import (
    FraudFamily,
    Signal,
    SignalType,
    SourceEvents,
    UncitedSignalError,
)
from app.domains.detection.detectors import cloning, counterfeit, diversion, refilling
from app.domains.identity import LifecycleState
from app.domains.supply_chain import SupplyChainEventType
from tests.detection_fixtures import (
    BENGALURU,
    CHENNAI,
    HYDERABAD,
    MUMBAI,
    NOW,
    located_scans,
    make_context,
    make_scan,
    make_supply_chain_event,
)


def _types(signals):
    return {signal.signal_type for signal in signals}


def test_a_signal_cannot_be_created_without_citing_source_events():
    with pytest.raises(UncitedSignalError):
        Signal(
            signal_type=SignalType.SCAN_VELOCITY,
            log_likelihood_ratio=1.0,
            explanation="no sources",
        )


def test_every_signal_type_maps_to_a_fraud_family():
    for signal_type in SignalType:
        assert isinstance(
            Signal(
                signal_type=signal_type,
                log_likelihood_ratio=0.5,
                explanation="mapped",
                sources=SourceEvents(verification_event_ids=(make_scan(at=NOW).id,)),
            ).family,
            FraudFamily,
        )


def test_no_detector_emits_anything_for_an_identity_with_no_history():
    context = make_context()
    for module in (counterfeit, cloning, refilling, diversion):
        assert module.evaluate(context) == []


def test_invalid_signature_scan_produces_counterfeit_evidence():
    scan = make_scan(at=NOW, signature_valid=False)
    signals = counterfeit.evaluate(make_context(scans=[scan]))

    assert _types(signals) == {SignalType.SIGNATURE_INVALID}
    assert signals[0].family is FraudFamily.FULL_COUNTERFEIT
    assert signals[0].sources.verification_event_ids == (scan.id,)


def test_untrusted_key_at_scan_produces_counterfeit_evidence():
    scan = make_scan(at=NOW, key_status="COMPROMISED")
    assert _types(counterfeit.evaluate(make_context(scans=[scan]))) == {
        SignalType.UNTRUSTED_KEY_AT_SCAN
    }


def test_scan_before_activation_produces_counterfeit_evidence():
    scan = make_scan(at=NOW, lifecycle_state=LifecycleState.SIGNED)
    assert _types(counterfeit.evaluate(make_context(scans=[scan]))) == {
        SignalType.PRE_ACTIVATION_SCAN
    }


def test_impossible_travel_between_two_distant_scans():
    scans, coordinates = located_scans(
        [(timedelta(0), BENGALURU), (timedelta(hours=1), MUMBAI)]
    )
    signals = cloning.evaluate(make_context(scans=scans, scan_coordinates=coordinates))

    assert SignalType.IMPOSSIBLE_TRAVEL in _types(signals)


def test_the_same_journey_over_a_plausible_duration_is_not_impossible_travel():
    scans, coordinates = located_scans(
        [(timedelta(0), BENGALURU), (timedelta(hours=20), MUMBAI)]
    )
    signals = cloning.evaluate(make_context(scans=scans, scan_coordinates=coordinates))

    assert SignalType.IMPOSSIBLE_TRAVEL not in _types(signals)


def test_repeated_scans_in_one_place_are_never_treated_as_cloning():
    scans, coordinates = located_scans(
        [(timedelta(hours=n), BENGALURU) for n in range(6)]
    )
    assert cloning.evaluate(make_context(scans=scans, scan_coordinates=coordinates)) == []


def test_reported_accuracy_slack_suppresses_marginal_impossible_travel():
    near = (BENGALURU[0] + 0.2, BENGALURU[1])
    first = make_scan(at=NOW, coordinates=BENGALURU, reported_accuracy_m=20_000)
    second = make_scan(
        at=NOW + timedelta(minutes=5), coordinates=near, reported_accuracy_m=20_000
    )
    context = make_context(
        scans=[first, second],
        scan_coordinates={first.id: BENGALURU, second.id: near},
    )
    assert SignalType.IMPOSSIBLE_TRAVEL not in _types(cloning.evaluate(context))


def test_geographic_spread_across_four_distinct_localities():
    scans, coordinates = located_scans(
        [
            (timedelta(days=0), BENGALURU),
            (timedelta(days=10), MUMBAI),
            (timedelta(days=20), CHENNAI),
            (timedelta(days=30), HYDERABAD),
        ]
    )
    signals = cloning.evaluate(make_context(scans=scans, scan_coordinates=coordinates))

    assert SignalType.GEOGRAPHIC_SPREAD in _types(signals)


def test_three_localities_stay_below_the_spread_threshold():
    scans, coordinates = located_scans(
        [
            (timedelta(days=0), BENGALURU),
            (timedelta(days=10), MUMBAI),
            (timedelta(days=20), CHENNAI),
        ]
    )
    signals = cloning.evaluate(make_context(scans=scans, scan_coordinates=coordinates))

    assert SignalType.GEOGRAPHIC_SPREAD not in _types(signals)


def test_scan_velocity_fires_only_above_the_configured_rate():
    burst = [make_scan(at=NOW + timedelta(minutes=n * 10)) for n in range(12)]
    assert SignalType.SCAN_VELOCITY in _types(cloning.evaluate(make_context(scans=burst)))


def test_a_retailer_inventory_sweep_spread_over_days_is_not_a_velocity_signal():
    paced = [make_scan(at=NOW + timedelta(days=n)) for n in range(12)]
    assert SignalType.SCAN_VELOCITY not in _types(cloning.evaluate(make_context(scans=paced)))


def test_thresholds_are_parameters_not_constants():
    scans, coordinates = located_scans(
        [(timedelta(days=0), BENGALURU), (timedelta(days=10), MUMBAI)]
    )
    from dataclasses import replace

    from app.domains.detection import DEFAULT_THRESHOLDS

    relaxed = make_context(scans=scans, scan_coordinates=coordinates)
    strict = make_context(
        scans=scans,
        scan_coordinates=coordinates,
        thresholds=replace(DEFAULT_THRESHOLDS, geographic_spread_cell_count=2),
    )

    assert SignalType.GEOGRAPHIC_SPREAD not in _types(cloning.evaluate(relaxed))
    assert SignalType.GEOGRAPHIC_SPREAD in _types(cloning.evaluate(strict))


def test_scans_long_after_retail_placement_produce_refilling_evidence():
    placement = make_supply_chain_event(
        at=NOW, event_type=SupplyChainEventType.RETAIL_PLACEMENT
    )
    later = [make_scan(at=NOW + timedelta(days=n + 10)) for n in range(4)]

    signals = refilling.evaluate(
        make_context(scans=later, supply_chain_events=[placement])
    )
    assert SignalType.POST_SALE_SCAN_RESURGENCE in _types(signals)


def test_a_scan_inside_the_post_sale_grace_window_is_not_refilling_evidence():
    placement = make_supply_chain_event(
        at=NOW, event_type=SupplyChainEventType.RETAIL_PLACEMENT
    )
    soon = [make_scan(at=NOW + timedelta(hours=n)) for n in range(1, 5)]

    signals = refilling.evaluate(make_context(scans=soon, supply_chain_events=[placement]))
    assert SignalType.POST_SALE_SCAN_RESURGENCE not in _types(signals)


def test_dormancy_then_reactivation_produces_refilling_evidence():
    scans = [make_scan(at=NOW)] + [
        make_scan(at=NOW + timedelta(days=200 + n)) for n in range(3)
    ]
    signals = refilling.evaluate(make_context(scans=scans))

    assert SignalType.DORMANCY_REACTIVATION in _types(signals)


def test_a_single_scan_after_dormancy_is_not_enough():
    scans = [make_scan(at=NOW), make_scan(at=NOW + timedelta(days=200))]
    assert refilling.evaluate(make_context(scans=scans)) == []


def test_scan_outside_every_authorized_territory_produces_diversion_evidence():
    scans, coordinates = located_scans([(timedelta(0), MUMBAI)])
    context = make_context(
        scans=scans,
        scan_coordinates=coordinates,
        inside_territory={scans[0].id: False},
    )
    assert SignalType.TERRITORY_VIOLATION in _types(diversion.evaluate(context))


def test_scan_inside_an_authorized_territory_produces_nothing():
    scans, coordinates = located_scans([(timedelta(0), BENGALURU)])
    context = make_context(
        scans=scans,
        scan_coordinates=coordinates,
        inside_territory={scans[0].id: True},
    )
    assert diversion.evaluate(context) == []


def test_custody_with_an_unauthorized_participant_produces_channel_evidence():
    event = make_supply_chain_event(at=NOW, event_type=SupplyChainEventType.TRANSFER)
    context = make_context(
        supply_chain_events=[event], custodian_authorized={event.id: False}
    )
    assert SignalType.CHANNEL_VIOLATION in _types(diversion.evaluate(context))


def test_an_end_of_season_return_to_an_authorized_distributor_is_not_diversion():
    event = make_supply_chain_event(at=NOW, event_type=SupplyChainEventType.RETURN)
    context = make_context(
        supply_chain_events=[event], custodian_authorized={event.id: True}
    )
    assert diversion.evaluate(context) == []


def test_a_reallocation_between_authorized_retailers_is_not_diversion():
    event = make_supply_chain_event(at=NOW, event_type=SupplyChainEventType.REALLOCATION)
    context = make_context(
        supply_chain_events=[event], custodian_authorized={event.id: True}
    )
    assert diversion.evaluate(context) == []


def test_no_detector_ever_returns_a_boolean_verdict():
    scans, coordinates = located_scans(
        [(timedelta(0), BENGALURU), (timedelta(hours=1), MUMBAI)]
    )
    signals = cloning.evaluate(make_context(scans=scans, scan_coordinates=coordinates))

    for signal in signals:
        assert isinstance(signal.log_likelihood_ratio, float)
        assert signal.explanation
        assert len(signal.sources) > 0
