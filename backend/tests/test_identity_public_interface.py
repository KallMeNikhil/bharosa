from datetime import date

import app.domains.identity as identity


def test_public_interface_exports_everything_this_test_needs():
    for name in [
        "Manufacturer",
        "ManufacturerKey",
        "Product",
        "Batch",
        "ProductIdentity",
        "LifecycleState",
        "IdentityIssuanceEvent",
        "DevelopmentOnlySigner",
        "Signer",
        "get_signer",
        "register_manufacturer",
        "issue_manufacturer_key",
        "register_product",
        "open_batch",
        "reserve_identity",
        "sign_identity",
        "transition_identity",
        "verify_cryptographic_authenticity",
        "ActorContext",
        "Capability",
        "SigningNotAuthorizedError",
        "CrossManufacturerKeyMismatchError",
        "KeyStatus",
    ]:
        assert hasattr(identity, name), f"public interface missing {name!r}"


def test_full_workflow_using_only_public_interface(identity_db_session):
    signer = identity.DevelopmentOnlySigner()
    actor = identity.ActorContext(
        actor_id="synthetic-workflow-actor",
        capabilities=frozenset({identity.Capability.AUTHORIZE_SIGNING}),
    )

    manufacturer = identity.register_manufacturer(identity_db_session, name="Synthetic Co")
    issued = identity.issue_manufacturer_key(
        identity_db_session, manufacturer_id=manufacturer.id, signer=signer, key_version=1
    )
    product = identity.register_product(
        identity_db_session,
        manufacturer_id=manufacturer.id,
        product_ref="SYN-001",
        name="Synthetic Product",
    )
    batch = identity.open_batch(
        identity_db_session,
        product_id=product.id,
        batch_ref="SYN-BATCH-001",
        manufacturing_date=date(2026, 1, 1),
        expiry_date=date(2028, 1, 1),
    )
    reserved = identity.reserve_identity(
        identity_db_session, batch_id=batch.id, serial="SYN-SERIAL-1"
    )
    assert reserved.lifecycle_state == identity.LifecycleState.RESERVED

    signed = identity.sign_identity(
        identity_db_session,
        identity=reserved,
        manufacturer_key=issued.manufacturer_key,
        signer=signer,
        key_handle=issued.key_handle,
        actor=actor,
    )
    assert signed.lifecycle_state == identity.LifecycleState.SIGNED

    result = identity.verify_cryptographic_authenticity(signed)
    assert result.is_valid is True

    identity.transition_identity(
        identity_db_session, identity=signed, new_state=identity.LifecycleState.PRINTED
    )
    identity.transition_identity(
        identity_db_session, identity=signed, new_state=identity.LifecycleState.PRINT_VERIFIED
    )
    identity.transition_identity(
        identity_db_session, identity=signed, new_state=identity.LifecycleState.RECONCILED
    )
    activated = identity.transition_identity(
        identity_db_session, identity=signed, new_state=identity.LifecycleState.ACTIVATED
    )
    identity_db_session.commit()

    assert activated.lifecycle_state == identity.LifecycleState.ACTIVATED
