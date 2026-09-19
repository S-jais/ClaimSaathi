"""
app/core/logging.py
Structured JSON logging with correlation_id propagation.
Uses structlog for consistent, machine-parseable logs.
correlation_id is set per-request in middleware and propagated everywhere.
"""
from __future__ import annotations

import logging
import uuid
from contextvars import ContextVar
from typing import Any

try:
    import structlog
except ImportError:
    structlog = None
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.config import get_settings

# ---------------------------------------------------------------------------
# Context variable — propagated through async request lifecycle
# ---------------------------------------------------------------------------
_correlation_id_var: ContextVar[str] = ContextVar(
    "correlation_id", default=""
)


def get_correlation_id() -> str:
    return _correlation_id_var.get() or ""


def set_correlation_id(cid: str) -> None:
    _correlation_id_var.set(cid)


# ---------------------------------------------------------------------------
# Structlog configuration
# ---------------------------------------------------------------------------
def configure_logging() -> None:
    if structlog is None:
        logging.basicConfig(level=logging.INFO)
        return
    settings = get_settings()
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.LOG_FORMAT == "json":
        processors = shared_processors + [
            structlog.processors.JSONRenderer(),
        ]
    else:
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)


def get_logger(name: str = "claimsaathi") -> Any:
    if structlog is None:
        return logging.getLogger(name)
    return structlog.get_logger(name)


# ---------------------------------------------------------------------------
# Middleware — assigns correlation_id to every request
# ---------------------------------------------------------------------------
class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Assigns a correlation_id to every incoming request.
    Reads from X-Correlation-ID header if provided (e.g. from n8n),
    otherwise generates a new UUID.
    Adds X-Correlation-ID to the response for client-side tracing.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        cid = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        set_correlation_id(cid)
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            correlation_id=cid,
            method=request.method,
            path=request.url.path,
        )
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = cid
        return response
