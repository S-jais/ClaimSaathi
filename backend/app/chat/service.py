"""
app/chat/service.py
ClaimSaathi AI Chatbot — powered by Cognee Cloud + Gemini 2.5 Flash.
Uses the new google-genai SDK (google.generativeai is deprecated).
Falls back to smart mock when keys are unavailable.
"""
from __future__ import annotations

import asyncio
import os
from typing import AsyncGenerator

import httpx
from dotenv import load_dotenv

load_dotenv()

from app.core.logging import get_logger

logger = get_logger(__name__)

# System prompt — claim-scoped, IRDAI grounded
SYSTEM_PROMPT = """You are ClaimSaathi Companion, an AI assistant exclusively focused on helping 
Indian health insurance policyholders understand their claims, policy clauses, and rights.

You are grounded in:
- IRDAI Master Circular on Protection of Policyholders' Interests 2024
- Insurance Ombudsman Rules 2017
- Insurance Act 1938 (as amended)

The current active claim context:
- Claim Reference: CLM-20491 (Star Health MediClassic Individual)
- Policy: #SH-884920, incepted 12 March 2018 (78 months continuous)
- Procedure: Total Knee Replacement (Left) — Apollo Hospital, Bengaluru
- Claim Amount: Rs.1,84,500
- Status: Repudiated by insurer citing Clause 4.2 (24-month waiting period)
- Key Legal Protection: IRDAI 2024 Chapter V, Section 5.3 — 60-Month Moratorium

CRITICAL RULES:
1. NEVER predict claim approval probability or guarantee financial outcomes
2. Always end with: "Final claim decision remains solely with the insurer."
3. Provide factual, legally grounded guidance only
4. If asked about other topics, politely redirect to insurance claims
5. Respond in the same language as the user (Hindi or English)
6. Keep responses concise and actionable
"""


def _get_gemini_client():
    """Return configured google-genai client (new SDK)."""
    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    model_name = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    
    if not gemini_key or "PASTE" in gemini_key:
        return None, None
    
    try:
        from google import genai  # type: ignore[import]
        from google.genai import types  # type: ignore[import]
        client = genai.Client(api_key=gemini_key)
        return client, model_name
    except ImportError:
        # Try old SDK as fallback
        try:
            import google.generativeai as genai_old  # type: ignore[import]
            genai_old.configure(api_key=gemini_key)
            return genai_old, model_name
        except ImportError:
            logger.warning("no_gemini_sdk_installed")
            return None, None


async def _query_cognee(question: str, claim_id: str) -> str | None:
    """Try Cognee Cloud recall for knowledge-graph grounded context."""
    cognee_url = os.environ.get("COGNEE_SERVICE_URL", "")
    cognee_key = os.environ.get("COGNEE_API_KEY", "")
    
    if not cognee_url or not cognee_key or "PASTE" in cognee_key or "REPLACE" in cognee_key:
        return None

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{cognee_url.rstrip('/')}/api/v1/recall",
                headers={
                    "X-Api-Key": cognee_key,
                    "Content-Type": "application/json",
                },
                json={"query": question},
            )
            if resp.status_code == 200:
                data = resp.json()
                # Cognee recall returns list of results
                results = data if isinstance(data, list) else data.get("results") or data.get("data") or []
                if results:
                    context = "\n".join(
                        str(r.get("text") or r.get("content") or r.get("answer") or str(r))
                        for r in results[:3]
                        if r
                    )
                    if context.strip():
                        logger.info("cognee_context_retrieved", chars=len(context))
                        return context
            else:
                logger.warning("cognee_recall_status", status=resp.status_code)
    except Exception as e:
        logger.warning("cognee_recall_failed", error=str(e))
    return None


