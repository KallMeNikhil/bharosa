from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from app.domains.detection.context import DetectionContext
from app.domains.detection.detectors import cloning, counterfeit, diversion, refilling
from app.domains.detection.signals import Signal


@dataclass(frozen=True)
class RegisteredDetector:
    detector_id: str
    detector_version: int
    evaluate: Callable[[DetectionContext], list[Signal]]


DETECTOR_REGISTRY: tuple[RegisteredDetector, ...] = (
    RegisteredDetector(
        detector_id=counterfeit.DETECTOR_ID,
        detector_version=counterfeit.DETECTOR_VERSION,
        evaluate=counterfeit.evaluate,
    ),
    RegisteredDetector(
        detector_id=cloning.DETECTOR_ID,
        detector_version=cloning.DETECTOR_VERSION,
        evaluate=cloning.evaluate,
    ),
    RegisteredDetector(
        detector_id=refilling.DETECTOR_ID,
        detector_version=refilling.DETECTOR_VERSION,
        evaluate=refilling.evaluate,
    ),
    RegisteredDetector(
        detector_id=diversion.DETECTOR_ID,
        detector_version=diversion.DETECTOR_VERSION,
        evaluate=diversion.evaluate,
    ),
)

__all__ = ["DETECTOR_REGISTRY", "RegisteredDetector"]
