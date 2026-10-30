from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, LargeBinary, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AccountRole(str, enum.Enum):
    OWNER = "OWNER"


class Account(Base):
    """A person who signs in to a manufacturer's workspace.

    Accounts are platform-level rather than tenant-scoped: signing in has to
    find the account before any tenant is known. Each account belongs to
    exactly one manufacturer, and it is that manufacturer the session is then
    scoped to.
    """

    __tablename__ = "auth_account"
    __table_args__ = (Index("ix_auth_account_manufacturer_id", "manufacturer_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    manufacturer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity_manufacturer.id"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False, default=AccountRole.OWNER.value)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_signed_in_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class AccountSession(Base):
    """A signed-in session. Only a hash of the token is stored, so a copy of
    this table cannot be replayed as a credential."""

    __tablename__ = "auth_session"
    __table_args__ = (Index("ix_auth_session_account_id", "account_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("auth_account.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
