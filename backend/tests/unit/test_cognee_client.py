"""
tests/unit/test_cognee_client.py
Unit tests for Cognee memory client:
- Strict multi-tenant user dataset isolation
- PII redaction before ingestion
- Offline graceful degradation when COGNEE_ENABLED=false
- User data purging via forget()
"""
import pytest
from app.memory.cognee_client import CogneeClient, _redact_pii


def test_pii_redaction():
    text = "Patient Rahul PAN ABCDE1234F Aadhaar 1234 5678 9012 Phone 9876543210 admitted."
    redacted = _redact_pii(text)
    assert "ABCDE1234F" not in redacted
    assert "[REDACTED_PAN]" in redacted
    assert "1234 5678 9012" not in redacted
    assert "[REDACTED_AADHAAR]" in redacted
    assert "9876543210" not in redacted
    assert "[REDACTED_PHONE]" in redacted


@pytest.mark.asyncio
async def test_cognee_user_dataset_isolation():
    client = CogneeClient(enabled=False)

    user_a = "11111111-1111-1111-1111-111111111111"
    user_b = "22222222-2222-2222-2222-222222222222"

    # Remember fact for user A
    await client.remember(user_a, "User A had knee surgery at Apollo Hospital on 12 Feb 2026.")

    # Remember fact for user B
    await client.remember(user_b, "User B submitted cataract claim for ₹40,000.")

    # User A recall
    results_a = await client.recall(user_a, "knee surgery")
    assert any("knee surgery" in r for r in results_a)
    assert not any("cataract" in r for r in results_a)

    # User B recall
    results_b = await client.recall(user_b, "cataract")
    assert any("cataract" in r for r in results_b)
    assert not any("knee surgery" in r for r in results_b)


@pytest.mark.asyncio
async def test_cognee_forget_purges_memory():
    client = CogneeClient(enabled=False)
    user_id = "33333333-3333-3333-3333-333333333333"

    await client.remember(user_id, "User fact to be deleted.")
    before = await client.recall(user_id, "deleted")
    assert len(before) > 0

    success = await client.forget(user_id)
    assert success is True

    after = await client.recall(user_id, "deleted")
    assert len(after) == 0
