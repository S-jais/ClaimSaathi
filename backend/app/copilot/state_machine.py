"""
app/copilot/state_machine.py
Deterministic Journey State Machine for the ClaimSaathi Copilot.
Enforces valid stage transitions and evidence prerequisites:
ONBOARDING -> POLICY_UNDERSTANDING -> CLAIM_PREPARATION -> SUBMITTED_TRACKING
           -> REJECTED_DECODING -> APPEAL_DRAFTING -> AWAITING_APPROVAL -> ESCALATION -> RESOLVED
"""
from __future__ import annotations

from enum import Enum
from typing import Any


class JourneyStage(str, Enum):
    ONBOARDING = "ONBOARDING"
    POLICY_UNDERSTANDING = "POLICY_UNDERSTANDING"
    CLAIM_PREPARATION = "CLAIM_PREPARATION"
    SUBMITTED_TRACKING = "SUBMITTED_TRACKING"
    REJECTED_DECODING = "REJECTED_DECODING"
    APPEAL_DRAFTING = "APPEAL_DRAFTING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    ESCALATION = "ESCALATION"
    RESOLVED = "RESOLVED"


class UIStage(str, Enum):
    UNDERSTAND = "Understand"
    PREPARE = "Prepare"
    RESOLVE = "Resolve"


# 3-step customer-facing UI mapping
STAGE_TO_UI_MAP: dict[JourneyStage, UIStage] = {
    JourneyStage.ONBOARDING: UIStage.UNDERSTAND,
    JourneyStage.POLICY_UNDERSTANDING: UIStage.UNDERSTAND,
    JourneyStage.CLAIM_PREPARATION: UIStage.PREPARE,
    JourneyStage.SUBMITTED_TRACKING: UIStage.PREPARE,
    JourneyStage.REJECTED_DECODING: UIStage.RESOLVE,
    JourneyStage.APPEAL_DRAFTING: UIStage.RESOLVE,
    JourneyStage.AWAITING_APPROVAL: UIStage.RESOLVE,
    JourneyStage.ESCALATION: UIStage.RESOLVE,
    JourneyStage.RESOLVED: UIStage.RESOLVE,
}

# Permitted state transitions
TRANSITIONS: dict[JourneyStage, set[JourneyStage]] = {
    JourneyStage.ONBOARDING: {
        JourneyStage.POLICY_UNDERSTANDING,
        JourneyStage.CLAIM_PREPARATION,
        JourneyStage.REJECTED_DECODING,
    },
    JourneyStage.POLICY_UNDERSTANDING: {
        JourneyStage.CLAIM_PREPARATION,
        JourneyStage.REJECTED_DECODING,
        JourneyStage.RESOLVED,
    },
    JourneyStage.CLAIM_PREPARATION: {
        JourneyStage.SUBMITTED_TRACKING,
        JourneyStage.POLICY_UNDERSTANDING,
        JourneyStage.RESOLVED,
    },
    JourneyStage.SUBMITTED_TRACKING: {
        JourneyStage.REJECTED_DECODING,
        JourneyStage.RESOLVED,
        JourneyStage.CLAIM_PREPARATION,
    },
    JourneyStage.REJECTED_DECODING: {
        JourneyStage.APPEAL_DRAFTING,
        JourneyStage.POLICY_UNDERSTANDING,
        JourneyStage.RESOLVED,
    },
    JourneyStage.APPEAL_DRAFTING: {
        JourneyStage.AWAITING_APPROVAL,
        JourneyStage.REJECTED_DECODING,
    },
    JourneyStage.AWAITING_APPROVAL: {
        JourneyStage.ESCALATION,
        JourneyStage.APPEAL_DRAFTING,
        JourneyStage.RESOLVED,
    },
    JourneyStage.ESCALATION: {
        JourneyStage.RESOLVED,
        JourneyStage.AWAITING_APPROVAL,
    },
    JourneyStage.RESOLVED: {
        JourneyStage.POLICY_UNDERSTANDING,
        JourneyStage.APPEAL_DRAFTING,
    },
}


def get_ui_stage(stage: str | JourneyStage) -> str:
    """Return customer-facing high-level stage: Understand, Prepare, or Resolve."""
    try:
        j_stage = JourneyStage(stage)
        return STAGE_TO_UI_MAP[j_stage].value
    except (ValueError, KeyError):
        return UIStage.UNDERSTAND.value


def allowed_transitions(current_stage: str | JourneyStage) -> set[str]:
    """Return set of stage names that are valid immediate destinations."""
    try:
        j_stage = JourneyStage(current_stage)
        return {s.value for s in TRANSITIONS.get(j_stage, set())}
    except ValueError:
        return set()


def can_transition(
    current_stage: str | JourneyStage,
    target_stage: str | JourneyStage,
    evidence: dict[str, Any] | None = None,
) -> tuple[bool, str | None]:
    """
    Evaluate if transitioning to target_stage is valid both structurally
    and with necessary evidence prerequisites.
    """
    evidence = evidence or {}
    try:
        c_stage = JourneyStage(current_stage)
        t_stage = JourneyStage(target_stage)
    except ValueError as e:
        return False, f"Invalid stage identifier: {e}"

    if t_stage == c_stage:
        return True, None

    if t_stage not in TRANSITIONS.get(c_stage, set()):
        return False, f"Illegal stage transition from {c_stage.value} to {t_stage.value}"

    # Check evidence prerequisites
    if t_stage == JourneyStage.REJECTED_DECODING:
        has_rejection = (
            evidence.get("has_rejection_reasons", False)
            or evidence.get("has_rejection_document", False)
            or evidence.get("claim_status") in {"rejected", "partially_approved", "query_raised"}
        )
        if not has_rejection:
            return False, "Transition to REJECTED_DECODING requires a rejection letter, deduction reason, or query from insurer."

    elif t_stage == JourneyStage.APPEAL_DRAFTING:
        has_decoded = (
            evidence.get("has_rejection_reasons", False)
            or evidence.get("rejection_decoded", False)
            or evidence.get("has_dispute_basis", False)
        )
        if not has_decoded:
            return False, "Transition to APPEAL_DRAFTING requires a decoded rejection reason or dispute basis."

    elif t_stage == JourneyStage.AWAITING_APPROVAL:
        if not evidence.get("has_draft", False):
            return False, "Transition to AWAITING_APPROVAL requires an existing generated appeal/grievance draft."

    elif t_stage == JourneyStage.ESCALATION:
        if not evidence.get("has_rejected_appeal", False) and not evidence.get("grievance_unresolved", False):
            # Allow escalation if formal internal grievance was already lodged or appeal draft approved
            pass

    return True, None
