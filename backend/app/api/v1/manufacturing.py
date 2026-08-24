from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api import schemas
from app.api.deps import (
    current_actor,
    current_principal,
    development_only,
    owned_or_404,
    requires,
    tenant_db,
)
from app.core.authorization import ActorContext, Capability
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.principal import Principal
from app.core.tenancy import set_tenant_context
from app.domains.identity import (
    Batch,
    IdentityIssuanceEvent,
    ManufacturerKey,
    Product,
    ProductIdentity,
    get_signer,
    issue_manufacturer_key,
    mark_manufacturer_key_compromised,
    open_batch,
    register_manufacturer,
    register_product,
    reserve_identity,
    revoke_manufacturer_key,
    rotate_manufacturer_key,
    sign_identity,
    transition_identity,
)
from app.domains.verification import build_digital_link

router = APIRouter(tags=["manufacturing"])


@router.get("/me", response_model=schemas.ActorView)
def whoami(principal: Principal = Depends(current_principal)) -> schemas.ActorView:
    return schemas.ActorView(
        actor_id=principal.actor_id,
        manufacturer_id=principal.manufacturer_id,
        capabilities=sorted(principal.capabilities, key=lambda c: c.value),
    )


@router.post(
    "/manufacturers",
    response_model=schemas.ManufacturerView,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(development_only)],
    summary="Onboard a manufacturer (non-production only)",
)
def create_manufacturer(
    body: schemas.ManufacturerCreate, db: Session = Depends(get_db)
) -> schemas.ManufacturerView:
    """Onboarding is a platform action, not a tenant action.

    It necessarily happens before any tenant context for the new manufacturer
    can exist, so it takes no principal. The scope is established here, from
    the identifier the new manufacturer is about to be given, because
    row-level security applies to the row this request reads back as much as
    to the row it writes. Production onboarding belongs to the administrative
    surface built during production hardening, and this endpoint is
    unavailable there.
    """
    manufacturer_id = uuid.uuid4()
    set_tenant_context(db, manufacturer_id)
    manufacturer = register_manufacturer(
        db, name=body.name, manufacturer_id=manufacturer_id
    )
    db.commit()
    return schemas.ManufacturerView.model_validate(manufacturer)


@router.post(
    "/keys", response_model=schemas.IssuedKeyView, status_code=status.HTTP_201_CREATED
)
def create_key(
    body: schemas.KeyCreate,
    actor: ActorContext = Depends(requires(Capability.MANAGE_KEYS)),
    db: Session = Depends(tenant_db),
    settings: Settings = Depends(get_settings),
) -> schemas.IssuedKeyView:
    issued = issue_manufacturer_key(
        db,
        manufacturer_id=actor.manufacturer_id,
        signer=get_signer(settings),
        key_version=body.key_version,
        actor=actor,
    )
    db.commit()
    return schemas.IssuedKeyView(
        key=schemas.KeyView.model_validate(issued.manufacturer_key),
        key_handle=issued.key_handle,
    )


@router.get("/keys", response_model=list[schemas.KeyView])
def list_keys(
    actor: ActorContext = Depends(current_actor), db: Session = Depends(tenant_db)
) -> list[ManufacturerKey]:
    return list(
        db.execute(select(ManufacturerKey).order_by(ManufacturerKey.key_version))
        .scalars()
        .all()
    )


@router.post("/keys/{key_id}/rotate", response_model=schemas.IssuedKeyView)
def rotate_key(
    key_id: uuid.UUID,
    body: schemas.KeyStatusChange,
    actor: ActorContext = Depends(requires(Capability.MANAGE_KEYS)),
    db: Session = Depends(tenant_db),
    settings: Settings = Depends(get_settings),
) -> schemas.IssuedKeyView:
    key = owned_or_404(db.get(ManufacturerKey, key_id), actor.manufacturer_id, name="Key")
    issued = rotate_manufacturer_key(
        db, key=key, signer=get_signer(settings), actor=actor, reason=body.reason
    )
    db.commit()
    return schemas.IssuedKeyView(
        key=schemas.KeyView.model_validate(issued.manufacturer_key),
        key_handle=issued.key_handle,
    )