def _sync_gemini_stream(client, model_name: str, messages: list[dict], question: str):
    """Synchronous Gemini streaming call — run in executor."""
    try:
        # New google-genai SDK
        from google import genai as new_genai  # type: ignore[import]
        from google.genai import types as genai_types  # type: ignore[import]

        # Build chat history
        history = []
        for msg in messages[-6:]:
            role = "user" if msg.get("role") == "user" else "model"
            history.append(
                new_genai.types.Content(
                    role=role,
                    parts=[new_genai.types.Part(text=msg.get("content", ""))]
                )
            )

        chat = client.chats.create(
            model=model_name,
            config=new_genai.types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.3,
                max_output_tokens=1024,
            ),
            history=history,
        )
        response = chat.send_message_stream(question)
        chunks = []
        for chunk in response:
            if chunk.text:
                chunks.append(chunk.text)
        return "".join(chunks)

    except (ImportError, AttributeError):
        # Fallback to old SDK
        import google.generativeai as old_genai  # type: ignore[import]
        model = old_genai.GenerativeModel(
            model_name=model_name,
            system_instruction=SYSTEM_PROMPT,
            generation_config=old_genai.types.GenerationConfig(
                temperature=0.3,
                max_output_tokens=1024,
            ),
        )
        hist = []
        for msg in messages[-6:]:
            role = "user" if msg.get("role") == "user" else "model"
            hist.append({"role": role, "parts": [msg.get("content", "")]})

        chat = model.start_chat(history=hist)
        response = chat.send_message(question, stream=False)
        return response.text or ""


async def chat_stream(
    question: str,
    claim_id: str = "CLM-20491",
    history: list[dict] | None = None,
) -> AsyncGenerator[str, None]:
    """Stream chat response: Cognee context → Gemini 2.5 Flash → SSE chunks."""
    history = history or []

    # Step 1: Cognee context (non-blocking)
    cognee_context = await _query_cognee(question, claim_id)

    # Step 2: Augment question with context
    augmented = question
    if cognee_context:
        augmented = (
            f"Using this claim knowledge context:\n{cognee_context}\n\n"
            f"Answer this question: {question}"
        )

    # Step 3: Gemini response
    client, model_name = _get_gemini_client()

    if client is None:
        # No Gemini key — smart mock
        yield _mock_chat_response(question)
        return

    try:
        loop = asyncio.get_event_loop()
        full_response = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                _sync_gemini_stream,
                client,
                model_name,
                history,
                augmented,
            ),
            timeout=45.0,
        )
        # Simulate streaming by yielding in chunks for typewriter effect
        words = full_response.split(" ")
        chunk_size = 4
        for i in range(0, len(words), chunk_size):
            yield " ".join(words[i:i + chunk_size]) + " "
            await asyncio.sleep(0.02)

    except asyncio.TimeoutError:
        yield "Request timed out. Please try again.\n\n---\n*AI guidance only. Final claim decision remains with the insurer.*"
    except Exception as e:
        logger.error("gemini_chat_failed", error=str(e))
        yield _mock_chat_response(question)


