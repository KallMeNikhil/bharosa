import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.domains.identity import (
    Batch,
    LifecycleState,
    Manufacturer,
    ManufacturerKey,
    Product,
    ProductIdentity,
)
from app.domains.identity.signer import DevelopmentOnlySigner
from tests.identity_fixtures import (
    make_batch,
    make_key,
    make_manufacturer,
    make_product,
    make_reserved_identity,
)


def test_valid_manufacturer(identity_db_session):
    m = make_manufacturer(identity_db_session)
    identity_db_session.commit()
    assert identity_db_session.get(Manufacturer, m.id) is not None


def test_valid_product(identity_db_session):
    m = make_manufacturer(identity_db_session)
    p = make_product(identity_db_session, m)
    identity_db_session.commit()
    fetched = identity_db_session.get(Product, p.id)
    assert fetched.manufacturer_id == m.id


def test_valid_batch(identity_db_session):
    m = make_manufacturer(identity_db_session)
    p = make_product(identity_db_session, m)
    b = make_batch(identity_db_session, p)
    identity_db_session.commit()
    fetched = identity_db_session.get(Batch, b.id)
    assert fetched.product_id == p.id


def test_valid_identity_reservation(identity_db_session):
    m = make_manufacturer(identity_db_session)
    p = make_product(identity_db_session, m)
    b = make_batch(identity_db_session, p)
    identity = make_reserved_identity(identity_db_session, b)
    identity_db_session.commit()
    fetched = identity_db_session.get(ProductIdentity, identity.id)
    assert fetched.lifecycle_state == LifecycleState.RESERVED
    assert fetched.batch_id == b.id


def test_product_foreign_key_integrity(identity_db_session):
    bogus_manufacturer_id = uuid.uuid4()
    product = Product(
        manufacturer_id=bogus_manufacturer_id, product_ref="X", name="X"
    )
    identity_db_session.add(product)
    with pytest.raises(IntegrityError):
        identity_db_session.commit()


def test_batch_foreign_key_integrity(identity_db_session):
    bogus_product_id = uuid.uuid4()
    batch = Batch(product_id=bogus_product_id, batch_ref="X")
    identity_db_session.add(batch)
    with pytest.raises(IntegrityError):
        identity_db_session.commit()


def test_identity_serial_uniqueness(identity_db_session):
    m = make_manufacturer(identity_db_session)
    p = make_product(identity_db_session, m)
    b = make_batch(identity_db_session, p)
    make_reserved_identity(identity_db_session, b)
    identity_db_session.commit()

    dup = ProductIdentity(batch_id=b.id)
    identity_db_session.add(dup)
    with pytest.raises(IntegrityError):
        identity_db_session.commit()


def test_product_ref_unique_per_manufacturer(identity_db_session):
    m = make_manufacturer(identity_db_session)
    make_product(identity_db_session, m, product_ref="SAME-REF")
    identity_db_session.commit()

    dup = Product(manufacturer_id=m.id, product_ref="SAME-REF", name="Other")
    identity_db_session.add(dup)
    with pytest.raises(IntegrityError):
        identity_db_session.commit()


def test_batch_ref_unique_per_product(identity_db_session):
    m = make_manufacturer(identity_db_session)
    p = make_product(identity_db_session, m)
    make_batch(identity_db_session, p, batch_ref="SAME-BATCH")
    identity_db_session.commit()

    dup = Batch(product_id=p.id, batch_ref="SAME-BATCH")
    identity_db_session.add(dup)
    with pytest.raises(IntegrityError):
        identity_db_session.commit()


def test_manufacturer_key_version_unique_per_manufacturer(identity_db_session):
    m = make_manufacturer(identity_db_session)
    signer = DevelopmentOnlySigner()
    make_key(identity_db_session, m, signer, key_version=1)
    identity_db_session.commit()

    dup = ManufacturerKey(
        manufacturer_id=m.id, key_version=1, public_key=b"x" * 32, status="ACTIVE"
    )
    identity_db_session.add(dup)
    with pytest.raises(IntegrityError):
        identity_db_session.commit()


def test_manufacturer_key_has_no_private_key_columns():
    columns = {c.name for c in ManufacturerKey.__table__.columns}
    forbidden_substrings = ["private", "secret", "seed", "scalar", "pem"]
    for column_name in columns:
        lowered = column_name.lower()
        for forbidden in forbidden_substrings:
            assert forbidden not in lowered, (
                f"ManufacturerKey column {column_name!r} looks like it might "
                f"hold private-key material (matched {forbidden!r})"
            )
    assert columns == {
        "id",
        "manufacturer_id",
        "key_version",
        "public_key",
        "status",
        "valid_from",
        "valid_to",
        "created_at",
    }