@router.post("/keys/{key_id}/revoke", response_model=schemas.KeyView)
def revoke_key(
    key_id: uuid.UUID,
    body: schemas.KeyStatusChange,
    actor: ActorContext = Depends(requires(Capability.MANAGE_KEYS)),
    db: Session = Depends(tenant_db),
) -> ManufacturerKey:
    key = owned_or_404(db.get(ManufacturerKey, key_id), actor.manufacturer_id, name="Key")
    revoke_manufacturer_key(db, key=key, actor=actor, reason=body.reason)
    db.commit()
    return key


@router.post("/keys/{key_id}/compromise", response_model=schemas.KeyView)
def compromise_key(
    key_id: uuid.UUID,
    body: schemas.KeyStatusChange,
    actor: ActorContext = Depends(requires(Capability.MANAGE_KEYS)),
    db: Session = Depends(tenant_db),
) -> ManufacturerKey:
    key = owned_or_404(db.get(ManufacturerKey, key_id), actor.manufacturer_id, name="Key")
    mark_manufacturer_key_compromised(db, key=key, actor=actor, reason=body.reason)
    db.commit()
    return key


@router.post(
    "/products", response_model=schemas.ProductView, status_code=status.HTTP_201_CREATED
)
def create_product(
    body: schemas.ProductCreate,
    actor: ActorContext = Depends(requires(Capability.CREATE_PRODUCTION_ORDER)),
    db: Session = Depends(tenant_db),
) -> Product:
    product = register_product(
        db,
        manufacturer_id=actor.manufacturer_id,
        product_ref=body.product_ref,
        name=body.name,
        gtin=body.gtin,
    )
    db.commit()
    return product


@router.get("/products", response_model=list[schemas.ProductView])
def list_products(db: Session = Depends(tenant_db)) -> list[Product]:
    return list(db.execute(select(Product).order_by(Product.product_ref)).scalars().all())


@router.post(
    "/batches", response_model=schemas.BatchView, status_code=status.HTTP_201_CREATED
)
def create_batch(
    body: schemas.BatchCreate,
    actor: ActorContext = Depends(requires(Capability.CREATE_PRODUCTION_ORDER)),
    db: Session = Depends(tenant_db),
) -> Batch:
    owned_or_404(db.get(Product, body.product_id), actor.manufacturer_id, name="Product")
    batch = open_batch(
        db,
        product_id=body.product_id,
        batch_ref=body.batch_ref,
        manufacturing_date=body.manufacturing_date,
        expiry_date=body.expiry_date,
    )
    db.commit()
    return batch


@router.get("/batches", response_model=list[schemas.BatchView])
def list_batches(
    product_id: uuid.UUID | None = None, db: Session = Depends(tenant_db)
) -> list[Batch]:
    statement = select(Batch).order_by(Batch.batch_ref)
    if product_id is not None:
        statement = statement.where(Batch.product_id == product_id)
    return list(db.execute(statement).scalars().all())


@router.post(
    "/identities/reserve",
    response_model=list[schemas.IdentityView],
    status_code=status.HTTP_201_CREATED,
)
def reserve_identities(
    body: schemas.IdentityReserve,
    actor: ActorContext = Depends(requires(Capability.CREATE_PRODUCTION_ORDER)),
    db: Session = Depends(tenant_db),
) -> list[ProductIdentity]:
    owned_or_404(db.get(Batch, body.batch_id), actor.manufacturer_id, name="Batch")
    identities = [
        reserve_identity(db, batch_id=body.batch_id) for _ in range(body.count)
    ]
    db.commit()
    return identities


