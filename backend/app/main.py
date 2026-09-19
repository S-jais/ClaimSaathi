"""
app/main.py
FastAPI application entry point.
Registers all routers, middleware, exception handlers, and lifecycle events.
This is the modular monolith root — each module registers its own router here.
"""
from __future__ import annotations

from dotenv import load_dotenv
load_dotenv()

import asyncio
import redis.asyncio as aioredis
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.core.config import get_settings
from app.core.db import check_db_connection
from app.core.exceptions import register_exception_handlers
from app.core.logging import CorrelationIdMiddleware, configure_logging, get_logger
from app.core.storage import storage

settings = get_settings()
configure_logging()
logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Rate limiter (slowapi — wraps limits)
# ---------------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])


# ---------------------------------------------------------------------------
# Lifespan: startup / shutdown
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("claimsaathi_startup", env=settings.APP_ENV)
    yield
    logger.info("claimsaathi_shutdown")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------
def create_app() -> FastAPI:
    app = FastAPI(
        title="ClaimSaathi API",
        description=(
            "Customer-side AI copilot for health-insurance reimbursement claims. "
            "ClaimSaathi never approves, rejects, or predicts claim outcomes. "
            "The insurer remains the sole regulated decision-maker."
        ),
        version="0.1.0",
        docs_url="/docs" if settings.ENABLE_DOCS else None,
        redoc_url="/redoc" if settings.ENABLE_DOCS else None,
        openapi_url="/openapi.json" if settings.ENABLE_DOCS else None,
        lifespan=lifespan,
    )

    # --- Middleware (applied in reverse order of registration) ---
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_origin_regex=r"https://.*\.vercel\.app",
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Correlation-ID", "Idempotency-Key"],
        expose_headers=["X-Correlation-ID"],
    )
    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(SlowAPIMiddleware)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # --- Exception handlers ---
    register_exception_handlers(app)

    # --- Routers ---
    from app.auth.router import router as auth_router
    app.include_router(auth_router, prefix="/api/v1")

    from app.policies.router import router as policy_router
    app.include_router(policy_router, prefix="/api/v1")
    from app.claims.router import router as claims_router
    app.include_router(claims_router, prefix="/api/v1")
    from app.documents.router import router as documents_router
    app.include_router(documents_router, prefix="/api/v1")
    from app.chat.router import router as chat_router
    app.include_router(chat_router, prefix="/api/v1")
    # from app.consent.router import router as consent_router
    # app.include_router(consent_router, prefix="/api/v1")
    # from app.audit.router import router as audit_router
    # app.include_router(audit_router, prefix="/api/v1")
    # from app.notifications.router import router as notifications_router
    # app.include_router(notifications_router, prefix="/api/v1")

    # --- Ops endpoints ---
    @app.get("/", tags=["ops"], include_in_schema=False)
    async def root() -> dict[str, Any]:
        """Root status endpoint returning API metadata and links."""
        return {
            "name": "ClaimSaathi API",
            "version": "0.1.0",
            "status": "healthy",
            "environment": settings.APP_ENV,
            "docs": "/docs" if settings.ENABLE_DOCS else None,
            "health": "/health",
            "readiness": "/readiness",
        }

    @app.get("/health", tags=["ops"], include_in_schema=False)
    async def health() -> dict[str, str]:
        """Process alive check. Returns 200 if the process is running."""
        return {"status": "ok"}

    @app.get("/readiness", tags=["ops"], include_in_schema=False)
    @app.get("/ready", tags=["ops"], include_in_schema=False)
    async def readiness() -> dict[str, Any]:
        """
        Deep readiness check. Returns 503 if any critical dependency is down.
        Checked by Docker health check and load balancers.
        """
        from fastapi import status as http_status
        from fastapi.responses import JSONResponse

        async def _safe_db() -> bool:
            try:
                return await asyncio.wait_for(check_db_connection(), timeout=2.0)
            except Exception:
                return False

        async def _safe_storage() -> bool:
            try:
                return await asyncio.wait_for(storage().health_check(), timeout=2.0)
            except Exception:
                return False

        async def _safe_redis() -> bool:
            try:
                r = aioredis.from_url(settings.REDIS_URL)
                await asyncio.wait_for(r.ping(), timeout=2.0)
                await r.aclose()
                return True
            except Exception:
                return False

        db_ok, storage_ok, redis_ok = await asyncio.gather(
            _safe_db(), _safe_storage(), _safe_redis()
        )

        result = {
            "status": "ready" if (db_ok and storage_ok and redis_ok) else "not_ready",
            "checks": {
                "database": "ok" if db_ok else "error",
                "storage": "ok" if storage_ok else "error",
                "redis": "ok" if redis_ok else "error",
            },
        }

        if result["status"] != "ready":
            return JSONResponse(content=result, status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE)
        return result

    @app.get("/version", tags=["ops"], include_in_schema=False)
    async def version() -> dict[str, str]:
        return {
            "version": app.version,
            "env": settings.APP_ENV,
            "llm_provider": settings.LLM_PROVIDER,
            "ocr_adapter": settings.OCR_ADAPTER,
        }

    return app


app = create_app()
