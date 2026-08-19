import pytest

from app.domains.identity import (
    IllegalLifecycleTransitionError,
    LifecycleState,
    is_terminal,
    legal_next_states,
    transition_identity,
)
from app.domains.identity.lifecycle import assert_legal_transition
from tests.identity_fixtures import (
    FULLY_AUTHORIZED_TEST_ACTOR,
    full_signed_fixture,
)

LEGAL_PAIRS = [
    (LifecycleState.RESERVED, LifecycleState.SIGNED),
    (LifecycleState.SIGNED, LifecycleState.PRINTED),
    (LifecycleState.PRINTED, LifecycleState.PRINT_VERIFIED),
    (LifecycleState.PRINTED, LifecycleState.PRINT_REJECTED),
    (LifecycleState.PRINT_VERIFIED, LifecycleState.RECONCILED),
    (LifecycleState.PRINT_VERIFIED, LifecycleState.PRINT_REJECTED),
    (LifecycleState.RECONCILED, LifecycleState.ACTIVATED),
    (LifecycleState.RECONCILED, LifecycleState.PRINT_REJECTED),
]

ILLEGAL_PAIRS = [
    (LifecycleState.PRINTED, LifecycleState.RESERVED),
    (LifecycleState.ACTIVATED, LifecycleState.RESERVED),
    (LifecycleState.ACTIVATED, LifecycleState.SIGNED),
    (LifecycleState.ACTIVATED, LifecycleState.PRINTED),
    (LifecycleState.PRINT_REJECTED, LifecycleState.ACTIVATED),
    (LifecycleState.PRINT_REJECTED, LifecycleState.RESERVED),
    (LifecycleState.PRINT_REJECTED, LifecycleState.SIGNED),
    (LifecycleState.RESERVED, LifecycleState.PRINTED),
    (LifecycleState.RESERVED, LifecycleState.ACTIVATED),
    (LifecycleState.SIGNED, LifecycleState.RESERVED),
    (LifecycleState.SIGNED, LifecycleState.ACTIVATED),
    (LifecycleState.RECONCILED, LifecycleState.SIGNED),
]


@pytest.mark.parametrize("current,requested", LEGAL_PAIRS)
def test_legal_transition_allowed(current, requested):
    assert_legal_transition(current, requested)
    assert requested in legal_next_states(current)


@pytest.mark.parametrize("current,requested", ILLEGAL_PAIRS)
def test_illegal_transition_rejected(current, requested):
    with pytest.raises(IllegalLifecycleTransitionError):
        assert_legal_transition(current, requested)
    assert requested not in legal_next_states(current)


def test_activated_and_print_rejected_are_terminal():
    assert is_terminal(LifecycleState.ACTIVATED) is True
    assert is_terminal(LifecycleState.PRINT_REJECTED) is True


def test_non_terminal_states():
    for state in [
        LifecycleState.RESERVED,
        LifecycleState.SIGNED,
        LifecycleState.PRINTED,
        LifecycleState.PRINT_VERIFIED,
        LifecycleState.RECONCILED,
    ]:
        assert is_terminal(state) is False


def test_full_happy_path_reaches_activated(identity_db_session):
    fx = full_signed_fixture(identity_db_session)
    identity = fx["identity"]
    assert identity.lifecycle_state == LifecycleState.SIGNED

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
    transition_identity(
        identity_db_session,
        identity=identity,
        new_state=LifecycleState.RECONCILED,
        actor=FULLY_AUTHORIZED_TEST_ACTOR,
    )
    transition_identity(
        identity_db_session,
        identity=identity,
        new_state=LifecycleState.ACTIVATED,
        actor=FULLY_AUTHORIZED_TEST_ACTOR,
    )
    identity_db_session.commit()

    assert identity.lifecycle_state == LifecycleState.ACTIVATED
    assert identity.activated_at is not None


def test_print_rejected_is_terminal_and_cannot_reach_activated(identity_db_session):
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
        new_state=LifecycleState.PRINT_REJECTED,
        actor=FULLY_AUTHORIZED_TEST_ACTOR,
    )
    identity_db_session.commit()

    assert identity.lifecycle_state == LifecycleState.PRINT_REJECTED
    with pytest.raises(IllegalLifecycleTransitionError):
        transition_identity(
            identity_db_session,
            identity=identity,
            new_state=LifecycleState.ACTIVATED,
            actor=FULLY_AUTHORIZED_TEST_ACTOR,
        )
    with pytest.raises(IllegalLifecycleTransitionError):
        transition_identity(
            identity_db_session,
            identity=identity,
            new_state=LifecycleState.RESERVED,
            actor=FULLY_AUTHORIZED_TEST_ACTOR,
        )


def test_activation_only_through_legal_path(identity_db_session):
    fx = full_signed_fixture(identity_db_session)
    identity = fx["identity"]
    with pytest.raises(IllegalLifecycleTransitionError):
        transition_identity(
            identity_db_session,
            identity=identity,
            new_state=LifecycleState.ACTIVATED,
            actor=FULLY_AUTHORIZED_TEST_ACTOR,
        )
    assert identity.lifecycle_state == LifecycleState.SIGNED
