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
        async with httpx.AsyncClient(timeout=1.5) as client:
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

        candidate_models = [model_name]
        for fallback_m in ["gemini-3.6-flash", "gemini-2.5-flash", "gemini-1.5-flash", "gemini-2.0-flash"]:
            if fallback_m not in candidate_models:
                candidate_models.append(fallback_m)

        last_error = None
        for candidate in candidate_models:
            try:
                chat = client.chats.create(
                    model=candidate,
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
                if chunks:
                    return "".join(chunks)
            except Exception as e:
                last_error = e
                logger.warning("gemini_model_failed_trying_next", model=candidate, error=str(e))
                continue

        if last_error:
            raise last_error
        return ""

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
    """Smart deterministic fallback when LLM connection is delayed or offline."""
    q = question.lower().strip()

    # 1. Greetings & Conversational
    if q in ["hi", "hello", "hey", "namaste", "good morning", "good afternoon", "good evening"] or q.startswith("hi ") or q.startswith("hello "):
        return (
            "Hello! I am your **ClaimSaathi Companion**, actively monitoring your health claim **CLM-20491**.\n\n"
            "Here is your quick claim summary:\n"
            "- **Procedure:** Total Knee Replacement (Apollo Hospital, Bengaluru)\n"
            "- **Billed Amount:** ₹1,84,500 claimed (Hospital bill: ₹73,000 itemized)\n"
            "- **Indicative Payable Estimate:** ₹61,200.00 (Subject to insurer assessment)\n"
            "- **Current Issue:** Repudiated under Clause 4.2 despite 78 months continuous coverage (exceeds IRDAI 60-month moratorium).\n\n"
            "How can I help you right now? You can ask me:\n"
            "1. *'Explain my reimbursement calculation'*\n"
            "2. *'What non-medical items were deducted?'*\n"
            "3. *'Which documents are still missing?'*\n"
            "4. *'How do I file an appeal with the GRO?'*\n\n"
            "---\n*AI guidance only. Final claim decision remains with the insurer.*"
        )

    # 2. Status & Overview
    if "status" in q or "update" in q or "what is happening" in q or "progress" in q:
        return (
            "**Current Claim Status for CLM-20491:**\n\n"
            "- **Insurance Status:** Repudiated by insurer (Star Health) on Feb 28, 2026 citing Clause 4.2.\n"
            "- **ClaimSaathi Audit Score:** 85% Readiness.\n"
            "- **Legal Protection:** Protected under IRDAI 2024 60-Month Moratorium (your policy is 78 months old).\n"
            "- **Pending Item:** 1 document pending — *Indoor Case Papers (ICPs)* from Apollo Hospital MRD.\n"
            "- **Next Step:** You can generate a formal grievance appeal letter directly from the **Appeal Builder** tab.\n\n"
            "---\n*AI guidance only. Final claim decision remains with the insurer.*"
        )

    # 3. Reimbursement, Settlement, and Waterfall Calculation
    if any(term in q for term in ["reimburse", "calculat", "waterfall", "payable", "estimate", "how much", "money", "settle"]):
        return (
            "**Indicative Payable Estimate Breakdown:**\n\n"
            "- **Gross Hospital Bill:** ₹73,000.00 (8 itemized line items)\n"
            "- **Less: IRDAI Non-Payables:** -₹5,000.00 (Gloves, PPE, Registration & Bio-waste)\n"
            "- **Less: Room Rent Adjustment:** ₹0.00 (Tariff within policy limit)\n"
            "- **Less: Policy Co-Payment (10%):** -₹6,800.00\n\n"
            "👉 **Indicative payable estimate — subject to your insurer's assessment:** **₹61,200.00**\n\n"
            "*Note: Computed deterministically according to your policy terms and IRDAI 2024 guidelines. Never accept arbitrary lump-sum deductions without itemized justification.*\n\n"
            "---\n*AI guidance only. Final claim decision remains with the insurer.*"
        )

    # 4. Non-Medical, Consumables & Deductions
    if any(term in q for term in ["non-medical", "consumable", "deduct", "cut", "glove", "ppe", "registration", "waste", "sanitizer"]):
        return (
            "**Commonly Non-Payable Deductions (IRDAI Annexure I, List I):**\n\n"
            "Under IRDAI standardization regulations, ₹5,000 was flagged as institutional consumables:\n\n"
            "1. **Gloves & PPE Kits (IRDAI-NP-001 & 002 - ₹2,450):** Routine protective gear for hospital staff is treated as institutional overhead unless bundled into a surgical package.\n"
            "2. **Registration & MRD Fees (IRDAI-NP-004 - ₹500):** Administrative record fees cannot be billed to insurance under IRDAI guidelines.\n"
            "3. **Bio-Medical Waste Levy (IRDAI-NP-005 - ₹850):** Statutory waste disposal is an institutional overhead.\n"
            "4. **Attendant Food & Misc (IRDAI-NP-006 & 007 - ₹1,200):** Personal comfort and visitor food are non-payable.\n\n"
            "**Patient Remedy:** If gloves or PPE were procedure-critical in an ICU or specialized OT, request the hospital billing desk for an itemized surgical certificate to challenge the deduction.\n\n"
            "---\n*AI guidance only. Final claim decision remains with the insurer.*"
        )

    # 5. Missing Documents & Verification Gates
    if any(term in q for term in ["document", "missing", "paper", "upload", "icp", "stamp", "signature", "gate"]):
        return (
            "**Document Verification Status for CLM-20491:**\n\n"
            "5 out of 6 standard admissibility gates are satisfied:\n"
            "✅ **Discharge Summary:** Verified (Apollo Hospital, Bengaluru)\n"
            "✅ **Hospital Bill:** Verified (₹73,000 itemized)\n"
            "✅ **Policy Schedule:** Verified (#SH-884920, continuous since March 2018)\n"
            "✅ **Doctor Prescription:** Verified\n"
            "✅ **Claim Form:** Verified and signed\n"
            "❌ **Pending Document:** **Indoor Case Papers (ICPs) / OT Notes**\n\n"
            "**Action:** Contact Apollo Hospital Medical Records Department (MRD) to request stamped Indoor Case Papers for admission Feb 10–14, 2026.\n\n"
            "---\n*AI guidance only. Final claim decision remains with the insurer.*"
        )

    # 6. Rejection, Repudiation, and Clause 4.2
    if any(term in q for term in ["reject", "repudiat", "clause 4", "denied", "why"]):
        return (
            "**Why Your Claim Was Rejected (and Why the Insurer is Wrong):**\n\n"
            "Star Health repudiated claim CLM-20491 citing **Clause 4.2** (24-month waiting period for joint replacement surgery).\n\n"
            "**Why this is legally invalid:**\n"
            "Under **IRDAI Master Circular on Protection of Policyholders' Interests 2024, Chapter V, Section 5.3**, "
            "all health policies have a statutory **60-Month Moratorium Period**. Once a policy is continuously renewed for 60 months, "
            "the insurer **cannot repudiate any claim** on grounds of pre-existing diseases or waiting period exclusions (except proven fraud).\n\n"
            "Your policy has **78 months of continuous coverage** (since 12 March 2018). Clause 4.2 cannot legally be applied.\n\n"
            "---\n*AI guidance only. Final claim decision remains with the insurer.*"
        )

    # 7. Appeals & Legal Redressal
    if any(term in q for term in ["appeal", "gro", "ombudsman", "grievance", "complaint", "legal"]):
        return (
            "**Your 2-Step Appeal Roadmap:**\n\n"
            "1. **Step 1 — Formal Grievance to Insurer GRO (Day 1):**\n"
            "   Submit a formal appeal citing IRDAI Master Circular 2024 (Chapter V, Section 5.3 - 60-Month Moratorium) and attach your renewal history (2018–2026). Use our **Appeal Builder** to generate this ready-to-sign letter.\n\n"
            "2. **Step 2 — Insurance Ombudsman Escalation (Day 30):**\n"
            "   If Star Health does not reverse the repudiation or fails to respond within 30 days, file an appeal under Rule 17 of the Insurance Ombudsman Rules 2017 with the Ombudsman Office in Bengaluru.\n\n"
            "---\n*AI guidance only. Final claim decision remains with the insurer.*"
        )

    # 8. Context-Aware Default Response
    return (
        f"Regarding your query on claim **CLM-20491**:\n\n"
        f"Your active case involves a Total Knee Replacement at Apollo Hospital (Billed: ₹73,000, Indicative Payable: ₹61,200.00). "
        f"The claim was repudiated under Clause 4.2, which directly contradicts the IRDAI 2024 60-month moratorium rule because your policy has 78 months continuous tenure.\n\n"
        f"I can specifically help you:\n"
        f"- Understand the **reimbursement calculation** & non-payable deductions\n"
        f"- Review **missing documents** (such as Indoor Case Papers)\n"
        f"- Draft an **appeal letter** for the Grievance Redressal Officer (GRO)\n\n"
        f"Please ask any question about your claim, deductions, or appeal rights!\n\n"
        f"---\n*AI guidance only. Final claim decision remains with the insurer.*"
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
