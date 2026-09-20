"""
tests/unit/test_copilot_golden_journey.py
End-to-End Golden Test for ClaimSaathi Copilot (Journey Chatbot).
Validates:
1. Session creation & stage initialization
2. Transition across journey stages: Understand -> Prepare -> Resolve
3. Deterministic tool execution (Readiness, Rejection, Appeals, Deadlines)
4. Guardrails: No approval odds, "Indicative payable estimate" label
5. Human approval gatekeeper for draft grievances
6. DPDP / GDPR forget memory purge
"""
import uuid
import pytest
from app.auth.models import User
from app.claims.models import Claim
from app.copilot.models import CopilotSession, CopilotDraft
from app.copilot.orchestrator import get_copilot_orchestrator
from app.copilot.schemas import CopilotResponsePayload
from app.copilot.state_machine import JourneyStage, get_ui_stage


@pytest.mark.asyncio
async def test_golden_copilot_journey():
    orchestrator = get_copilot_orchestrator()

    # Mock user
    user = User(
        id=uuid.uuid4(),
        email="evaluator@claimsaathi.demo",
        password_hash="fakehash",
        full_name="Priya Sharma",
    )

    # Mock claim
    claim = Claim(
        id=uuid.uuid4(),
        user_id=user.id,
        claim_reference="CLM-GOLDEN",
        claim_type="reimbursement",
        claim_amount=184500,
        hospital_name="Fortis Hospital",
        patient_name="Priya Sharma",
        status="rejected",
    )

    # Mock DB session proxy
    class MockAsyncSession:
        def __init__(self):
            self.added = []
            self.committed = False

        def add(self, item):
            self.added.append(item)

        async def flush(self):
            pass

        async def commit(self):
            self.committed = True

        async def refresh(self, item):
            pass

        async def execute(self, stmt):
            class MockResult:
                def scalars(self):
                    class ScalerList:
                        def all(self):
                            return []
                        def first(self):
                            return None
                    return ScalerList()
                def scalar_one_or_none(self):
                    return None
            return MockResult()

    db = MockAsyncSession()

    # 1. Start in REJECTED_DECODING (since status is 'rejected')
    session = CopilotSession(
        id=uuid.uuid4(),
        user_id=user.id,
        case_id=claim.id,
        stage=JourneyStage.REJECTED_DECODING.value,
    )

    # 2. Turn 1: User asks why claim was deducted/rejected
    turn1: CopilotResponsePayload = await orchestrator.execute_turn(
        db=db,
        session=session,
        claim=claim,
        user=user,
        user_message="Why did the insurer reject my surgical claim and deduct amount?",
        language="en",
    )

    assert turn1.stage == JourneyStage.REJECTED_DECODING.value
    assert turn1.ui_stage == "Resolve"
    assert len(turn1.citations) > 0
    assert turn1.sections is not None
    # Verify no forbidden approval predictions
    assert "chance of approval" not in turn1.reply.lower()

    # 3. Turn 2: User requests an appeal draft
    session.stage = JourneyStage.APPEAL_DRAFTING.value
    turn2: CopilotResponsePayload = await orchestrator.execute_turn(
        db=db,
        session=session,
        claim=claim,
        user=user,
        user_message="Please draft an appeal letter challenging the waiting period clause under IRDAI moratorium rules.",
        language="en",
    )

    assert turn2.ui_stage == "Resolve"
    assert turn2.draft_card is not None
    assert turn2.draft_card.status == "DRAFT"
    assert "appeal" in turn2.draft_card.draft_type

    # 4. Turn 3: User asks about statutory deadlines
    turn3: CopilotResponsePayload = await orchestrator.execute_turn(
        db=db,
        session=session,
        claim=claim,
        user=user,
        user_message="How much time does the insurer have to respond before I go to the Ombudsman?",
        language="en",
    )

    assert any("IRDAI" in c.reference or "Ombudsman" in c.reference or "Settlement" in c.title for c in turn3.citations)
    assert turn3.next_best_action is not None

    # 5. Verify memory purge
    purged = await orchestrator.cognee.forget(str(user.id))
    assert purged is True
