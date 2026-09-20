"""
app/memory/cognee_client.py
Cognee Cloud Knowledge Graph and Memory layer.
Enforces:
- User isolation: dataset is strictly scoped per user (`user_{user_id}`)
- Feature flag: COGNEE_ENABLED toggle with graceful offline degradation
- Data retention / GDPR / DPDP compliance: forget() wipes user dataset
"""
from __future__ import annotations

import re
from typing import Any
import httpx
import structlog

from app.core.config import get_settings

logger = structlog.get_logger(__name__)


def _redact_pii(text: str) -> str:
    """Mask obvious Aadhaar, PAN, phone numbers before external memory ingestion."""
    # Mask 10-digit PAN
    text = re.sub(r"[A-Z]{5}[0-9]{4}[A-Z]", "[REDACTED_PAN]", text)
    # Mask 12-digit Aadhaar
    text = re.sub(r"\b\d{4}\s?\d{4}\s?\d{4}\b", "[REDACTED_AADHAAR]", text)
    # Mask 10-digit Indian phone
    text = re.sub(r"\b[6-9]\d{9}\b", "[REDACTED_PHONE]", text)
    return text


class CogneeClient:
    """Client for Cognee Cloud Memory API with dataset-per-user isolation."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        enabled: bool | None = None,
    ) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.COGNEE_BASE_URL or "https://api.cognee.ai").rstrip("/")
        self.api_key = api_key or settings.COGNEE_API_KEY
        self.enabled = enabled if enabled is not None else settings.COGNEE_ENABLED

        # In-memory mock store for local/testing without cloud connectivity
        self._local_store: dict[str, list[str]] = {}

    @property
    def is_active(self) -> bool:
        return bool(self.enabled and self.api_key and "PASTE" not in self.api_key and "REPLACE" not in self.api_key)

    def _dataset_id(self, user_id: str) -> str:
        """Enforce strict multi-tenant isolation via dataset namespace."""
        clean_id = str(user_id).replace("-", "_")
        return f"user_{clean_id}"

    async def recall(self, user_id: str, query: str, limit: int = 3) -> list[str]:
        """Recall semantically relevant facts from user-scoped knowledge graph."""
        dataset = self._dataset_id(user_id)

        if not self.is_active:
            # Fall back to local store
            items = self._local_store.get(dataset, [])
            matches = [m for m in items if any(q in m.lower() for q in query.lower().split() if len(q) > 3)]
            return matches[:limit] if matches else items[:limit]

        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.post(
                    f"{self.base_url}/api/v1/recall",
                    headers={
                        "X-Api-Key": self.api_key,
                        "Content-Type": "application/json",
                    },
                    json={
                        "query": query,
                        "dataset": dataset,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    results = data if isinstance(data, list) else data.get("results") or data.get("data") or []
                    extracted: list[str] = []
                    for r in results[:limit]:
                        text = r.get("text") or r.get("content") or r.get("answer") or str(r)
                        if text:
                            extracted.append(str(text))
                    return extracted
                else:
                    logger.warning("cognee_recall_non_200", status=resp.status_code)
        except Exception as e:
            logger.warning("cognee_recall_network_error", error=str(e))

        return []

    async def remember(self, user_id: str, fact: str, claim_id: str | None = None) -> bool:
        """Store verified fact into user's isolated dataset after PII redaction."""
        clean_fact = _redact_pii(fact)
        dataset = self._dataset_id(user_id)

        # Store in local fallback
        if dataset not in self._local_store:
            self._local_store[dataset] = []
        if clean_fact not in self._local_store[dataset]:
            self._local_store[dataset].append(clean_fact)

        if not self.is_active:
            return True

        try:
            async with httpx.AsyncClient(timeout=2.5) as client:
                resp = await client.post(
                    f"{self.base_url}/api/v1/remember",
                    headers={
                        "X-Api-Key": self.api_key,
                        "Content-Type": "application/json",
                    },
                    json={
                        "text": clean_fact,
                        "dataset": dataset,
                        "metadata": {"claim_id": claim_id} if claim_id else {},
                    },
                )
                return resp.status_code in {200, 201, 202}
        except Exception as e:
            logger.warning("cognee_remember_network_error", error=str(e))
            return False

    async def forget(self, user_id: str) -> bool:
        """Completely purge all memory and knowledge graph entries for a user."""
        dataset = self._dataset_id(user_id)
        if dataset in self._local_store:
            del self._local_store[dataset]

        if not self.is_active:
            return True

        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.delete(
                    f"{self.base_url}/api/v1/datasets/{dataset}",
                    headers={"X-Api-Key": self.api_key},
                )
                return resp.status_code in {200, 204}
        except Exception as e:
            logger.warning("cognee_forget_error", error=str(e))
            return False


_cognee_instance: CogneeClient | None = None


def get_cognee_client() -> CogneeClient:
    global _cognee_instance
    if _cognee_instance is None:
        _cognee_instance = CogneeClient()
    return _cognee_instance
