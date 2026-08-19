from __future__ import annotations

from app.domains.detection.context import DetectionContext
from app.domains.detection.signals import Signal, SignalType, SourceEvents
from app.domains.identity import LifecycleState

DETECTOR_ID = "counterfeit"
DETECTOR_VERSION = 1

UNTRUSTED_KEY_STATUSES = frozenset({"REVOKED", "COMPROMISED"})


def evaluate(context: DetectionContext) -> list[Signal]:
    signals: list[Signal] = []
    thresholds = context.thresholds

    invalid = [event for event in context.verification_events if not event.signature_valid]
    if invalid:
        signals.append(
            Signal(
                signal_type=SignalType.SIGNATURE_INVALID,
                log_likelihood_ratio=thresholds.signature_invalid_log_lr,
                explanation=(
                    f"{len(invalid)} scan(s) presented a payload whose signature did "
                    f"not verify against the key version recorded for this identity."
                ),
                sources=SourceEvents(
                    verification_event_ids=tuple(event.id for event in invalid)
                ),
            )
        )

    untrusted = [
        event
        for event in context.verification_events
        if event.key_status_at_scan in UNTRUSTED_KEY_STATUSES
    ]
    if untrusted:
        statuses = sorted({event.key_status_at_scan for event in untrusted})
        signals.append(
            Signal(
                signal_type=SignalType.UNTRUSTED_KEY_AT_SCAN,
                log_likelihood_ratio=thresholds.untrusted_key_log_lr,
                explanation=(
                    f"{len(untrusted)} scan(s) resolved to a signing key whose status "
                    f"was {', '.join(statuses)} at the time of the scan."
                ),
                sources=SourceEvents(
                    verification_event_ids=tuple(event.id for event in untrusted)
                ),
            )
        )

    pre_activation = [
        event
        for event in context.verification_events
        if event.lifecycle_state_at_scan != LifecycleState.ACTIVATED.value
    ]
    if pre_activation:
        signals.append(
            Signal(
                signal_type=SignalType.PRE_ACTIVATION_SCAN,
                log_likelihood_ratio=thresholds.pre_activation_scan_log_lr,
                explanation=(
                    f"{len(pre_activation)} scan(s) occurred while this identity had "
                    f"not reached the activated lifecycle state, so no legitimately "
                    f"distributed pack should have been carrying it yet."
                ),
                sources=SourceEvents(
                    verification_event_ids=tuple(event.id for event in pre_activation)
                ),
            )
        )

    return signals