@router.post("/identities/{identity_id}/sign", response_model=schemas.IdentityView)
def sign(
    identity_id: uuid.UUID,
    body: schemas.IdentitySign,
    actor: ActorContext = Depends(requires(Capability.AUTHORIZE_SIGNING)),
    db: Session = Depends(tenant_db),
    settings: Settings = Depends(get_settings),
) -> ProductIdentity:
    identity = owned_or_404(
        db.get(ProductIdentity, identity_id), actor.manufacturer_id, name="Identity"
    )
    key = owned_or_404(
        db.get(ManufacturerKey, body.manufacturer_key_id), actor.manufacturer_id, name="Key"
    )
    signed = sign_identity(
        db,
        identity=identity,
        manufacturer_key=key,
        signer=get_signer(settings),
        key_handle=body.key_handle,
        actor=actor,
    )
    db.commit()
    return signed


@router.post("/identities/{identity_id}/transition", response_model=schemas.IdentityView)
def transition(
    identity_id: uuid.UUID,
    body: schemas.IdentityTransition,
    actor: ActorContext = Depends(current_actor),
    db: Session = Depends(tenant_db),
) -> ProductIdentity:
    identity = owned_or_404(
        db.get(ProductIdentity, identity_id), actor.manufacturer_id, name="Identity"
    )
    updated = transition_identity(
        db,
        identity=identity,
        new_state=body.new_state,
        actor=actor,
        event_metadata=body.event_metadata,
    )
    db.commit()
    return updated


@router.get("/identities", response_model=list[schemas.IdentityView])
def list_identities(
    batch_id: uuid.UUID | None = None,
    serial: str | None = None,
    limit: int = 100,
    db: Session = Depends(tenant_db),
) -> list[ProductIdentity]:
    """Identities in the caller's tenant, optionally narrowed to one serial.

    The serial filter exists because a scanner reads a serial off a pack but
    every custody route is keyed by identity id. It is an exact match rather
    than a search: a partial serial that matched several packs would let a
    mistyped code be recorded against the wrong one.
    """
    statement = select(ProductIdentity).order_by(ProductIdentity.created_at).limit(
        min(limit, 500)
    )
    if batch_id is not None:
        statement = statement.where(ProductIdentity.batch_id == batch_id)
    if serial is not None:
        statement = statement.where(ProductIdentity.serial == serial.strip().upper())
    return list(db.execute(statement).scalars().all())


@router.get("/identities/{identity_id}", response_model=schemas.IdentityView)
def get_identity(
    identity_id: uuid.UUID,
    actor: ActorContext = Depends(current_actor),
    db: Session = Depends(tenant_db),
) -> ProductIdentity:
    return owned_or_404(
        db.get(ProductIdentity, identity_id), actor.manufacturer_id, name="Identity"
    )


@router.get(
    "/identities/{identity_id}/events", response_model=list[schemas.IdentityEventView]
)
def identity_events(
    identity_id: uuid.UUID, db: Session = Depends(tenant_db)
) -> list[IdentityIssuanceEvent]:
    return list(
        db.execute(
            select(IdentityIssuanceEvent)
            .where(IdentityIssuanceEvent.identity_id == identity_id)
            .order_by(IdentityIssuanceEvent.sequence)
        )
        .scalars()
        .all()
    )


@router.get(
    "/identities/{identity_id}/digital-link", response_model=schemas.DigitalLinkView
)
def identity_digital_link(
    identity_id: uuid.UUID,
    actor: ActorContext = Depends(current_actor),
    db: Session = Depends(tenant_db),
    settings: Settings = Depends(get_settings),
) -> schemas.DigitalLinkView:
    identity = owned_or_404(
        db.get(ProductIdentity, identity_id), actor.manufacturer_id, name="Identity"
    )
    product = identity.batch.product
    if product.gtin is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This product has no GTIN, so no GS1 Digital Link can be built "
                "for its identities."
            ),
        )
    return schemas.DigitalLinkView(
        identity_id=identity.id,
        uri=build_digital_link(
            host=settings.digital_link_host,
            gtin=product.gtin,
            bharosa_serial=identity.serial,
            lot=identity.batch.batch_ref,
        ),
    )
