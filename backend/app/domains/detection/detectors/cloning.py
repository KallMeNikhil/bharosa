from __future__ import annotations

import math

from app.domains.detection.context import DetectionContext
from app.domains.detection.signals import Signal, SignalType, SourceEvents
from app.domains.verification import great_circle_metres

DETECTOR_ID = "cloning"
DETECTOR_VERSION = 1

SECONDS_PER_HOUR = 3600.0


def _implied_speed_kmh(metres: float, seconds: float) -> float:
    if seconds <= 0:
        return math.inf
    return (metres / 1000.0) / (seconds / SECONDS_PER_HOUR)


def _impossible_travel(context: DetectionContext) -> list[Signal]:
    thresholds = context.thresholds
    events = sorted(context.located_verification_events, key=lambda e: e.occurred_at)
    signals: list[Signal] = []

    for earlier, later in zip(events, events[1:], strict=False):
        earlier_lon, earlier_lat = context.scan_coordinates[earlier.id]
        later_lon, later_lat = context.scan_coordinates[later.id]
        metres = great_circle_metres(earlier_lon, earlier_lat, later_lon, later_lat)

        slack = thresholds.location_accuracy_slack_m + (earlier.reported_accuracy_m or 0)
        slack += later.reported_accuracy_m or 0
        effective_metres = metres - slack

        if effective_metres < thresholds.impossible_travel_min_separation_m:
            continue

        seconds = (later.occurred_at - earlier.occurred_at).total_seconds()
        speed = _implied_speed_kmh(effective_metres, seconds)
        if speed <= thresholds.max_plausible_speed_kmh:
            continue

        excess = speed / thresholds.max_plausible_speed_kmh
        signals.append(
            Signal(
                signal_type=SignalType.IMPOSSIBLE_TRAVEL,
                log_likelihood_ratio=thresholds.impossible_travel_log_lr * min(excess, 3.0),
                explanation=(
                    f"Two scans {effective_metres / 1000:.0f} km apart were "
                    f"{seconds / SECONDS_PER_HOUR:.1f} hours apart, implying "
                    f"{speed:.0f} km/h of travel for a single physical pack against a "
                    f"plausible maximum of {thresholds.max_plausible_speed_kmh:.0f} km/h."
                ),
                sources=SourceEvents(verification_event_ids=(earlier.id, later.id)),
            )
        )

    return signals


def _geographic_spread(context: DetectionContext) -> list[Signal]:
    thresholds = context.thresholds
    located = context.located_verification_events
    cells = {event.coarse_cell for event in located if event.coarse_cell}

    if len(cells) < thresholds.geographic_spread_cell_count:
        return []

    return [
        Signal(
            signal_type=SignalType.GEOGRAPHIC_SPREAD,
            log_likelihood_ratio=thresholds.geographic_spread_log_lr,
            explanation=(
                f"Scans of this identity fall in {len(cells)} distinct locality cells, "
                f"against a threshold of {thresholds.geographic_spread_cell_count} for "
                f"a single pack's expected distribution neighbourhood."
            ),
            sources=SourceEvents(
                verification_event_ids=tuple(event.id for event in located)
            ),
        )
    ]


def _scan_velocity(context: DetectionContext) -> list[Signal]:
    thresholds = context.thresholds
    events = sorted(context.verification_events, key=lambda e: e.occurred_at)

    if len(events) < thresholds.scan_velocity_min_scans:
        return []

    span_days = (events[-1].occurred_at - events[0].occurred_at).total_seconds() / 86_400.0
    if span_days <= 0:
        span_days = 1.0 / 24.0

    rate = len(events) / span_days
    if rate <= thresholds.scan_velocity_per_day:
        return []

    return [
        Signal(
            signal_type=SignalType.SCAN_VELOCITY,
            log_likelihood_ratio=thresholds.scan_velocity_log_lr,
            explanation=(
                f"{len(events)} scans over {span_days:.1f} days is {rate:.1f} scans per "
                f"day, above the {thresholds.scan_velocity_per_day:.0f} per day expected "
                f"even allowing for repeat checks and retailer inventory scanning."
            ),
            sources=SourceEvents(verification_event_ids=tuple(event.id for event in events)),
        )
    ]


def evaluate(context: DetectionContext) -> list[Signal]:
    return [
        *_impossible_travel(context),
        *_geographic_spread(context),
        *_scan_velocity(context),
    ]
