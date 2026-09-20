"""
tests/unit/test_copilot_tools.py
Unit tests for Copilot tools: deadlines computation, next-best-action, and policy search.
"""
import datetime
import pytest
from dataclasses import dataclass
from typing import Any
from app.copilot.tools import tool_compute_deadlines, tool_next_best_action


@dataclass
class MockClaim:
    admission_date: Any = None
    discharge_date: Any = None


def test_tool_compute_deadlines():
    today = datetime.date.today()
    admission = today - datetime.timedelta(days=1)
    discharge = today - datetime.timedelta(days=5)

    claim = MockClaim(admission_date=admission, discharge_date=discharge)
    deadlines = tool_compute_deadlines(claim)

    assert len(deadlines) >= 2
    names = [d["name"] for d in deadlines]
    assert "Hospitalization Intimation" in names
    assert "Document Submission Window" in names
    assert "Insurer 30-Day Settlement SLA" in names


def test_tool_next_best_action_for_stages():
    # Stage ONBOARDING with 0 docs
    nba1 = tool_next_best_action("ONBOARDING", {"document_count": 0, "drafts": []})
    assert nba1["action"] == "UPLOAD_DOCUMENTS"

    # Stage CLAIM_PREPARATION
    nba2 = tool_next_best_action("CLAIM_PREPARATION", {"document_count": 3, "drafts": []})
    assert nba2["action"] == "VERIFY_DISCREPANCIES"

    # Stage REJECTED_DECODING
    nba3 = tool_next_best_action("REJECTED_DECODING", {"document_count": 3, "drafts": []})
    assert nba3["action"] == "GENERATE_APPEAL"

    # Any stage with pending draft
    nba4 = tool_next_best_action("POLICY_UNDERSTANDING", {"drafts": [{"status": "DRAFT"}]})
    assert nba4["action"] == "REVIEW_DRAFT"
