"""
app/auth/router.py
Auth endpoints: register, login, refresh, logout, me.
Rate-limited aggressively. Every failure is audit-logged.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.auth.service import AuthService, get_current_user
from app.auth.models import User
from app.core.db import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    req: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Register a new customer account and return auth tokens."""
    service = AuthService(db)
    _, tokens = await service.register(req)
    return tokens


@router.post("/login", response_model=TokenResponse)
async def login(
    req: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate and return access + refresh tokens."""
    service = AuthService(db)
    ip = request.client.host if request.client else None
    ua = request.headers.get("User-Agent")
    _, tokens = await service.login(req, ip=ip, ua=ua)
    return tokens


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    req: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Rotate a refresh token and return new token pair."""
    service = AuthService(db)
    return await service.refresh(req.refresh_token)


@router.post("/logout", status_code=204)
async def logout(
    req: LogoutRequest,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Revoke the refresh token (session)."""
    service = AuthService(db)
    await service.logout(req.refresh_token)


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)) -> User:
    """Return the current authenticated user's profile."""
    return user
