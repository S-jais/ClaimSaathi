"""
app/core/config.py
Centralised configuration via Pydantic Settings.
All values come from environment variables (or .env file in dev).
Never access os.environ directly — use settings.FIELD_NAME.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- App ---
    APP_ENV: Literal["development", "staging", "production"] = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    SECRET_KEY: str = Field(..., min_length=32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",")]
        return v

    # --- Database ---
    DATABASE_URL: str  # async: postgresql+asyncpg://...
    DATABASE_URL_SYNC: str  # sync: postgresql://... (for Alembic)

    # --- Redis ---
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL_SECONDS: int = 3600

    # --- Object Storage ---
    STORAGE_BACKEND: Literal["minio", "s3", "gcs"] = "minio"
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "claimsaathi_minio"
    MINIO_SECRET_KEY: str = "claimsaathi_minio_secret"
    MINIO_BUCKET_DOCUMENTS: str = "claimsaathi-documents"
    MINIO_BUCKET_EXPORTS: str = "claimsaathi-exports"
    MINIO_USE_SSL: bool = False
    STORAGE_SIGNED_URL_EXPIRE_SECONDS: int = 900

    # --- LLM ---
    LLM_PROVIDER: Literal["openai", "gemini", "mock"] = "openai"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-pro"

    # --- OCR ---
    OCR_ADAPTER: Literal["mock", "google_document_ai"] = "mock"
    GOOGLE_CLOUD_PROJECT: str = ""
    GOOGLE_DOCUMENT_AI_PROCESSOR_ID: str = ""
    GOOGLE_APPLICATION_CREDENTIALS: str = ""
    OCR_CONFIDENCE_THRESHOLD: float = 0.70

    # --- n8n / Internal service auth ---
    N8N_SERVICE_SECRET: str = Field(..., min_length=32)
    N8N_WEBHOOK_BASE_URL: str = "http://n8n:5678/webhook"
    BACKEND_INTERNAL_BASE_URL: str = "http://backend:8000/internal"

    # --- Notifications ---
    NOTIFICATION_EMAIL_ENABLED: bool = False
    SENDGRID_API_KEY: str = ""
    NOTIFICATION_FROM_EMAIL: str = "noreply@claimsaathi.demo"
    NOTIFICATION_FROM_NAME: str = "ClaimSaathi"

    # --- Security / Rate limits ---
    RATE_LIMIT_AUTH_PER_MINUTE: int = 10
    RATE_LIMIT_UPLOAD_PER_MINUTE: int = 20
    RATE_LIMIT_AI_PER_MINUTE: int = 5
    MAX_UPLOAD_SIZE_MB: int = 25
    ALLOWED_MIME_TYPES: list[str] = [
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/tiff",
    ]

    @field_validator("ALLOWED_MIME_TYPES", mode="before")
    @classmethod
    def parse_mime_types(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [m.strip() for m in v.split(",")]
        return v

    # --- Logging ---
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: Literal["json", "text"] = "json"

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"


@lru_cache
def get_settings() -> Settings:
    """Return cached Settings singleton. Use as a FastAPI dependency."""
    return Settings()  # type: ignore[call-arg]
