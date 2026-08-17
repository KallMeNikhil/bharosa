from app.domains.supply_chain import ParticipantRole, register_participant
from tests.identity_fixtures import FULLY_AUTHORIZED_TEST_ACTOR, make_manufacturer
from tests.supply_chain_fixtures import make_participant


def test_register_participant_succeeds(supply_chain_db_session):
    manufacturer = make_manufacturer(supply_chain_db_session, name="Participant Test Mfr")
    supply_chain_db_session.commit()

    participant = register_participant(
        supply_chain_db_session,
        manufacturer_id=manufacturer.id,
        participant_ref="DEPOT-A",
        name="Depot A",
        role=ParticipantRole.DEPOT,
        actor=FULLY_AUTHORIZED_TEST_ACTOR,
    )
    supply_chain_db_session.commit()

    assert participant.id is not None
    assert participant.manufacturer_id == manufacturer.id
    assert participant.role == ParticipantRole.DEPOT


def test_all_three_participant_roles_are_representable(supply_chain_db_session):
    manufacturer = make_manufacturer(supply_chain_db_session, name="Role Test Mfr")
    supply_chain_db_session.commit()

    depot = make_participant(
        supply_chain_db_session, manufacturer.id, participant_ref="D1", role=ParticipantRole.DEPOT
    )
    distributor = make_participant(
        supply_chain_db_session,
        manufacturer.id,
        participant_ref="DI1",
        role=ParticipantRole.DISTRIBUTOR,
    )
    retailer = make_participant(
        supply_chain_db_session,
        manufacturer.id,
        participant_ref="R1",
        role=ParticipantRole.RETAILER,
    )
    supply_chain_db_session.commit()

    assert depot.role == ParticipantRole.DEPOT
    assert distributor.role == ParticipantRole.DISTRIBUTOR
    assert retailer.role == ParticipantRole.RETAILER


def test_participant_ref_is_unique_per_manufacturer(supply_chain_db_session):
    from sqlalchemy.exc import IntegrityError

    manufacturer = make_manufacturer(supply_chain_db_session, name="Unique Ref Mfr")
    supply_chain_db_session.commit()

    make_participant(supply_chain_db_session, manufacturer.id, participant_ref="DUP-REF")
    supply_chain_db_session.commit()

    try:
        make_participant(supply_chain_db_session, manufacturer.id, participant_ref="DUP-REF")
        raised = False
    except IntegrityError:
        raised = True
        supply_chain_db_session.rollback()
    assert raised


def test_same_participant_ref_allowed_across_different_manufacturers(supply_chain_db_session):
    manufacturer_a = make_manufacturer(supply_chain_db_session, name="Cross Ref Mfr A")
    manufacturer_b = make_manufacturer(supply_chain_db_session, name="Cross Ref Mfr B")
    supply_chain_db_session.commit()

    make_participant(supply_chain_db_session, manufacturer_a.id, participant_ref="SHARED-REF")
    make_participant(supply_chain_db_session, manufacturer_b.id, participant_ref="SHARED-REF")
    supply_chain_db_session.commit()
