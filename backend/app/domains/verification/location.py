from __future__ import annotations

import math
from dataclasses import dataclass

COARSE_GRID_DEGREES = 0.1

MIN_LATITUDE = -90.0
MAX_LATITUDE = 90.0
MIN_LONGITUDE = -180.0
MAX_LONGITUDE = 180.0

EARTH_RADIUS_METRES = 6_371_000.0


class InvalidCoordinateError(ValueError):
    pass


@dataclass(frozen=True)
class ScanLocation:
    longitude: float
    latitude: float
    reported_accuracy_m: int | None = None

    def __post_init__(self) -> None:
        if not MIN_LATITUDE <= self.latitude <= MAX_LATITUDE:
            raise InvalidCoordinateError(f"latitude {self.latitude!r} is out of range")
        if not MIN_LONGITUDE <= self.longitude <= MAX_LONGITUDE:
            raise InvalidCoordinateError(f"longitude {self.longitude!r} is out of range")
        if self.reported_accuracy_m is not None and self.reported_accuracy_m < 0:
            raise InvalidCoordinateError("reported_accuracy_m cannot be negative")

    @property
    def point_wkt(self) -> str:
        return f"POINT({self.longitude} {self.latitude})"

    @property
    def coarse_cell(self) -> str:
        return coarse_cell(self.longitude, self.latitude)


def coarse_cell(longitude: float, latitude: float) -> str:
    lon_index = math.floor(longitude / COARSE_GRID_DEGREES)
    lat_index = math.floor(latitude / COARSE_GRID_DEGREES)
    return f"{lat_index}:{lon_index}"


def great_circle_metres(
    longitude_a: float, latitude_a: float, longitude_b: float, latitude_b: float
) -> float:
    phi_a = math.radians(latitude_a)
    phi_b = math.radians(latitude_b)
    delta_phi = math.radians(latitude_b - latitude_a)
    delta_lambda = math.radians(longitude_b - longitude_a)

    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi_a) * math.cos(phi_b) * math.sin(delta_lambda / 2) ** 2
    )
    return 2 * EARTH_RADIUS_METRES * math.asin(math.sqrt(a))
