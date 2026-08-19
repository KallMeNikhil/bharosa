from __future__ import annotations

from datetime import timedelta

from app.domains.detection.context import DetectionContext
from app.domains.detection.signals import Signal, SignalType, SourceEvents
from app.domains.supply_chain import SupplyChainEventType

DETECTOR_ID = "refilling"
DETECTOR_VERSION = 1


def _retail_placement(context: DetectionContext):
    placements = [
        event
        for event in context.supply_chain_events
        if event.event_type is SupplyChainEventType.RETAIL_PLACEMENT
    ]
    if not placements:
        return None
    return max(placements, key=lambda event: event.occurred_at)


def _post_sale_resurgence(context: DetectionContext) -> list[Signal]:
    thresholds = context.thresholds
    placement = _retail_placement(context)
    if placement is None:
        return []

    grace_ends = placement.occurred_at + timedelta(hours=thresholds.post_sale_grace_hours)
    later_scans = [
        event for event in context.verification_events if event.occurred_at > grace_ends
    ]

    if len(later_scans) < thresholds.post_sale_scan_count:
        return []

    return [
        Signal(
            signal_type=SignalType.POST_SALE_SCAN_RESURGENCE,
            log_likelihood_ratio=thresholds.post_sale_resurgence_log_lr,
            explanation=(
                f"{len(later_scans)} scans occurred more than "
                f"{thresholds.post_sale_grace_hours} hours after this pack was placed "
                f"at retail. A container that has been sold and used should not keep "
                f"generating fresh verification activity."
            ),
            sources=SourceEvents(
                verification_event_ids=tuple(event.id for event in later_scans),
                supply_chain_event_ids=(placement.id,),
            ),
        )
    ]


def _dormancy_reactivation(context: DetectionContext) -> list[Signal]:
    thresholds = context.thresholds
    events = sorted(context.verification_events, key=lambda e: e.occurred_at)
    if len(events) < 2:
        return []

    dormancy = timedelta(days=thresholds.dormancy_days)
    signals: list[Signal] = []

    for index, (earlier, later) in enumerate(zip(events, events[1:], strict=False)):
        if later.occurred_at - earlier.occurred_at < dormancy:
            continue

        reactivation = events[index + 1 :]
        if len(reactivation) < thresholds.dormancy_reactivation_scan_count:
            continue

        gap_days = (later.occurred_at - earlier.occurred_at).days
        signals.append(
            Signal(
                signal_type=SignalType.DORMANCY_REACTIVATION,
                log_likelihood_ratio=thresholds.dormancy_reactivation_log_lr,
                explanation=(
                    f"This identity was silent for {gap_days} days and then produced "
                    f"{len(reactivation)} further scans. A reused container reentering "
                    f"circulation looks like this; so does a genuine pack found at the "
                    f"back of a shelf, which is why this signal is weak on its own."
                ),
                sources=SourceEvents(
                    verification_event_ids=(earlier.id, *[e.id for e in reactivation])
                ),
            )
        )

    return signals


def evaluate(context: DetectionContext) -> list[Signal]:
    return [*_post_sale_resurgence(context), *_dormancy_reactivation(context)]
