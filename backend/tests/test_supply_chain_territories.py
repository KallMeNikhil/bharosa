import pytest

from app.domains.supply_chain import InvalidTerritoryGeometryError, territory_contains_point
from tests.identity_fixtures import make_manufacturer
from tests.supply_chain_fixtures import INVALID_BOWTIE_WKT, VALID_SQUARE_WKT, make_territory


def test_define_territory_with_valid_multipolygon_succeeds(supply_chain_db_session):
    manufacturer = make_manufacturer(supply_chain_db_session, name="Territory Test Mfr")
    supply_chain_db_session.commit()

    territory = make_territory(supply_chain_db_session, manufacturer.id)
    supply_chain_db_session.commit()

    assert territory.id is not None
    assert territory.manufacturer_id == manufacturer.id


def test_define_territory_with_invalid_geometry_is_rejected(supply_chain_db_session):
    manufacturer = make_manufacturer(supply_chain_db_session, name="Invalid Geometry Mfr")
    supply_chain_db_session.commit()

    with pytest.raises(InvalidTerritoryGeometryError):
        make_territory(
            supply_chain_db_session,
            manufacturer.id,
            territory_ref="BAD-GEOM",
            boundary_wkt=INVALID_BOWTIE_WKT,
        )


def test_territory_ref_is_unique_per_manufacturer(supply_chain_db_session):
    from sqlalchemy.exc import IntegrityError

    manufacturer = make_manufacturer(supply_chain_db_session, name="Unique Territory Mfr")
    supply_chain_db_session.commit()

    make_territory(supply_chain_db_session, manufacturer.id, territory_ref="DUP-TERR")
    supply_chain_db_session.commit()

    try:
        make_territory(supply_chain_db_session, manufacturer.id, territory_ref="DUP-TERR")
        raised = False
    except IntegrityError:
        raised = True
        supply_chain_db_session.rollback()
    assert raised


def test_territory_contains_point_true_for_interior_point(supply_chain_db_session):
    manufacturer = make_manufacturer(supply_chain_db_session, name="PIP True Mfr")
    supply_chain_db_session.commit()
    territory = make_territory(
        supply_chain_db_session, manufacturer.id, boundary_wkt=VALID_SQUARE_WKT
    )
    supply_chain_db_session.commit()

    assert (
        territory_contains_point(
            supply_chain_db_session, territory=territory, longitude=0.5, latitude=0.5
        )
        is True
    )


def test_territory_contains_point_false_for_exterior_point(supply_chain_db_session):
    manufacturer = make_manufacturer(supply_chain_db_session, name="PIP False Mfr")
    supply_chain_db_session.commit()
    territory = make_territory(
        supply_chain_db_session, manufacturer.id, boundary_wkt=VALID_SQUARE_WKT
    )
    supply_chain_db_session.commit()

    assert (
        territory_contains_point(
            supply_chain_db_session, territory=territory, longitude=5.0, latitude=5.0
        )
        is False
    )
