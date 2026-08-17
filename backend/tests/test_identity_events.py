import pytest

from app.domains.identity import (
    ActorContext,
    Capability,
    IdentityEventType,
    IllegalLifecycleTransitionError,
    LifecycleState,
    transition_identity,
)
from tests.identity_fixtures import (
    FULLY_AUTHORIZED_TEST_ACTOR,
    full_signed_fixture,
)


def test_reservation_creates_an_event(identity_db_session):
    fx = full_signed_fixture(identity_db_session)
    identity = fx["identity"]
    events = sorted(identity.events, key=lambda e: e.sequence)
    assert events[0].event_type == IdentityEventType.RESERVED
    assert events[0].previous_state is None
    assert events[0].new_state == LifecycleState.RESERVED


def test_transition_creates_event_with_previous_and_new_state(identity_db_session):
    fx = full_signed_fixture(identity_db_session)
    identity = fx["identity"]
    transition_identity(
        identity_db_session,
        identity=identity,
        new_state=LifecycleState.PRINTED,
        actor=FULLY_AUTHORIZED_TEST_ACTOR,
    )
    identity_db_session.commit()

    events = sorted(identity.events, key=lambda e: e.sequence)
    latest = events[-1]
    assert latest.previous_state == LifecycleState.SIGNED
    assert latest.new_state == LifecycleState.PRINTED
    assert latest.event_type == IdentityEventType.PRINTED


def test_full_lifecycle_produces_one_event_per_transition(identity_db_session):
    fx = full_signed_fixture(identity_db_session)
    identity = fx["identity"]
    for state in [
        LifecycleState.PRINTED,
        LifecycleState.PRINT_VERIFIED,
        LifecycleState.RECONCILED,
        LifecycleState.ACTIVATED,
    ]:
        transition_identity(
            identity_db_session,
            identity=identity,
            new_state=state,
            actor=FULLY_AUTHORIZED_TEST_ACTOR,
        )
    identity_db_session.commit()

    assert len(identity.events) == 6
    sequences = [e.sequence for e in sorted(identity.events, key=lambda e: e.sequence)]
    assert sequences == list(range(1, 7))


def test_event_sequence_and_history_is_deterministic_and_ordered(identity_db_session):
    fx = full_signed_fixture(identity_db_session)
    identity = fx["identity"]
    transition_identity(
        identity_db_session,
        identity=identity,
        new_state=LifecycleState.PRINTED,
        actor=FULLY_AUTHORIZED_TEST_ACTOR,
    )
    transition_identity(
        identity_db_session,
        identity=identity,
        new_state=LifecycleState.PRINT_VERIFIED,
        actor=FULLY_AUTHORIZED_TEST_ACTOR,
    )
    identity_db_session.commit()

    history_states = [e.new_state for e in sorted(identity.events, key=lambda e: e.sequence)]
    assert history_states == [
        LifecycleState.RESERVED,
        LifecycleState.SIGNED,
        LifecycleState.PRINTED,
        LifecycleState.PRINT_VERIFIED,
    ]


def test_illegal_transition_does_not_create_an_event(identity_db_session):
    fx = full_signed_fixture(identity_db_session)
    identity = fx["identity"]
    event_count_before = len(identity.events)
    with pytest.raises(IllegalLifecycleTransitionError):
        transition_identity(
            identity_db_session,
            identity=identity,
            new_state=LifecycleState.ACTIVATED,
            actor=FULLY_AUTHORIZED_TEST_ACTOR,
        )
    assert len(identity.events) == event_count_before


def test_state_and_event_commit_atomically(identity_db_session):
    fx = full_signed_fixture(identity_db_session)
    identity = fx["identity"]
    transition_identity(
        identity_db_session,
        identity=identity,
        new_state=LifecycleState.PRINTED,
        actor=FULLY_AUTHORIZED_TEST_ACTOR,
    )
    identity_db_session.commit()

    latest_event = sorted(identity.events, key=lambda e: e.sequence)[-1]
    assert identity.lifecycle_state == latest_event.new_state


def test_identity_issuance_event_has_no_orm_update_or_delete_helper_used_by_domain(
    identity_db_session,
):
    import app.domains.identity as identity_pkg

    forbidden_name_fragments = ["update_event", "delete_event", "edit_event"]
    public_names = set(identity_pkg.__all__)
    for fragment in forbidden_name_fragments:
        assert not any(fragment in name.lower() for name in public_names)


def test_event_records_actor_and_metadata_when_provided(identity_db_session):
    fx = full_signed_fixture(identity_db_session)
    identity = fx["identity"]
    transition_identity(
        identity_db_session,
        identity=identity,
        new_state=LifecycleState.PRINTED,
        actor=ActorContext(
            actor_id="synthetic-test-operator",
            capabilities=frozenset({Capability.AUTHORIZE_PRINT}),
        ),
        event_metadata="printed via synthetic test fixture",
    )
    identity_db_session.commit()

    latest = sorted(identity.events, key=lambda e: e.sequence)[-1]
    assert latest.actor == "synthetic-test-operator"
    assert latest.event_metadata == "printed via synthetic test fixture"
