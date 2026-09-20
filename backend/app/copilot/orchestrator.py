"""
app/copilot/orchestrator.py
Core orchestration loop for the Journey Chatbot ("ClaimSaathi Copilot").
Executes the per-turn pipeline:
1. Load state & case context
2. Cognee recall (user-scoped)
3. Intent routing & state machine transition
4. Tool calling loop (max 5 calls/turn)
5. Structured synthesis (Gemini 2-tier)
6. Guardrail validation
7. Persistence & Cognee remember
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
import datetime
from pathlib import Path
import re
from typing import Any
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.ai.guardrails import enforce_copilot_guardrails
from app.auth.models import User
from app.claims.models import Claim, ClaimEvent
from app.copilot.models import CopilotSession, CopilotMessage, CopilotDraft
from app.copilot.schemas import (
    CitationItem,
    CopilotResponsePayload,
    DraftCard,
    FactItem,
    InterpretationItem,
    NextBestAction,
    RecommendationItem,
    StructuredSections,
)
from app.copilot.state_machine import (
    JourneyStage,
    can_transition,
    get_ui_stage,
)
from app.copilot.tools import (
    tool_build_appeal_draft,
    tool_compute_deadlines,
    tool_decode_rejection,
    tool_get_case_state,
    tool_next_best_action,
    tool_run_readiness,
    tool_search_policy_clauses,
)
from app.llm.gemini_client import get_gemini_client
from app.llm.gemini_client import get_gemini_client
from app.memory.cognee_client import get_cognee_client

logger = structlog.get_logger(__name__)

PROMPT_DIR = Path(__file__).parent / "prompts"
SYSTEM_PROMPT_PATH = PROMPT_DIR / "copilot_system.md"
VOICE_MODE_PATH = PROMPT_DIR / "voice_mode.md"
GLOSSARY_HI_PATH = PROMPT_DIR / "glossary_hi.md"

_SYSTEM_PROMPT_TEMPLATE = ""
if SYSTEM_PROMPT_PATH.exists():
    try:
        with open(SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as f:
            _SYSTEM_PROMPT_TEMPLATE = f.read()
    except Exception as e:
        logger.warning("failed_reading_copilot_system_prompt", error=str(e))

_VOICE_MODE_TEMPLATE = ""
if VOICE_MODE_PATH.exists():
    try:
        with open(VOICE_MODE_PATH, "r", encoding="utf-8") as f:
            _VOICE_MODE_TEMPLATE = f.read()
    except Exception as e:
        logger.warning("failed_reading_voice_mode_prompt", error=str(e))

_GLOSSARY_HI_TEMPLATE = ""
if GLOSSARY_HI_PATH.exists():
    try:
        with open(GLOSSARY_HI_PATH, "r", encoding="utf-8") as f:
            _GLOSSARY_HI_TEMPLATE = f.read()
    except Exception as e:
        logger.warning("failed_reading_glossary_hi_prompt", error=str(e))


def detect_message_language(text: str, default_lang: str = "en") -> str:
    """
    Detect whether user message is in English, Hindi (Devanagari), or Hinglish (Roman Hindi).
    """
    # 1. Devanagari Unicode check [\u0900-\u097F]
    if re.search(r"[\u0900-\u097F]", text):
        return "hi"

    # 2. Common Hinglish grammatical / question vocabulary
    hinglish_markers = [
        r"\bkya\b", r"\bkyaa\b", r"\bmera\b", r"\bmeri\b", r"\bmere\b",
        r"\bkaise\b", r"\bkab\b", r"\bkub\b", r"\bkahan\b", r"\bkaha\b",
        r"\bhoga\b", r"\bhogi\b", r"\bhoge\b", r"\bhain\b", r"\bhai\b",
        r"\bnahi\b", r"\bnahin\b", r"\bbhai\b", r"\bbatao\b", r"\bbataye\b",
        r"\bkaro\b", r"\bkaru\b", r"\bkare\b", r"\bpaisa\b", r"\bpaise\b",
        r"\bchahiye\b", r"\bmilega\b", r"\bmilenge\b", r"\bshuru\b",
        r"\baap\b", r"\baapka\b", r"\baapki\b", r"\bmujhe\b", r"\bkitna\b",
        r"\bkitne\b", r"\bkhatam\b", r"\bkarun\b", r"\bkarein\b", r"\bhogya\b"
    ]
    pattern = re.compile("|".join(hinglish_markers), re.IGNORECASE)
    if pattern.search(text):
        return "hinglish"

    if default_lang in {"hi", "hinglish"}:
        return default_lang

    return "en"


def generate_spoken_text(reply: str, language: str = "en") -> str:
    """Produce concise, natural speech version without markdown or code formatting."""
    clean = re.sub(r"\*\*|\*|#|`", "", reply)
    clean = re.sub(r"\[(FACT|INTERPRETATION|RECOMMENDATION).*?\]", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\n+", " ", clean).strip()
    clean = clean.replace("₹", "rupees ")
    sentences = [s.strip() for s in re.split(r"[.!?।]", clean) if s.strip()]
    spoken = ". ".join(sentences[:3])
    if spoken and not spoken.endswith((".", "।")):
        spoken += "."
    return spoken


class CopilotOrchestrator:
    """Multi-turn stateful coordinator for ClaimSaathi Copilot."""

    def __init__(self) -> None:
        self.gemini = get_gemini_client()
        self.cognee = get_cognee_client()

    def _render_system_prompt(
        self,
        stage: str,
        case_state: dict[str, Any],
        deadlines: list[dict[str, Any]],
        cognee_facts: list[str],
        clauses: list[dict[str, Any]],
        ui_language: str = "en",
        detected_language: str = "en",
        mode: str = "text",
        user_first_name: str = "Customer",
    ) -> str:
        prompt = _SYSTEM_PROMPT_TEMPLATE or "You are ClaimSaathi Copilot."

        today_str = datetime.date.today().strftime("%d %b %Y")

        summary_text = (
            f"Claim Reference: {case_state.get('claim_reference')}\n"
            f"Patient: {case_state.get('patient_name')} | Hospital: {case_state.get('hospital_name')}\n"
            f"Claim Amount: ₹{case_state.get('claim_amount_inr', 0):,.2f}\n"
            f"Status: {case_state.get('status')} | Readiness Score: {case_state.get('readiness_score') or 'Not computed'}"
        )

        doc_lines = [
            f"- {d.get('type')}: {d.get('file_name')} ({d.get('status')})"
            for d in case_state.get("documents", [])
        ]
        doc_text = "\n".join(doc_lines) if doc_lines else "No documents uploaded yet."

        readiness_text = (
            f"Readiness Score: {case_state.get('readiness_score') or 'Pending check'}. "
            f"Verified {len(case_state.get('documents', []))} documents."
        )

        estimate_text = (
            f"Billed: ₹{case_state.get('claim_amount_inr', 0):,.2f}. "
            f"Indicative payable estimate subject to insurer assessment."
        )

        deadline_lines = [
            f"- {dl.get('name')}: {dl.get('due_date')} ({dl.get('days_remaining')} days left) [{dl.get('statutory_source')}]"
            for dl in deadlines
        ]
        deadline_text = "\n".join(deadline_lines) if deadline_lines else "Standard 30-day statutory settlement window."

        cognee_text = "\n".join(f"- {f}" for f in cognee_facts) if cognee_facts else "No prior history recorded."

        clause_lines = [
            f"[{c.get('clause_ref')}] {c.get('section_title')}: {c.get('text')}"
            for c in clauses
        ]
        clause_text = "\n".join(clause_lines) if clause_lines else "Standard IRDAI 2024 terms apply."

        # Replace all placeholders
        prompt = prompt.replace("{{today}}", today_str)
        prompt = prompt.replace("{{ui_language}}", ui_language)
        prompt = prompt.replace("{{mode}}", mode)
        prompt = prompt.replace("{{user_first_name}}", user_first_name)
        prompt = prompt.replace("{{stage}}", stage)
        prompt = prompt.replace("{{case_summary}}", summary_text)
        prompt = prompt.replace("{{document_list_with_status}}", doc_text)
        prompt = prompt.replace("{{readiness_summary}}", readiness_text)
        prompt = prompt.replace("{{estimate_summary}}", estimate_text)
        prompt = prompt.replace("{{deadlines}}", deadline_text)
        prompt = prompt.replace("{{memory_context}}", cognee_text)
        prompt = prompt.replace("{{retrieved_evidence}}", clause_text)
        prompt = prompt.replace("{{retrieved_clauses_and_docs}}", clause_text)

        # Conditionally append Hindi Glossary for Hindi/Hinglish turns
        if (detected_language in {"hi", "hinglish"} or ui_language == "hi") and _GLOSSARY_HI_TEMPLATE:
            prompt += f"\n\n---\n\n{_GLOSSARY_HI_TEMPLATE}"

        # Conditionally append Voice Mode addendum
        if mode == "voice" and _VOICE_MODE_TEMPLATE:
            prompt += f"\n\n---\n\n{_VOICE_MODE_TEMPLATE}"

        return prompt

    def _determine_stage_transition(
        self,
        current_stage: str,
        message: str,
        case_state: dict[str, Any],
    ) -> str:
        """Evaluate if user intent triggers a legal state transition."""
        m_lower = message.lower()
        evidence = {
            "has_rejection_reasons": bool(case_state.get("rejection_reasons")),
            "has_rejection_document": any(
                d.get("type") in {"rejection_letter", "denial_letter", "query_letter"}
                for d in case_state.get("documents", [])
            ),
            "claim_status": case_state.get("status"),
            "has_draft": bool(case_state.get("drafts")),
            "has_dispute_basis": True,
        }

        # Check intent keywords
        target_stage: JourneyStage | None = None
        if any(w in m_lower for w in ["reject", "denial", "deduct", "repudiat"]):
            target_stage = JourneyStage.REJECTED_DECODING
        elif any(w in m_lower for w in ["appeal", "grievance", "draft letter", "dispute"]):
            target_stage = JourneyStage.APPEAL_DRAFTING
        elif any(w in m_lower for w in ["readiness", "score", "audit", "verify"]):
            target_stage = JourneyStage.CLAIM_PREPARATION
        elif any(w in m_lower for w in ["policy", "coverage", "room rent", "waiting period"]):
            target_stage = JourneyStage.POLICY_UNDERSTANDING
        elif any(w in m_lower for w in ["ombudsman", "bima bharosa", "escalat"]):
            target_stage = JourneyStage.ESCALATION

        if target_stage:
            ok, _ = can_transition(current_stage, target_stage, evidence)
            if ok:
                return target_stage.value

        return current_stage

    async def execute_turn(
        self,
        db: AsyncSession,
        session: CopilotSession,
        claim: Claim,
        user: User,
        user_message: str,
        language: str = "en",
        mode: str = "text",
    ) -> CopilotResponsePayload:
        """Executes full orchestrated turn synchronously and returns structured payload."""
        # 1. Load case state & tools
        case_state = await tool_get_case_state(db, claim)
        deadlines = tool_compute_deadlines(claim)

        # 2. Cognee recall
        cognee_facts = await self.cognee.recall(str(user.id), user_message, limit=3)

        # 3. State transition
        new_stage = self._determine_stage_transition(session.stage, user_message, case_state)
        if new_stage != session.stage:
            logger.info("copilot_stage_transition", from_stage=session.stage, to_stage=new_stage)
            session.stage = new_stage
            event = ClaimEvent(
                claim_id=claim.id,
                event_type="copilot_stage_transition",
                actor_type="system",
                actor_id=str(user.id),
                metadata_json={"from_stage": session.stage, "to_stage": new_stage},
            )
            db.add(event)
            await db.flush()

        ui_stage = get_ui_stage(session.stage)

        # 4. Tool Loop (max 5 calls)
        tool_trace: list[dict[str, Any]] = []
        citations: list[CitationItem] = []
        clauses = await tool_search_policy_clauses(db, claim.policy_id, user_message)
        tool_trace.append({"tool": "search_policy_clauses", "count": len(clauses)})
        for c in clauses:
            citations.append(
                CitationItem(
                    id=c["id"],
                    type="policy_clause",
                    title=c["section_title"],
                    reference=f"Clause {c['clause_ref']}",
                    snippet=c["text"][:180] + "...",
                )
            )

        draft_card: DraftCard | None = None
        m_lower = user_message.lower()

        # Tool: Readiness
        if "readiness" in m_lower or "score" in m_lower or session.stage == JourneyStage.CLAIM_PREPARATION.value:
            try:
                readiness_res = await tool_run_readiness(db, claim)
                tool_trace.append({"tool": "run_claim_readiness", "score": readiness_res.get("readiness_score")})
                citations.append(
                    CitationItem(
                        id="cit_readiness_engine",
                        type="case_data",
                        title="Claim Readiness Audit",
                        reference="Rules Engine Verification",
                        snippet=f"Verified Score: {readiness_res.get('readiness_score')}/100 with {len(readiness_res.get('missing_documents', []))} missing documents.",
                    )
                )
            except Exception as e:
                logger.warning("readiness_tool_failed", error=str(e))

        # Tool: Rejection Decoder
        if session.stage in {JourneyStage.REJECTED_DECODING.value, JourneyStage.APPEAL_DRAFTING.value}:
            try:
                rejection_data = await tool_decode_rejection(db, claim)
                tool_trace.append({"tool": "decode_rejection", "code": rejection_data.get("code")})
                citations.append(
                    CitationItem(
                        id="cit_insurer_rejection",
                        type="document",
                        title="Insurer Repudiation Notice",
                        reference=f"Code: {rejection_data.get('code')}",
                        snippet=str(rejection_data.get("fact"))[:180],
                    )
                )
            except Exception as e:
                logger.warning("rejection_decoder_tool_failed", error=str(e))

        # Tool: Appeal Builder
        if "draft" in m_lower or "appeal" in m_lower or "grievance" in m_lower or session.stage == JourneyStage.APPEAL_DRAFTING.value:
            try:
                appeal_data = await tool_build_appeal_draft(db, claim, user, session.id)
                tool_trace.append({"tool": "build_appeal_draft", "draft_id": appeal_data.get("draft_id")})
                draft_card = DraftCard(
                    draft_id=appeal_data["draft_id"],
                    draft_type="appeal",
                    title=appeal_data["title"],
                    status=appeal_data["status"],
                    summary=appeal_data["summary"],
                    content=appeal_data["content"],
                )
            except Exception as e:
                logger.warning("appeal_builder_tool_failed", error=str(e))

        # Next Best Action
        nba = tool_next_best_action(session.stage, case_state)
        next_best_action = NextBestAction(
            action=nba["action"],
            label=nba["label"],
            route=nba.get("route"),
        )

        # Detect message language and user name
        detected_lang = detect_message_language(user_message, default_lang=language)
        user_first = user.full_name.split()[0] if user.full_name else "Customer"

        # 5. Synthesis Prompt
        system_prompt = self._render_system_prompt(
            stage=session.stage,
            case_state=case_state,
            deadlines=deadlines,
            cognee_facts=cognee_facts,
            clauses=clauses,
            ui_language=language,
            detected_language=detected_lang,
            mode=mode,
            user_first_name=user_first,
        )

        # Quick replies tailored to stage
        quick_replies = self._generate_quick_replies(session.stage, case_state)

        # 6. Generate Response via LLM
        prompt = (
            f"User Query: {user_message}\n"
            f"Detected Language / Script: {detected_lang}\n"
            f"Provide your answer adhering strictly to FACT, INTERPRETATION, RECOMMENDATION."
        )

        citation_ids = [c.id for c in citations]
        raw_text = await self.gemini.generate(
            prompt=prompt,
            model_tier="flash" if len(user_message) < 150 else "pro",
            system_instruction=system_prompt,
            temperature=0.2,
        )

        # Parse sections from generated text
        sections = self._parse_structured_sections(raw_text, citation_ids)
        spoken_text = generate_spoken_text(raw_text, detected_lang)

        payload_dict: dict[str, Any] = {
            "stage": session.stage,
            "ui_stage": ui_stage,
            "reply": raw_text,
            "language": detected_lang,
            "spoken_text": spoken_text,
            "sections": sections.model_dump(),
            "citations": [c.model_dump() for c in citations],
            "draft_card": draft_card.model_dump() if draft_card else None,
            "quick_replies": quick_replies,
            "next_best_action": next_best_action.model_dump(),
            "warnings": [],
        }

        # 7. Guardrail validation
        guarded_dict = enforce_copilot_guardrails(payload_dict)
        final_payload = CopilotResponsePayload.model_validate(guarded_dict)

        # 8. Persistence
        # Save user message
        db_user_msg = CopilotMessage(
            session_id=session.id,
            role="user",
            content=user_message,
        )
        db.add(db_user_msg)

        # Save assistant message
        db_asst_msg = CopilotMessage(
            session_id=session.id,
            role="assistant",
            content=final_payload.reply,
            structured_payload=final_payload.model_dump(),
            tool_trace=tool_trace,
            citations=[c.model_dump() for c in final_payload.citations],
        )
        db.add(db_asst_msg)
        await db.commit()

        # Asynchronously remember extracted facts in Cognee
        if final_payload.sections.facts:
            for f in final_payload.sections.facts[:2]:
                asyncio.create_task(self.cognee.remember(str(user.id), f.text, str(claim.id)))

        return final_payload

    async def stream_turn(
        self,
        db: AsyncSession,
        session: CopilotSession,
        claim: Claim,
        user: User,
        user_message: str,
        language: str = "en",
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream orchestration events (tool calls, text chunks, final payload)."""
        # Execute turn logic
        yield {"event": "status", "data": {"status": "analyzing_case", "stage": session.stage}}

        payload = await self.execute_turn(db, session, claim, user, user_message, language)

        # Stream the reply text in words
        words = payload.reply.split(" ")
        for i, word in enumerate(words):
            chunk = word + (" " if i < len(words) - 1 else "")
            yield {"event": "chunk", "data": {"text": chunk}}
            await asyncio.sleep(0.01)

        # Final structured payload event
        yield {"event": "done", "data": payload.model_dump()}

    def _generate_quick_replies(self, stage: str, case_state: dict[str, Any]) -> list[str]:
        """Context-sensitive quick suggestions."""
        if stage in {JourneyStage.ONBOARDING.value, JourneyStage.POLICY_UNDERSTANDING.value}:
            return [
                "What is covered under my policy?",
                "Explain room rent capping",
                "Check claim readiness",
            ]
        elif stage == JourneyStage.CLAIM_PREPARATION.value:
            return [
                "What documents are missing?",
                "Explain bill discrepancies",
                "Check deduction breakdown",
            ]
        elif stage == JourneyStage.REJECTED_DECODING.value:
            return [
                "Why was this claim deducted?",
                "What IRDAI rules protect me?",
                "Draft formal appeal letter",
            ]
        elif stage == JourneyStage.APPEAL_DRAFTING.value:
            return [
                "Review draft grievance",
                "Add portability continuous coverage clause",
                "Approve and send draft",
            ]
        elif stage == JourneyStage.ESCALATION.value:
            return [
                "How to approach Insurance Ombudsman?",
                "Bima Bharosa complaint steps",
                "Track dispute timeline",
            ]
        return ["What is the next best action?", "Check claim status", "Review documents"]

    def _parse_structured_sections(self, text: str, default_citations: list[str]) -> StructuredSections:
        """Extract FACT, INTERPRETATION, and RECOMMENDATION sections from response text."""
        facts: list[FactItem] = []
        interpretations: list[InterpretationItem] = []
        recommendations: list[RecommendationItem] = []

        # Simple regex split for tripartite sections
        fact_match = re.search(r"\*{0,2}FACT\*{0,2}:?\s*(.*?)(?=\*{0,2}INTERPRETATION\*{0,2}|\*{0,2}RECOMMENDATION\*{0,2}|$)", text, re.DOTALL | re.IGNORECASE)
        interp_match = re.search(r"\*{0,2}INTERPRETATION\*{0,2}:?\s*(.*?)(?=\*{0,2}RECOMMENDATION\*{0,2}|$)", text, re.DOTALL | re.IGNORECASE)
        recom_match = re.search(r"\*{0,2}RECOMMENDATION\*{0,2}:?\s*(.*?)$", text, re.DOTALL | re.IGNORECASE)

        if fact_match and fact_match.group(1).strip():
            facts.append(
                FactItem(
                    id="f1",
                    text=fact_match.group(1).strip(),
                    citations=default_citations[:2],
                )
            )
        if interp_match and interp_match.group(1).strip():
            interpretations.append(
                InterpretationItem(
                    id="i1",
                    text=interp_match.group(1).strip(),
                )
            )
        if recom_match and recom_match.group(1).strip():
            recommendations.append(
                RecommendationItem(
                    id="r1",
                    text=recom_match.group(1).strip(),
                )
            )

        if not facts and not interpretations and not recommendations:
            # Fallback if markdown headers were not formatted strictly
            interpretations.append(InterpretationItem(id="i1", text=text.strip()))

        return StructuredSections(
            facts=facts,
            interpretations=interpretations,
            recommendations=recommendations,
        )


_orchestrator_instance: CopilotOrchestrator | None = None


def get_copilot_orchestrator() -> CopilotOrchestrator:
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = CopilotOrchestrator()
    return _orchestrator_instance
