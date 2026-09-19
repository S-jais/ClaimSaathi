"""
app/core/hmac_middleware.py
Middleware + dependency for verifying HMAC-signed internal service requests.
Applied to all /internal/* routes — called only by n8n (or other backend services).
Human JWT tokens are NOT accepted on internal routes.
"""
from __future__ import annotations

from fastapi import Depends, Header, HTTPException, Request, status

from app.core.logging import get_logger
from app.core.security import verify_service_request

logger = get_logger(__name__)


async def verify_internal_service_auth(
    request: Request,
    x_service_auth: str = Header(..., alias="X-Service-Auth"),
) -> None:
    """
    FastAPI dependency for internal routes.
    Verifies that the X-Service-Auth HMAC header is valid and fresh.

    Usage:
        @router.post("/internal/documents/{id}/validate")
        async def internal_endpoint(_: None = Depends(verify_internal_service_auth)):
            ...
    """
    # Read body for HMAC verification — note: body can only be read once in
    # FastAPI; for GET requests with no body, use the path as the payload.
    try:
        body = await request.body()
        payload = body.decode("utf-8") if body else str(request.url.path)
    except Exception:
        payload = str(request.url.path)

    if not verify_service_request(x_service_auth, payload):
        logger.warning(
            "hmac_verification_failed",
            path=str(request.url.path),
            header_prefix=x_service_auth[:8] if x_service_auth else "missing",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or expired service authentication header.",
        )
