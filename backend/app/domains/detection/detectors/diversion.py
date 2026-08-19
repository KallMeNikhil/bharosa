from __future__ import annotations

from app.domains.detection.context import DetectionContext
from app.domains.detection.signals import Signal, SignalType, SourceEvents

DETECTOR_ID = "diversion"
DETECTOR_VERSION = 1


def _territory_violation(context: DetectionContext) -> list[Signal]:
    thresholds = context.thresholds
    outside = [
        event
        for event in context.located_verification_events
        if context.scan_inside_authorized_territory.get(event.id) is False
    ]
    if not outside:
        return []

    return [
        Signal(
            signal_type=SignalType.TERRITORY_VIOLATION,
            log_likelihood_ratio=thresholds.territory_violation_log_lr,
            explanation=(
                f"{len(outside)} scan(s) fell outside every territory this "
                f"manufacturer has authorized for distribution. Territory is a "
                f"commercial boundary rather than a physical one, so legitimate "
                f"cross-territory sourcing produces this signal too."
            ),
            sources=SourceEvents(
                verification_event_ids=tuple(event.id for event in outside)
            ),
        )
    ]


def _channel_violation(context: DetectionContext) -> list[Signal]:
    thresholds = context.thresholds
    unauthorized = [
        event
        for event in context.supply_chain_events
        if context.custodian_authorized_at_event.get(event.id) is False
    ]
    if not unauthorized:
        return []

    return [
        Signal(
            signal_type=SignalType.CHANNEL_VIOLATION,
            log_likelihood_ratio=thresholds.channel_violation_log_lr,
            explanation=(
                f"{len(unauthorized)} custody event(s) placed this pack with a "
                f"participant holding no active channel authorization from this "
                f"manufacturer at the time the movement was recorded."
            ),
            sources=SourceEvents(
                supply_chain_event_ids=tuple(event.id for event in unauthorized)
            ),
        )
    ]


def evaluate(context: DetectionContext) -> list[Signal]:
    return [*_territory_violation(context), *_channel_violation(context)]
