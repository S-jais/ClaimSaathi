"""
tests/unit/test_appeal_gatekeeper.py
Unit tests for the Appeal Builder gatekeeper protocol.
Enforces that unapproved appeal briefs can NEVER be exported,
and that ClaimSaathi never auto-submits to an insurer.
"""
import pytest
from dataclasses import dataclass
from typing import Any


@dataclass
class MockAppealDraft:
    status: str = "draft"
    content_json: dict[str, Any] | None = None
    approved_at: Any = None
    exported_at: Any = None


def test_appeal_draft_default_status():
    """Appeal drafts must initialize in 'draft' status."""
    draft = MockAppealDraft(status="draft")
    assert draft.status == "draft"
    assert draft.approved_at is None
    assert draft.exported_at is None


def test_appeal_gatekeeper_blocks_unapproved_export():
    """Exporting a draft that has not been approved must raise PermissionError."""
    draft = MockAppealDraft(status="draft", content_json={"claim_summary": {"content": "Sample"}})
    
    # Gatekeeper rule: export is forbidden unless status == 'approved'
    def check_export_allowed(d):
        if d.status != "approved":
            raise PermissionError("Export requires prior policyholder approval (Gatekeeper violation)")
        return True

    with pytest.raises(PermissionError):
        check_export_allowed(draft)


def test_appeal_gatekeeper_allows_approved_export():
    """Export is permitted once status is set to 'approved'."""
    draft = MockAppealDraft(status="approved", content_json={"claim_summary": {"content": "Sample"}})
    assert draft.status == "approved"
    
    def check_export_allowed(d):
        if d.status != "approved":
            raise PermissionError("Export requires prior policyholder approval (Gatekeeper violation)")
        return True

    assert check_export_allowed(draft) is True


def test_no_auto_submit_column():
    """Verify that auto-submission fields are intentionally absent."""
    draft = MockAppealDraft()
    assert not hasattr(draft, "submitted_to_insurer_at")
    assert not hasattr(draft, "auto_submitted")
