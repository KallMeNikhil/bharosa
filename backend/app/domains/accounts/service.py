from __future__ import annotations

import hashlib
import re
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.authorization import Capability
from app.core.principal import Principal
from app.core.tenancy import set_tenant_context
from app.domains.accounts.models import Account, AccountRole, AccountSession
from app.domains.accounts.passwords import (
    DUMMY_HASH,
    MIN_PASSWORD_LENGTH,
    hash_password,
    verify_password,
)
from app.domains.identity import Manufacturer, register_manufacturer

SESSION_TOKEN_PREFIX = "bt_"
_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

_CAPABILITIES_BY_ROLE: dict[str, frozenset[Capability]] = {
    AccountRole.OWNER.value: frozenset(Capability),
}


class AccountError(ValueError):
    pass


class EmailAlreadyRegisteredError(AccountError):
    pass


class InvalidSignInError(AccountError):
    pass


@dataclass(frozen=True)
class SignedIn:
    account: Account
    manufacturer: Manufacturer
    token: str
    expires_at: datetime


def normalize_email(email: str) -> str:
    normalized = email.strip().lower()
    if len(normalized) > 320 or not _EMAIL_PATTERN.match(normalized):
        raise AccountError("Enter a valid email address.")
    return normalized


def _token_hash(token: str) -> bytes:
    return hashlib.sha256(token.encode("utf-8")).digest()


def _issue_session(db: Session, account: Account, ttl: timedelta) -> tuple[str, datetime]:
    token = SESSION_TOKEN_PREFIX + secrets.token_urlsafe(32)
    expires_at = datetime.now(UTC) + ttl
    db.add(
        AccountSession(account_id=account.id, token_hash=_token_hash(token), expires_at=expires_at)
    )
    db.flush()
    return token, expires_at


def register_account(
    db: Session,
    *,
    company_name: str,
    email: str,
    password: str,
    display_name: str | None,
    session_ttl: timedelta,
) -> SignedIn:
    """Create a manufacturer and the account that owns it, and sign it in."""
    company_name = company_name.strip()
    if not 2 <= len(company_name) <= 255:
        raise AccountError("Enter the company name, 2 to 255 characters.")
    email = normalize_email(email)
    if len(password) < MIN_PASSWORD_LENGTH:
        raise AccountError(f"Use a password of at least {MIN_PASSWORD_LENGTH} characters.")
    if db.execute(select(Account.id).where(Account.email == email)).first():
        raise EmailAlreadyRegisteredError("An account with this email already exists.")

    manufacturer_id = uuid.uuid4()
    set_tenant_context(db, manufacturer_id)
    manufacturer = register_manufacturer(db, name=company_name, manufacturer_id=manufacturer_id)

    account = Account(
        email=email,
        display_name=(display_name or "").strip() or None,
        password_hash=hash_password(password),
        manufacturer_id=manufacturer_id,
        role=AccountRole.OWNER.value,
        last_signed_in_at=datetime.now(UTC),
    )
    db.add(account)
    db.flush()
    token, expires_at = _issue_session(db, account, session_ttl)
    return SignedIn(account=account, manufacturer=manufacturer, token=token, expires_at=expires_at)


def sign_in(db: Session, *, email: str, password: str, session_ttl: timedelta) -> SignedIn:
    try:
        email = normalize_email(email)
    except AccountError:
        email = ""
    account = db.execute(select(Account).where(Account.email == email)).scalar_one_or_none()
    if account is None:
        verify_password(password, DUMMY_HASH)
        raise InvalidSignInError("The email or password is not right.")
    if not verify_password(password, account.password_hash):
        raise InvalidSignInError("The email or password is not right.")

    account.last_signed_in_at = datetime.now(UTC)
    token, expires_at = _issue_session(db, account, session_ttl)
    set_tenant_context(db, account.manufacturer_id)
    manufacturer = db.execute(
        select(Manufacturer).where(Manufacturer.id == account.manufacturer_id)
    ).scalar_one()
    return SignedIn(account=account, manufacturer=manufacturer, token=token, expires_at=expires_at)


def resolve_session(db: Session, token: str) -> Principal | None:
    """The principal a session token stands for, or None if it is unknown,
    expired or signed out."""
    if not token.startswith(SESSION_TOKEN_PREFIX):
        return None
    row = db.execute(
        select(Account, AccountSession)
        .join(AccountSession, AccountSession.account_id == Account.id)
        .where(AccountSession.token_hash == _token_hash(token))
    ).first()
    if row is None:
        return None
    account, session = row
    if session.revoked_at is not None or session.expires_at <= datetime.now(UTC):
        return None
    return Principal(
        actor_id=account.email,
        manufacturer_id=account.manufacturer_id,
        capabilities=_CAPABILITIES_BY_ROLE.get(account.role, frozenset()),
    )


def sign_out(db: Session, token: str) -> None:
    session = db.execute(
        select(AccountSession).where(AccountSession.token_hash == _token_hash(token))
    ).scalar_one_or_none()
    if session is not None and session.revoked_at is None:
        session.revoked_at = datetime.now(UTC)
        db.flush()
