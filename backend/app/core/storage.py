"""
app/core/storage.py
StorageAdapter interface + MinIO concrete implementation.
Swap implementation by changing STORAGE_BACKEND env var.
Documents are NEVER stored as raw bytes in Postgres.
All client reads use short-TTL signed URLs (never public buckets).
"""
from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from datetime import timedelta
from io import BytesIO
from typing import Protocol

from minio import Minio
from minio.error import S3Error

from app.core.config import get_settings
from app.core.exceptions import StorageError
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


# ---------------------------------------------------------------------------
# Interface (Protocol — structural typing, no inheritance required)
# ---------------------------------------------------------------------------
class StorageAdapter(Protocol):
    """
    Interface for object storage.
    All concrete adapters must implement these methods.
    """

    async def upload(
        self,
        bucket: str,
        object_key: str,
        data: bytes,
        content_type: str,
    ) -> str:
        """Upload data; return the object_key on success."""
        ...

    async def download(self, bucket: str, object_key: str) -> bytes:
        """Download and return raw bytes."""
        ...

    async def signed_read_url(
        self,
        bucket: str,
        object_key: str,
        expire_seconds: int = settings.STORAGE_SIGNED_URL_EXPIRE_SECONDS,
    ) -> str:
        """Return a short-TTL signed URL for client-side reads."""
        ...

    async def delete(self, bucket: str, object_key: str) -> None:
        """Permanently delete an object (used on consent revocation)."""
        ...

    async def exists(self, bucket: str, object_key: str) -> bool:
        """Check if an object exists."""
        ...

    async def health_check(self) -> bool:
        """Return True if storage is reachable."""
        ...


# ---------------------------------------------------------------------------
# MinIO implementation
# ---------------------------------------------------------------------------
class MinioStorageAdapter:
    """
    S3-compatible object storage via MinIO SDK.
    Used for local development; swap to S3Adapter in production
    by setting STORAGE_BACKEND=s3 (same interface).
    """

    def __init__(self) -> None:
        self._client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_USE_SSL,
        )

    async def upload(
        self,
        bucket: str,
        object_key: str,
        data: bytes,
        content_type: str,
    ) -> str:
        try:
            self._client.put_object(
                bucket_name=bucket,
                object_name=object_key,
                data=BytesIO(data),
                length=len(data),
                content_type=content_type,
            )
            logger.info("storage_upload", bucket=bucket, key=object_key, size=len(data))
            return object_key
        except S3Error as e:
            logger.error("storage_upload_failed", bucket=bucket, key=object_key, error=str(e))
            raise StorageError(f"Failed to upload {object_key}: {e}") from e

    async def download(self, bucket: str, object_key: str) -> bytes:
        try:
            response = self._client.get_object(bucket, object_key)
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except S3Error as e:
            raise StorageError(f"Failed to download {object_key}: {e}") from e

    async def signed_read_url(
        self,
        bucket: str,
        object_key: str,
        expire_seconds: int = settings.STORAGE_SIGNED_URL_EXPIRE_SECONDS,
    ) -> str:
        try:
            url = self._client.presigned_get_object(
                bucket_name=bucket,
                object_name=object_key,
                expires=timedelta(seconds=expire_seconds),
            )
            return url
        except S3Error as e:
            raise StorageError(f"Failed to sign URL for {object_key}: {e}") from e

    async def delete(self, bucket: str, object_key: str) -> None:
        try:
            self._client.remove_object(bucket, object_key)
            logger.info("storage_delete", bucket=bucket, key=object_key)
        except S3Error as e:
            raise StorageError(f"Failed to delete {object_key}: {e}") from e

    async def exists(self, bucket: str, object_key: str) -> bool:
        try:
            self._client.stat_object(bucket, object_key)
            return True
        except S3Error:
            return False

    async def health_check(self) -> bool:
        try:
            import asyncio
            await asyncio.to_thread(self._client.list_buckets)
            return True
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Utility: compute SHA-256 checksum for upload integrity verification
# ---------------------------------------------------------------------------
def compute_checksum(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# Factory — instantiate the correct adapter based on config
# ---------------------------------------------------------------------------
def get_storage_adapter() -> MinioStorageAdapter:
    """
    Returns the configured storage adapter.
    Extend this factory to add S3Adapter, GCSAdapter, etc.
    """
    if settings.STORAGE_BACKEND == "minio":
        return MinioStorageAdapter()
    # NOTE: future extension — not implemented
    # elif settings.STORAGE_BACKEND == "s3":
    #     return S3StorageAdapter()
    # elif settings.STORAGE_BACKEND == "gcs":
    #     return GCSStorageAdapter()
    raise NotImplementedError(f"Storage backend not implemented: {settings.STORAGE_BACKEND}")


# Singleton adapter for dependency injection
_storage: MinioStorageAdapter | None = None


def storage() -> MinioStorageAdapter:
    """FastAPI dependency: returns singleton storage adapter."""
    global _storage
    if _storage is None:
        _storage = get_storage_adapter()
    return _storage
