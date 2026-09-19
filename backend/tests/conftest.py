"""
tests/conftest.py
Shared pytest fixtures for all test types.
"""
from __future__ import annotations

import os
import pytest

# Force mock adapter in all tests unless explicitly overridden
os.environ.setdefault("LLM_PROVIDER", "mock")
os.environ.setdefault("OCR_ADAPTER", "mock")
os.environ.setdefault("STORAGE_BACKEND", "minio")
os.environ.setdefault("SECRET_KEY", "test_secret_key_32_characters_minimum!")
os.environ.setdefault("N8N_SERVICE_SECRET", "test_n8n_secret_32_characters_min!")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://claimsaathi:claimsaathi_dev@localhost:5432/claimsaathi_test")
os.environ.setdefault("DATABASE_URL_SYNC", "postgresql://claimsaathi:claimsaathi_dev@localhost:5432/claimsaathi_test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")  # DB 1 for tests
