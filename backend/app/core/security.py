"""
app/core/security.py
JWT generation/verification, password hashing, HMAC signing.
Never import this module from business logic — use the auth service layer.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()

# ---------------------------------------------------------------------------
# Password hashing (bcrypt)
# ---------------------------------------------------------------------------
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


# ---------------------------------------------------------------------------
# JWT access tokens
# ---------------------------------------------------------------------------
ALGORITHM = "HS256"


def create_access_token(
    subject: str,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """
    Create a short-lived JWT access token.
    subject: user id (UUID as string)
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": expire,
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token() -> tuple[str, str]:
    """
    Generate a cryptographically random refresh token.
    Returns (raw_token, hashed_token).
    Store only the hash; return the raw token to the client.
    """
    raw = secrets.token_urlsafe(48)
    hashed = hashlib.sha256(raw.encode()).hexdigest()
    return raw, hashed


def hash_token(raw: str) -> str:
    """Hash a raw token (refresh or session) for safe storage."""
    return hashlib.sha256(raw.encode()).hexdigest()


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT access token.
    Raises JWTError on invalid/expired token.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            raise JWTError("Invalid token type")
        return payload
    except JWTError:
        raise


# ---------------------------------------------------------------------------
# HMAC — service-to-service request signing (n8n -> backend)
# ---------------------------------------------------------------------------
HMAC_TOLERANCE_SECONDS = 300  # reject requests older than 5 minutes


def sign_service_request(payload: str, timestamp: int | None = None) -> str:
    """
    Create an HMAC-SHA256 signature for an internal service request.
    Format: "v1:{timestamp}:{hex-signature}"
    """
    ts = timestamp or int(time.time())
    message = f"{ts}:{payload}".encode()
    sig = hmac.new(
        settings.N8N_SERVICE_SECRET.encode(),
        message,
        hashlib.sha256,
    ).hexdigest()
    return f"v1:{ts}:{sig}"


def verify_service_request(
    header_value: str,
    payload: str,
) -> bool:
    """
    Verify an incoming HMAC-signed service request header.
    Returns False (never raises) — caller raises HTTP 403.
    """
    try:
        parts = header_value.split(":")
        if len(parts) != 3 or parts[0] != "v1":
            return False
        _, ts_str, provided_sig = parts
        ts = int(ts_str)
        # Reject stale requests
        if abs(int(time.time()) - ts) > HMAC_TOLERANCE_SECONDS:
            return False
        message = f"{ts}:{payload}".encode()
        expected_sig = hmac.new(
            settings.N8N_SERVICE_SECRET.encode(),
            message,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected_sig, provided_sig)
    except Exception:
        return False
