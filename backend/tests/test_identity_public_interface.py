from datetime import date

import app.domains.identity as identity


def test_public_interface_exports_everything_this_test_needs():
    for name in [
        "Manufacturer",
        "ManufacturerKey",
        "ManufacturerKeyEvent",
        "Product",
        "Batch",
        "ProductIdentity",
        "LifecycleState",
        "IdentityIssuanceEvent",
        "DevelopmentOnlySigner",
        "Signer",
        "get_signer",
        "generate_serial",
        "register_manufacturer",
        "issue_manufacturer_key",
        "rotate_manufacturer_key",
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
        "BHIP_SCHEMA_VERSION",
    ]:
        assert hasattr(identity, name), f"public interface missing {name!r}"


def test_full_workflow_using_only_public_interface(identity_db_session):
    signer = identity.DevelopmentOnlySigner()
    actor = identity.ActorContext(
        actor_id="synthetic-workflow-actor",
        capabilities=frozenset(identity.Capability),
    )

    manufacturer = identity.register_manufacturer(identity_db_session, name="Synthetic Co")
    issued = identity.issue_manufacturer_key(
        identity_db_session,
        manufacturer_id=manufacturer.id,
        signer=signer,
        key_version=1,
        actor=actor,
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
    reserved = identity.reserve_identity(identity_db_session, batch_id=batch.id)
    assert reserved.lifecycle_state == identity.LifecycleState.RESERVED
    assert identity.is_well_formed_serial(reserved.serial)

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

    for state in [
        identity.LifecycleState.PRINTED,
        identity.LifecycleState.PRINT_VERIFIED,
        identity.LifecycleState.RECONCILED,
        identity.LifecycleState.ACTIVATED,
    ]:
        activated = identity.transition_identity(
            identity_db_session, identity=signed, new_state=state, actor=actor
        )
    identity_db_session.commit()

    assert activated.lifecycle_state == identity.LifecycleState.ACTIVATED
