from __future__ import annotations

from dataclasses import dataclass

from app.domains.simulation.models import ScenarioType

DEFAULT_IDENTITY_COUNT = 6
MIN_IDENTITY_COUNT = 1
MAX_IDENTITY_COUNT = 30

INJECTION_FRACTION_DENOMINATOR = 3


@dataclass(frozen=True)
class ScenarioDescription:
    scenario_type: ScenarioType
    label: str
    summary: str
    injects_fraud: bool


SCENARIO_CATALOGUE: dict[ScenarioType, ScenarioDescription] = {
    ScenarioType.LEGITIMATE_BASELINE: ScenarioDescription(
        scenario_type=ScenarioType.LEGITIMATE_BASELINE,
        label="Legitimate baseline",
        summary=(
            "A fully legitimate supply chain: every identity is signed, "
            "activated, moved through a normal custody path and scanned "
            "normally. Exercises true-negative behaviour."
        ),
        injects_fraud=False,
    ),
    ScenarioType.FULL_COUNTERFEIT: ScenarioDescription(
        scenario_type=ScenarioType.FULL_COUNTERFEIT,
        label="Full counterfeit",
        summary=(
            "A minority of identities are scanned while still unsigned and "
            "unactivated, the way a counterfeiter guessing at an unissued "
            "identity slot would be. Expects SIGNATURE_INVALID / "
            "PRE_ACTIVATION_SCAN evidence."
        ),
        injects_fraud=True,
    ),
    ScenarioType.CODE_CLONING: ScenarioDescription(
        scenario_type=ScenarioType.CODE_CLONING,
        label="Code cloning",
        summary=(
            "A minority of identities are scanned from geographically distant "
            "locations within an implausible time window, as a cloned code "
            "circulating on multiple physical objects would be. Expects "
            "IMPOSSIBLE_TRAVEL / GEOGRAPHIC_SPREAD evidence."
        ),
        injects_fraud=True,
    ),
    ScenarioType.REFILLING: ScenarioDescription(
        scenario_type=ScenarioType.REFILLING,
        label="Refilling / reuse",
        summary=(
            "A minority of identities generate a burst of scans long after "
            "their retail placement and post-sale grace period, as a reused "
            "container reentering circulation would. Expects "
            "POST_SALE_SCAN_RESURGENCE evidence."
        ),
        injects_fraud=True,
    ),
    ScenarioType.DIVERSION: ScenarioDescription(
        scenario_type=ScenarioType.DIVERSION,
        label="Diversion / grey market",
        summary=(
            "A minority of identities are transferred to a distributor "
            "holding no channel authorization, as diverted stock would be. "
            "Expects CHANNEL_VIOLATION evidence."
        ),
        injects_fraud=True,
    ),
    ScenarioType.COMBINED_MULTI_SIGNAL: ScenarioDescription(
        scenario_type=ScenarioType.COMBINED_MULTI_SIGNAL,
        label="Combined multi-signal",
        summary=(
            "A minority of identities receive both the cloning and diversion "
            "treatment together, to exercise cross-family evidence "
            "correlation, risk escalation and incident opening."
        ),
        injects_fraud=True,
    ),
    ScenarioType.BENIGN_ANOMALY: ScenarioDescription(
        scenario_type=ScenarioType.BENIGN_ANOMALY,
        label="Benign but unusual",
        summary=(
            "Every identity is legitimate but exhibits unusual, non-fraudulent "
            "patterns: returns, reallocation between a distributor's own "
            "retailers, and repeated same-territory scans below every "
            "detector threshold. Exists to measure false positives, not to "
            "generate them."
        ),
        injects_fraud=False,
    ),
}
