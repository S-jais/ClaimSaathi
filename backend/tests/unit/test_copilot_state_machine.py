"""
tests/unit/test_copilot_state_machine.py
Unit tests for the Journey Chatbot state machine.
Verifies legal/illegal transitions, UI stage mappings, and evidence prerequisites.
"""
import pytest
from app.copilot.state_machine import (
    JourneyStage,
    UIStage,
    get_ui_stage,
    allowed_transitions,
    can_transition,
)


def test_ui_stage_mapping():
    """Verify mapping of 9 journey stages to 3 customer-facing UI stages."""
    assert get_ui_stage(JourneyStage.ONBOARDING) == UIStage.UNDERSTAND.value
    assert get_ui_stage(JourneyStage.POLICY_UNDERSTANDING) == UIStage.UNDERSTAND.value
    assert get_ui_stage(JourneyStage.CLAIM_PREPARATION) == UIStage.PREPARE.value
    assert get_ui_stage(JourneyStage.SUBMITTED_TRACKING) == UIStage.PREPARE.value
    assert get_ui_stage(JourneyStage.REJECTED_DECODING) == UIStage.RESOLVE.value
    assert get_ui_stage(JourneyStage.APPEAL_DRAFTING) == UIStage.RESOLVE.value
    assert get_ui_stage(JourneyStage.AWAITING_APPROVAL) == UIStage.RESOLVE.value
    assert get_ui_stage(JourneyStage.ESCALATION) == UIStage.RESOLVE.value
    assert get_ui_stage(JourneyStage.RESOLVED) == UIStage.RESOLVE.value
    # Fallback
    assert get_ui_stage("UNKNOWN_STAGE") == UIStage.UNDERSTAND.value


def test_allowed_transitions():
    """Verify defined legal destinations from each stage."""
    onboarding_allowed = allowed_transitions(JourneyStage.ONBOARDING)
    assert JourneyStage.POLICY_UNDERSTANDING.value in onboarding_allowed
    assert JourneyStage.CLAIM_PREPARATION.value in onboarding_allowed
    assert JourneyStage.REJECTED_DECODING.value in onboarding_allowed
    assert JourneyStage.ESCALATION.value not in onboarding_allowed

    prep_allowed = allowed_transitions(JourneyStage.CLAIM_PREPARATION)
    assert JourneyStage.SUBMITTED_TRACKING.value in prep_allowed
    assert JourneyStage.ESCALATION.value not in prep_allowed


def test_illegal_transitions_blocked():
    """Jumping across unauthorized stages must fail validation."""
    # Cannot jump from ONBOARDING directly to ESCALATION
    ok, err = can_transition(JourneyStage.ONBOARDING, JourneyStage.ESCALATION)
    assert not ok
    assert "Illegal stage transition" in (err or "")

    # Cannot jump from SUBMITTED_TRACKING directly to AWAITING_APPROVAL without decoding & drafting
    ok, err = can_transition(JourneyStage.SUBMITTED_TRACKING, JourneyStage.AWAITING_APPROVAL)
    assert not ok


def test_evidence_prerequisite_for_rejection_decoding():
    """Transitioning to REJECTED_DECODING requires rejection documents or status."""
    # Without evidence
    ok, err = can_transition(
        JourneyStage.ONBOARDING,
        JourneyStage.REJECTED_DECODING,
        evidence={"has_rejection_reasons": False, "claim_status": "draft"},
    )
    assert not ok
    assert "requires a rejection letter" in (err or "")

    # With evidence
    ok, err = can_transition(
        JourneyStage.ONBOARDING,
        JourneyStage.REJECTED_DECODING,
        evidence={"has_rejection_reasons": True},
    )
    assert ok
    assert err is None


def test_evidence_prerequisite_for_awaiting_approval():
    """Transitioning to AWAITING_APPROVAL requires an existing draft."""
    # Without draft
    ok, err = can_transition(
        JourneyStage.APPEAL_DRAFTING,
        JourneyStage.AWAITING_APPROVAL,
        evidence={"has_draft": False},
    )
    assert not ok
    assert "requires an existing generated" in (err or "")

    # With draft
    ok, err = can_transition(
        JourneyStage.APPEAL_DRAFTING,
        JourneyStage.AWAITING_APPROVAL,
        evidence={"has_draft": True},
    )
    assert ok
    assert err is None
