from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass, field


class FraudFamily(str, enum.Enum):
    FULL_COUNTERFEIT = "FULL_COUNTERFEIT"
    CODE_CLONING = "CODE_CLONING"
    REFILLING = "REFILLING"
    DIVERSION = "DIVERSION"


class SignalType(str, enum.Enum):
    SIGNATURE_INVALID = "SIGNATURE_INVALID"
    UNTRUSTED_KEY_AT_SCAN = "UNTRUSTED_KEY_AT_SCAN"
    PRE_ACTIVATION_SCAN = "PRE_ACTIVATION_SCAN"

    IMPOSSIBLE_TRAVEL = "IMPOSSIBLE_TRAVEL"
    GEOGRAPHIC_SPREAD = "GEOGRAPHIC_SPREAD"
    SCAN_VELOCITY = "SCAN_VELOCITY"

    POST_SALE_SCAN_RESURGENCE = "POST_SALE_SCAN_RESURGENCE"
    DORMANCY_REACTIVATION = "DORMANCY_REACTIVATION"

    TERRITORY_VIOLATION = "TERRITORY_VIOLATION"
    CHANNEL_VIOLATION = "CHANNEL_VIOLATION"


FAMILY_FOR_SIGNAL: dict[SignalType, FraudFamily] = {
    SignalType.SIGNATURE_INVALID: FraudFamily.FULL_COUNTERFEIT,
    SignalType.UNTRUSTED_KEY_AT_SCAN: FraudFamily.FULL_COUNTERFEIT,
    SignalType.PRE_ACTIVATION_SCAN: FraudFamily.FULL_COUNTERFEIT,
    SignalType.IMPOSSIBLE_TRAVEL: FraudFamily.CODE_CLONING,
    SignalType.GEOGRAPHIC_SPREAD: FraudFamily.CODE_CLONING,
    SignalType.SCAN_VELOCITY: FraudFamily.CODE_CLONING,
    SignalType.POST_SALE_SCAN_RESURGENCE: FraudFamily.REFILLING,
    SignalType.DORMANCY_REACTIVATION: FraudFamily.REFILLING,
    SignalType.TERRITORY_VIOLATION: FraudFamily.DIVERSION,
    SignalType.CHANNEL_VIOLATION: FraudFamily.DIVERSION,
}


@dataclass(frozen=True)
class SourceEvents:
    verification_event_ids: tuple[uuid.UUID, ...] = ()
    supply_chain_event_ids: tuple[uuid.UUID, ...] = ()
    identity_issuance_event_ids: tuple[uuid.UUID, ...] = ()

    def __bool__(self) -> bool:
        return bool(
            self.verification_event_ids
            or self.supply_chain_event_ids
            or self.identity_issuance_event_ids
        )

    def __len__(self) -> int:
        return (
            len(self.verification_event_ids)
            + len(self.supply_chain_event_ids)
            + len(self.identity_issuance_event_ids)
        )


class UncitedSignalError(ValueError):
    def __init__(self, signal_type: SignalType) -> None:
        self.signal_type = signal_type
        super().__init__(
            f"Signal {signal_type.value} cites no source events. Detection "
            f"evidence can never exist without the specific events it was "
            f"derived from."
        )


@dataclass(frozen=True)
class Signal:
    """One detector observation.

    `log_likelihood_ratio` is the natural log of "how many times more likely
    this observation is under fraud than under legitimate use". Logs are what
    the correlation layer accumulates additively, so detectors emit them
    directly rather than a score that would have to be reinterpreted later.
    A detector never emits a verdict, and never emits a boolean.
    """

    signal_type: SignalType
    log_likelihood_ratio: float
    explanation: str
    sources: SourceEvents = field(default_factory=SourceEvents)

    def __post_init__(self) -> None:
        if not self.sources:
            raise UncitedSignalError(self.signal_type)

    @property
    def family(self) -> FraudFamily:
        return FAMILY_FOR_SIGNAL[self.signal_type]
