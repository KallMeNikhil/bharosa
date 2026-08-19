import uuid

import pytest

from app.core.authorization import Capability
from app.core.config import Settings
from app.core.principal import (
    DevelopmentOnlyPrincipalResolver,
    MalformedCredentialError,
    NoProductionPrincipalResolverConfiguredError,
    get_principal_resolver,
)

MANUFACTURER_ID = uuid.uuid4()


def _credential(capabilities: str = "*") -> str:
    return f"dev:{MANUFACTURER_ID}:alice:{capabilities}"


def test_a_missing_credential_resolves_to_no_principal():
    assert DevelopmentOnlyPrincipalResolver().resolve(None) is None
    assert DevelopmentOnlyPrincipalResolver().resolve("") is None


def test_a_credential_resolves_to_an_actor_scoped_to_one_manufacturer():
    principal = DevelopmentOnlyPrincipalResolver().resolve(
        _credential("AUTHORIZE_SIGNING")
    )
    assert principal.actor_id == "alice"
    assert principal.manufacturer_id == MANUFACTURER_ID
    assert principal.capabilities == frozenset({Capability.AUTHORIZE_SIGNING})


def test_the_wildcard_grants_every_capability():
    principal = DevelopmentOnlyPrincipalResolver().resolve(_credential("*"))
    assert principal.capabilities == frozenset(Capability)


def test_the_resolved_actor_carries_its_tenant_scope():
    actor = DevelopmentOnlyPrincipalResolver().resolve(_credential()).to_actor()
    assert actor.manufacturer_id == MANUFACTURER_ID
    actor.require_tenant(MANUFACTURER_ID)


@pytest.mark.parametrize(
    "credential",
    [
        "bearer-token-without-structure",
        f"dev:{MANUFACTURER_ID}:alice",
        f"prod:{MANUFACTURER_ID}:alice:*",
        "dev:not-a-uuid:alice:*",
        f"dev:{MANUFACTURER_ID}::*",
        f"dev:{MANUFACTURER_ID}:alice:NOT_A_CAPABILITY",
    ],
)
def test_malformed_credentials_are_rejected(credential):
    with pytest.raises(MalformedCredentialError):
        DevelopmentOnlyPrincipalResolver().resolve(credential)


@pytest.mark.parametrize("environment", ["development", "test"])
def test_the_development_resolver_is_available_outside_production(environment):
    resolver = get_principal_resolver(Settings(environment=environment))
    assert isinstance(resolver, DevelopmentOnlyPrincipalResolver)


def test_the_development_resolver_is_structurally_blocked_in_production():
    with pytest.raises(NoProductionPrincipalResolverConfiguredError):
        get_principal_resolver(Settings(environment="production"))


def test_no_resolver_silently_falls_back_for_an_unknown_environment():
    with pytest.raises(NoProductionPrincipalResolverConfiguredError):
        get_principal_resolver(Settings(environment="staging"))
