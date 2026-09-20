"""
app/copilot/n8n_dispatcher.py
Lightweight async dispatcher for n8n automation workflows.
Workflows:
1. document_ocr_ingest
2. grievance_package_build
3. deadline_reminder_schedule
Degrades gracefully if n8n webhook endpoint is unavailable.
"""
from __future__ import annotations

import asyncio
from typing import Any
import httpx
import structlog

from app.core.config import get_settings

logger = structlog.get_logger(__name__)


async def trigger_n8n_workflow(
    workflow_name: str,
    payload: dict[str, Any],
    timeout_seconds: float = 2.0,
) -> bool:
    """
    Fire-and-forget webhook dispatcher to local or remote n8n instance.
    Logs success or graceful failure without interrupting main user request flow.
    """
    settings = get_settings()
    base_url = settings.N8N_WEBHOOK_BASE_URL.rstrip("/")
    url = f"{base_url}/{workflow_name}"

    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            resp = await client.post(
                url,
                headers={
                    "Content-Type": "application/json",
                    "X-ClaimSaathi-Secret": settings.N8N_SERVICE_SECRET,
                },
                json=payload,
            )
            if resp.status_code in {200, 201, 202}:
                logger.info("n8n_workflow_triggered", workflow=workflow_name, status=resp.status_code)
                return True
            logger.debug("n8n_workflow_response", workflow=workflow_name, status=resp.status_code)
    except Exception as e:
        logger.debug("n8n_workflow_not_reachable", workflow=workflow_name, error=str(e))

    return False


def dispatch_workflow_async(workflow_name: str, payload: dict[str, Any]) -> None:
    """Non-blocking fire-and-forget trigger using background task."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(trigger_n8n_workflow(workflow_name, payload))
    except RuntimeError:
        pass
