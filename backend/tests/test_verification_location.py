import pytest

from app.domains.verification import (
    InvalidCoordinateError,
    ScanLocation,
    coarse_cell,
    great_circle_metres,
)


def test_nearby_points_share_a_coarse_cell():
    assert coarse_cell(77.5946, 12.9716) == coarse_cell(77.5951, 12.9720)


def test_distant_points_do_not_share_a_coarse_cell():
    assert coarse_cell(77.5946, 12.9716) != coarse_cell(72.8777, 19.0760)


def test_coarse_cell_discards_precision_below_the_grid():
    assert coarse_cell(77.59461234, 12.97161234) == coarse_cell(77.5, 12.9)


def test_coarse_cell_is_stable_across_the_meridian_sign():
    assert coarse_cell(-0.05, 0.05) != coarse_cell(0.05, 0.05)


def test_scan_location_exposes_wkt_and_coarse_cell():
    location = ScanLocation(longitude=77.5946, latitude=12.9716)
    assert location.point_wkt == "POINT(77.5946 12.9716)"
    assert location.coarse_cell == coarse_cell(77.5946, 12.9716)


@pytest.mark.parametrize(
    "longitude,latitude",
    [(181.0, 0.0), (-181.0, 0.0), (0.0, 91.0), (0.0, -91.0)],
)
def test_out_of_range_coordinates_are_rejected(longitude, latitude):
    with pytest.raises(InvalidCoordinateError):
        ScanLocation(longitude=longitude, latitude=latitude)


def test_negative_accuracy_is_rejected():
    with pytest.raises(InvalidCoordinateError):
        ScanLocation(longitude=0.0, latitude=0.0, reported_accuracy_m=-1)


def test_great_circle_distance_bengaluru_to_mumbai():
    metres = great_circle_metres(77.5946, 12.9716, 72.8777, 19.0760)
    assert 830_000 < metres < 860_000


def test_great_circle_distance_is_zero_for_identical_points():
    assert great_circle_metres(77.5946, 12.9716, 77.5946, 12.9716) == pytest.approx(0.0)
