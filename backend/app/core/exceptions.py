"""
app/core/exceptions.py
RFC-7807 problem+json error responses.
All HTTP errors raised as ClaimSaathiError subclasses.
Global exception handlers registered in main.py.
Never return stack traces or internal paths to the client.
"""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_correlation_id, get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Base error
# ---------------------------------------------------------------------------
class ClaimSaathiError(Exception):
    """Base application error."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_type: str = "https://claimsaathi.in/errors/internal"
    title: str = "Internal Server Error"

    def __init__(
        self,
        detail: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        self.detail = detail or self.title
        self.extra = extra or {}
        super().__init__(self.detail)


# ---------------------------------------------------------------------------
# Typed error classes
# ---------------------------------------------------------------------------
class NotFoundError(ClaimSaathiError):
    status_code = status.HTTP_404_NOT_FOUND
    error_type = "https://claimsaathi.in/errors/not-found"
    title = "Resource Not Found"


class UnauthorizedError(ClaimSaathiError):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_type = "https://claimsaathi.in/errors/unauthorized"
    title = "Unauthorized"


class ForbiddenError(ClaimSaathiError):
    status_code = status.HTTP_403_FORBIDDEN
    error_type = "https://claimsaathi.in/errors/forbidden"
    title = "Forbidden"


class ConflictError(ClaimSaathiError):
    status_code = status.HTTP_409_CONFLICT
    error_type = "https://claimsaathi.in/errors/conflict"
    title = "Conflict"


class ValidationError(ClaimSaathiError):
    status_code = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)
    error_type = "https://claimsaathi.in/errors/validation"
    title = "Validation Error"


class RateLimitError(ClaimSaathiError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    error_type = "https://claimsaathi.in/errors/rate-limit"
    title = "Too Many Requests"


class StorageError(ClaimSaathiError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    error_type = "https://claimsaathi.in/errors/storage"
    title = "Storage Service Unavailable"


class AIProviderError(ClaimSaathiError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    error_type = "https://claimsaathi.in/errors/ai-provider"
    title = "AI Provider Unavailable"


class ConsentRequiredError(ClaimSaathiError):
    status_code = status.HTTP_451_UNAVAILABLE_FOR_LEGAL_REASONS
    error_type = "https://claimsaathi.in/errors/consent-required"
    title = "Consent Required"


# ---------------------------------------------------------------------------
# Problem+JSON response builder
# ---------------------------------------------------------------------------
def _problem_response(
    status_code: int,
    error_type: str,
    title: str,
    detail: str,
    extra: dict[str, Any] | None = None,
) -> JSONResponse:
    body: dict[str, Any] = {
        "type": error_type,
        "title": title,
        "status": status_code,
        "detail": detail,
        "correlation_id": get_correlation_id(),
    }
    if extra:
        body.update(extra)
    return JSONResponse(
        status_code=status_code,
        content=body,
        media_type="application/problem+json",
    )


# ---------------------------------------------------------------------------
# Global exception handlers — register with register_exception_handlers()
# ---------------------------------------------------------------------------
def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ClaimSaathiError)
    async def claimsaathi_error_handler(
        request: Request, exc: ClaimSaathiError
    ) -> JSONResponse:
        logger.warning(
            "application_error",
            error_type=exc.error_type,
            detail=exc.detail,
            path=str(request.url),
        )
        return _problem_response(
            exc.status_code, exc.error_type, exc.title, exc.detail, exc.extra
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        logger.warning(
            "http_error",
            status_code=exc.status_code,
            detail=exc.detail,
            path=str(request.url),
        )
        return _problem_response(
            exc.status_code,
            f"https://claimsaathi.in/errors/http-{exc.status_code}",
            "HTTP Error",
            str(exc.detail) if exc.detail else "An error occurred",
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Extract field-level errors without leaking internals
        errors = [
            {"field": ".".join(str(l) for l in e["loc"]), "msg": e["msg"]}
            for e in exc.errors()
        ]
        logger.info("validation_error", errors=errors, path=str(request.url))
        return _problem_response(
            getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
            "https://claimsaathi.in/errors/validation",
            "Validation Error",
            "One or more fields are invalid.",
            {"errors": errors},
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        # Log the real error server-side but never expose it to the client
        logger.error(
            "unhandled_exception",
            exc_type=type(exc).__name__,
            # Do NOT log exc args — they may contain sensitive data
            path=str(request.url),
        )
        return _problem_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "https://claimsaathi.in/errors/internal",
            "Internal Server Error",
            "An unexpected error occurred. Quote your correlation_id when contacting support.",
        )
