"""
app/auth/service.py
Business logic for authentication: register, login, refresh, logout.
Also provides the get_current_user dependency used by all protected routes.
Ownership checks are enforced here and in each domain service — never at route level alone.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.models import Role, Session, User, UserRole
from app.auth.schemas import LoginRequest, RegisterRequest, TokenResponse
from app.core.config import get_settings
from app.core.db import get_db
from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)

settings = get_settings()
logger = get_logger(__name__)
_bearer = HTTPBearer(auto_error=False)


async def _get_customer_role(db: AsyncSession) -> Role:
    result = await db.execute(select(Role).where(Role.name == "customer"))
    role = result.scalar_one_or_none()
    if not role:
        raise RuntimeError("customer role not seeded — run migrations first")
    return role


class AuthService:

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def register(self, req: RegisterRequest) -> tuple[User, TokenResponse]:
        # Check uniqueness
        exists = await self._db.execute(select(User).where(User.email == req.email))
        if exists.scalar_one_or_none():
            raise ConflictError("An account with this email already exists.")

        user = User(
            email=req.email,
            full_name=req.full_name,
            password_hash=hash_password(req.password),
        )
        self._db.add(user)
        await self._db.flush()  # get UUID before commit

        # Assign customer role
        customer_role = await _get_customer_role(self._db)
        self._db.add(UserRole(user_id=user.id, role_id=customer_role.id))

        tokens = await self._create_session(user)
        logger.info("user_registered", user_id=str(user.id))
        return user, tokens

    async def login(self, req: LoginRequest, ip: str | None, ua: str | None) -> tuple[User, TokenResponse]:
        result = await self._db.execute(
            select(User).where(User.email == req.email, User.deleted_at.is_(None))
            .options(selectinload(User.user_roles).selectinload(UserRole.role))
        )
        user = result.scalar_one_or_none()

        # Constant-time check regardless of whether user exists
        if not user or not verify_password(req.password, user.password_hash):
            logger.warning("login_failed", email=req.email, ip=ip)
            raise UnauthorizedError("Invalid email or password.")

        if user.status != "active":
            raise UnauthorizedError("Account suspended. Contact support.")

        tokens = await self._create_session(user, ip=ip, ua=ua)
        logger.info("user_login", user_id=str(user.id))
        return user, tokens

    async def refresh(self, raw_refresh_token: str) -> TokenResponse:
        token_hash = hash_token(raw_refresh_token)
        result = await self._db.execute(
            select(Session)
            .where(Session.token_hash == token_hash)
            .options(selectinload(Session.user))
        )
        session = result.scalar_one_or_none()
        if not session or not session.is_valid:
            raise UnauthorizedError("Invalid or expired refresh token.")

        # Rotate: revoke old session, create new
        session.revoked_at = datetime.now(timezone.utc)
        tokens = await self._create_session(session.user)
        logger.info("token_refreshed", user_id=str(session.user_id))
        return tokens

    async def logout(self, raw_refresh_token: str) -> None:
        token_hash = hash_token(raw_refresh_token)
        result = await self._db.execute(
            select(Session).where(Session.token_hash == token_hash)
        )
        session = result.scalar_one_or_none()
        if session:
            session.revoked_at = datetime.now(timezone.utc)
        # Silently succeed even if token not found (already revoked)

    async def _create_session(
        self,
        user: User,
        ip: str | None = None,
        ua: str | None = None,
    ) -> TokenResponse:
        raw_refresh, hashed_refresh = create_refresh_token()
        expire_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        session = Session(
            user_id=user.id,
            token_hash=hashed_refresh,
            expires_at=expire_at,
            ip_address=ip,
            user_agent=ua,
        )
        self._db.add(session)
        access_token = create_access_token(str(user.id))
        return TokenResponse(
            access_token=access_token,
            refresh_token=raw_refresh,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )


# ---------------------------------------------------------------------------
# FastAPI dependency — get current authenticated user
# ---------------------------------------------------------------------------
async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Decodes JWT, validates it, loads the User from DB.
    Raises UnauthorizedError on any failure.
    Used as: user: User = Depends(get_current_user)
    """
    if not credentials:
        raise UnauthorizedError("Authentication required.")

    try:
        payload = __import__("app.core.security", fromlist=["decode_access_token"]).decode_access_token(
            credentials.credentials
        )
        user_id = payload.get("sub")
        if not user_id:
            raise UnauthorizedError("Invalid token payload.")
    except JWTError:
        raise UnauthorizedError("Invalid or expired token.")

    result = await db.execute(
        select(User)
        .where(User.id == uuid.UUID(user_id), User.deleted_at.is_(None), User.status == "active")
        .options(selectinload(User.user_roles).selectinload(UserRole.role))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise UnauthorizedError("User not found or account deactivated.")

    return user


async def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """
    Returns the authenticated User if a valid JWT is present, or None if unauthenticated/invalid.
    Used for public or demo endpoints where authentication is optional.
    """
    if not credentials:
        return None

    try:
        payload = __import__("app.core.security", fromlist=["decode_access_token"]).decode_access_token(
            credentials.credentials
        )
        user_id = payload.get("sub")
        if not user_id:
            return None
        result = await db.execute(
            select(User)
            .where(User.id == uuid.UUID(user_id), User.deleted_at.is_(None), User.status == "active")
            .options(selectinload(User.user_roles).selectinload(UserRole.role))
        )
        return result.scalar_one_or_none()
    except Exception:
        return None


def require_role(role: str):
    """
    Dependency factory: require a specific role.
    Usage: Depends(require_role("support_admin"))
    """
    async def _check(user: User = Depends(get_current_user)) -> User:
        if not user.has_role(role) and not user.has_role("system"):
            raise __import__("app.core.exceptions", fromlist=["ForbiddenError"]).ForbiddenError(
                f"Role '{role}' required."
            )
        return user
    return _check
