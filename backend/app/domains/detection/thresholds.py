from __future__ import annotations

from dataclasses import dataclass

"""Prototype-stage detector parameters.

None of these numbers are calibrated. They are starting points chosen to be
obviously wrong in the safe direction -- generous enough that ordinary
behaviour does not generate evidence -- and every one of them is expected to
move once the simulation milestone can measure detector performance against
known ground truth.

They are parameters, never architecture. No detector may hardcode any of
them, and no downstream consumer may treat a value here as settled.
"""


@dataclass(frozen=True)
class DetectorThresholds:
    analysis_window_days: int = 90

    max_plausible_speed_kmh: float = 120.0
    impossible_travel_min_separation_m: float = 25_000.0
    location_accuracy_slack_m: float = 5_000.0

    geographic_spread_cell_count: int = 4
    scan_velocity_per_day: float = 12.0
    scan_velocity_min_scans: int = 8

    post_sale_grace_hours: int = 72
    post_sale_scan_count: int = 4

    dormancy_days: int = 120
    dormancy_reactivation_scan_count: int = 3

    impossible_travel_log_lr: float = 2.3
    geographic_spread_log_lr: float = 1.1
    scan_velocity_log_lr: float = 0.7
    signature_invalid_log_lr: float = 3.9
    untrusted_key_log_lr: float = 2.3
    pre_activation_scan_log_lr: float = 1.6
    post_sale_resurgence_log_lr: float = 1.4
    dormancy_reactivation_log_lr: float = 1.1
    territory_violation_log_lr: float = 1.1
    channel_violation_log_lr: float = 1.4


DEFAULT_THRESHOLDS = DetectorThresholds()
