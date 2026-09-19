"""
app/auth/models.py
SQLAlchemy ORM models: users, roles, user_roles, sessions.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, TimestampMixin

if TYPE_CHECKING:
    from app.consent.models import Consent


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    # Valid values: customer | support_admin | system
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    user_roles: Mapped[list["UserRole"]] = relationship("UserRole", back_populates="role")


class UserRole(Base):
    __tablename__ = "user_roles"
    __table_args__ = (UniqueConstraint("user_id", "role_id", name="uq_user_role"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )

    user: Mapped["User"] = relationship("User", back_populates="user_roles")
    role: Mapped["Role"] = relationship("Role", back_populates="user_roles")


class User(Base, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)  # masked at rest
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="active", nullable=False
    )  # active | suspended | deleted
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user_roles: Mapped[list["UserRole"]] = relationship(
        "UserRole", back_populates="user", cascade="all, delete-orphan"
    )
    sessions: Mapped[list["Session"]] = relationship(
        "Session", back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def roles(self) -> list[str]:
        return [ur.role.name for ur in self.user_roles if ur.role]

    def has_role(self, role: str) -> bool:
        return role in self.roles


class Session(Base, TimestampMixin):
    __tablename__ = "sessions"
    __table_args__ = (
        # Fast lookup for refresh-token rotation
        {"comment": "Stores hashed refresh tokens — never plaintext"},
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="sessions")

    @property
    def is_valid(self) -> bool:
        from datetime import timezone
        from datetime import datetime as dt
        return self.revoked_at is None and self.expires_at > dt.now(timezone.utc)