def _mock_chat_response(question: str) -> str:
    """Smart deterministic fallback when no Gemini key configured."""
    q = question.lower()
    if "reject" in q or "clause 4" in q or "repudiat" in q or "why" in q:
        return (
            "Your claim CLM-20491 was repudiated under **Clause 4.2** (24-month waiting period for joint replacement). "
            "However, your policy has been continuously active for **78 months** since March 2018.\n\n"
            "Under **IRDAI Master Circular 2024, Chapter V, Section 5.3** — after 60 continuous months of coverage, "
            "no claim can be repudiated on waiting-period grounds. "
            "This repudiation directly violates the statutory moratorium.\n\n"
            "**Action:** File a formal grievance to the insurer's GRO citing the IRDAI 2024 moratorium.\n\n"
            "---\n*AI guidance only. Final claim decision remains with the insurer.*"
        )
    elif "moratorium" in q or "irdai" in q or "60" in q:
        return (
            "**IRDAI 60-Month Moratorium (Chapter V, Section 5.3):**\n\n"
            "After 60 continuous months of health insurance coverage, insurers **cannot** repudiate claims on grounds of:\n"
            "- Non-disclosure of pre-existing conditions\n"
            "- Waiting period exclusions\n\n"
            "Your policy has **78 months** of continuous coverage — exceeding this by 18 months. "
            "The Clause 4.2 waiting period is legally inapplicable.\n\n"
            "---\n*AI guidance only. Final claim decision remains with the insurer.*"
        )
    elif "document" in q or "missing" in q or "icp" in q:
        return (
            "**Missing document for CLM-20491:**\n\n"
            "Only one gap: **Indoor Case Papers (ICPs) / OT Notes**\n\n"
            "**Action:** Contact Apollo Hospital's Medical Records Department (MRD) and request "
            "certified ICPs for admission Feb 10–14, 2026. All other 5 documents are verified.\n\n"
            "---\n*AI guidance only. Final claim decision remains with the insurer.*"
        )
    elif "reimburse" in q or "calculat" in q or "waterfall" in q or "payable" in q or "estimate" in q:
        return (
            "**Indicative Payable Estimate Breakdown:**\n\n"
            "- **Gross Hospital Bill:** ₹73,000.00\n"
            "- **Less: IRDAI Non-Payables:** -₹5,000.00 (Gloves, PPE, Registration & Bio-waste)\n"
            "- **Less: Room Rent Adjustment:** ₹0.00 (Tariff within policy limits)\n"
            "- **Less: Policy Co-Payment (10%):** -₹6,800.00\n\n"
            "👉 **Indicative payable estimate — subject to your insurer's assessment:** **₹61,200.00**\n\n"
            "*Note: Computed deterministically according to your policy terms and IRDAI 2024 guidelines.*\n\n"
            "---\n*AI guidance only. Final claim decision remains with the insurer.*"
        )
    elif "non-medical" in q or "consumable" in q or "deduct" in q or "glove" in q or "ppe" in q:
        return (
            "**Commonly Non-Payable Deductions (IRDAI Annexure I, List I):**\n\n"
            "Under IRDAI standardization regulations, certain items are classified as hospital operational consumables:\n\n"
            "1. **Gloves & PPE Kits (IRDAI-NP-001 & 002):** Routine personal protective gear for hospital staff is treated as institutional overhead unless bundled into a surgical package.\n"
            "2. **Registration & MRD Fees (IRDAI-NP-004):** Administrative fees cannot be passed to insurance.\n"
            "3. **Bio-Medical Waste Levy (IRDAI-NP-005):** Environmental statutory levies are hospital overheads.\n\n"
            "**Patient Remedy:** If gloves or PPE were procedure-critical in an ICU or specialized OT, request the hospital billing desk for an itemized surgical certificate.\n\n"
            "---\n*AI guidance only. Final claim decision remains with the insurer.*"
        )
    elif "appeal" in q or "gro" in q or "ombudsman" in q:
        return (
            "**Your appeal path:**\n\n"
            "1. **Day 1 →** File with Star Health's Grievance Redressal Officer (GRO), citing IRDAI 2024 Chapter V\n"
            "2. **Attach** renewal receipts 2018–2026 proving 78 months continuous coverage\n"
            "3. **Day 30 →** If no resolution, escalate to Insurance Ombudsman (Bengaluru) under Rule 17\n\n"
            "Use the **Appeal Builder** tab to auto-generate your legally-grounded letter.\n\n"
            "---\n*AI guidance only. Final claim decision remains with the insurer.*"
        )
    else:
        return (
            "I'm your **ClaimSaathi AI Companion**, scoped to claim CLM-20491.\n\n"
            "I can help with:\n"
            "- Why your claim was rejected and your legal rights\n"
            "- The IRDAI 60-month moratorium\n"
            "- Missing documents and how to get them\n"
            "- Filing an appeal with the GRO or Ombudsman\n\n"
            "---\n*AI guidance only. Final claim decision remains with the insurer.*"
        )


async def chat_once(
    question: str,
    claim_id: str = "CLM-20491",
    history: list[dict] | None = None,
) -> str:
    """Non-streaming version."""
    chunks = []
    async for chunk in chat_stream(question, claim_id, history):
        chunks.append(chunk)
    return "".join(chunks)
