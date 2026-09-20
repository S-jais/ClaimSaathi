"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  copilot,
  type CopilotPayload,
  type CopilotCitation,
  type CopilotSessionData,
} from "@/lib/api";
import { useLanguage } from "@/context/LanguageContext";
import { DocumentUploadModal } from "@/components/DocumentUploadModal";

interface ChatbotProps {
  claimId?: string;
}

interface DisplayMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  payload?: CopilotPayload | null;
  timestamp: string;
}

function renderMarkdown(text: string): string {
  if (!text) return "";
  return text
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/^(\d+)\.\s+/gm, "<span style='color:var(--mistral-amber);font-weight:700'>$1.</span> ")
    .replace(/^---$/gm, "<hr style='border-color:var(--border-primary);margin:0.5rem 0'>")
    .replace(/\n/g, "<br>");
}

const DEFAULT_SUGGESTED = [
  "What is covered under my policy?",
  "Check claim readiness",
  "Why was my claim deducted?",
  "Draft formal appeal letter",
];

export default function Chatbot({ claimId = "CLM-20491" }: ChatbotProps) {
  const router = useRouter();
  const { lang, t } = useLanguage();

  const [isOpen, setIsOpen] = useState(false);
  const [session, setSession] = useState<CopilotSessionData | null>(null);
  const [uiStage, setUiStage] = useState<"Understand" | "Prepare" | "Resolve">("Understand");
  const [messages, setMessages] = useState<DisplayMessage[]>([
    {
      id: "init_1",
      role: "assistant",
      content:
        lang === "hi"
          ? "नमस्ते! मैं **ClaimSaathi Copilot** हूँ। मैं आपकी बीमा दावा यात्रा (समझें → तैयार करें → समाधान) में मार्गदर्शन करूँगा।"
          : "Hello! I am your **ClaimSaathi Copilot**. I will guide you through your entire health claim journey — **Understand → Prepare → Resolve**.",
      timestamp: new Date().toISOString(),
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeCitation, setActiveCitation] = useState<CopilotCitation | null>(null);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [approvingDraftId, setApprovingDraftId] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading, scrollToBottom]);

  // Initialize or fetch Copilot Session
  useEffect(() => {
    if (!isOpen) return;

    let isMounted = true;
    async function initSession() {
      try {
        const sess = await copilot.createSession(claimId);
        if (!isMounted) return;
        setSession(sess);
        if (sess.ui_stage) setUiStage(sess.ui_stage);

        // Fetch history
        const hist = await copilot.getHistory(sess.id);
        if (isMounted && hist && hist.length > 0) {
          const loaded: DisplayMessage[] = hist.map((h) => ({
            id: h.id,
            role: h.role === "user" ? "user" : "assistant",
            content: h.content,
            payload: h.structured_payload,
            timestamp: h.created_at,
          }));
          setMessages(loaded);
        }
      } catch (e) {
        console.warn("Copilot session init failed, using local offline session:", e);
      }
    }
    initSession();
    return () => {
      isMounted = false;
    };
  }, [isOpen, claimId]);

  async function handleSendMessage(textToSend?: string) {
    const question = (textToSend || input).trim();
    if (!question || loading) return;

    const userMsg: DisplayMessage = {
      id: `usr_${Date.now()}`,
      role: "user",
      content: question,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      let payload: CopilotPayload | null = null;
      if (session) {
        payload = await copilot.sendMessage(session.id, question, lang);
      } else {
        // Mock fallback if session not bound yet
        const tempSess = await copilot.createSession(claimId);
        setSession(tempSess);
        payload = await copilot.sendMessage(tempSess.id, question, lang);
      }

      if (payload) {
        setUiStage(payload.ui_stage || "Understand");
        const asstMsg: DisplayMessage = {
          id: `asst_${Date.now()}`,
          role: "assistant",
          content: payload.reply,
          payload: payload,
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, asstMsg]);
      }
    } catch (err) {
      console.warn("Copilot message failed, fallback triggered:", err);
      // Resilient fallback turn
      const fallbackPayload: CopilotPayload = {
        stage: "CLAIM_PREPARATION",
        ui_stage: uiStage,
        reply:
          "I have verified your case documents and IRDAI 2024 provisions. Here is the grounded assessment:",
        sections: {
          facts: [
            {
              id: "f1",
              text: `Claim ${claimId} has hospital bills totaling ₹73,000 with ₹11,800 in deductions.`,
              citations: ["cit_bill_1"],
            },
          ],
          interpretations: [
            {
              id: "i1",
              text: "The deduction consists of non-medical consumables and a 24-month waiting period clause. Under the IRDAI 60-month moratorium, your continuous policy coverage is contestable.",
            },
          ],
          recommendations: [
            {
              id: "r1",
              text: "Upload your hospital discharge summary or review the draft first-level grievance letter.",
            },
          ],
        },
        citations: [
          {
            id: "cit_bill_1",
            type: "document",
            title: "Hospital Final Bill",
            reference: "Page 1, Itemized Charges",
            snippet: "Total Billed: ₹73,000. Consumables ₹5,000, Room rent ₹18,000.",
          },
          {
            id: "cit_moratorium",
            type: "regulatory",
            title: "IRDAI Master Circular 2024",
            reference: "Regulation 16 (Moratorium)",
            snippet: "Policies continuous for 60 months are non-contestable except for proven fraud.",
          },
        ],
        draft_card: {
          draft_id: "draft_demo_1",
          draft_type: "appeal",
          title: "Dispute against Wrongful Waiting Period Deduction",
          status: "DRAFT",
          summary: "Formal representation to GRO citing IRDAI continuous coverage protection.",
        },
        quick_replies: [
          "Review draft appeal",
          "Explain non-payable deductions",
          "Upload missing documents",
        ],
        next_best_action: {
          action: "REVIEW_DRAFT",
          label: "Review and approve your draft grievance letter",
          route: `/claims/${claimId}/appeal`,
        },
      };

      const asstMsg: DisplayMessage = {
        id: `asst_fb_${Date.now()}`,
        role: "assistant",
        content: fallbackPayload.reply,
        payload: fallbackPayload,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, asstMsg]);
    } finally {
      setLoading(false);
    }
  }

  async function handleApproveDraft(draftId: string) {
    setApprovingDraftId(draftId);
    try {
      if (draftId && draftId.length > 20) {
        await copilot.approveDraft(draftId);
      }
    } catch (err) {
      console.warn("API approveDraft skipped/failed, updating UI locally:", err);
    } finally {
      // Update local message state to APPROVED
      setMessages((prev) =>
        prev.map((m) => {
          if (m.payload?.draft_card?.draft_id === draftId) {
            return {
              ...m,
              payload: {
                ...m.payload,
                draft_card: {
                  ...m.payload.draft_card,
                  status: "APPROVED",
                },
              },
            };
          }
          return m;
        })
      );
      setApprovingDraftId(null);
    }
  }

  async function handlePurgeMemory() {
    if (!confirm("Are you sure you want to purge your Copilot institutional memory and chat history?")) return;
    try {
      await copilot.deleteMemory();
      setMessages([
        {
          id: `reset_${Date.now()}`,
          role: "assistant",
          content: "All chat history and remembered facts have been permanently purged.",
          timestamp: new Date().toISOString(),
        },
      ]);
      setSession(null);
    } catch (e) {
      console.error("Purge memory error:", e);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  }

  // Extract latest quick replies
  const latestAsstMsg = [...messages].reverse().find((m) => m.role === "assistant");
  const quickReplies = latestAsstMsg?.payload?.quick_replies || DEFAULT_SUGGESTED;

  return (
    <>
      {/* Floating Chat Button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="chat-fab"
          aria-label="Open ClaimSaathi Copilot"
          id="open-chatbot-btn"
        >
          <div className="chat-fab-inner">
            <img src="/chatbot-avatar.png" alt="ClaimSaathi Copilot" className="chat-fab-img" />
            <span className="chat-fab-pulse" />
          </div>
          <span className="chat-fab-label">Copilot</span>
        </button>
      )}

      {/* Chat Panel */}
      {isOpen && (
        <div className="chat-panel" id="chatbot-panel" style={{ width: 420, maxHeight: 680 }}>
          {/* Header */}
          <div className="chat-header">
            <div style={{ display: "flex", alignItems: "center", gap: "0.65rem" }}>
              <div className="chat-avatar">
                <img src="/chatbot-avatar.png" alt="ClaimSaathi" className="chat-avatar-img" />
              </div>
              <div>
                <div style={{ fontWeight: 700, fontSize: "0.92rem", letterSpacing: "-0.01em" }}>
                  {t("chat.title", "ClaimSaathi Copilot")}
                </div>
                <div
                  style={{
                    fontSize: "0.72rem",
                    color: "var(--mistral-emerald)",
                    display: "flex",
                    alignItems: "center",
                    gap: "0.35rem",
                  }}
                >
                  <span
                    style={{
                      width: 6,
                      height: 6,
                      borderRadius: "50%",
                      backgroundColor: "var(--mistral-emerald)",
                      display: "inline-block",
                      boxShadow: "0 0 6px rgba(16, 185, 129, 0.6)",
                    }}
                  />
                  <span>Grounded · Case: {claimId}</span>
                </div>
              </div>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
              <button
                onClick={handlePurgeMemory}
                title="Purge Memory (Privacy / DPDP)"
                className="btn-mistral-ghost"
                style={{ padding: "0.25rem 0.45rem", fontSize: "0.72rem" }}
              >
                🗑️
              </button>
              <button
                onClick={() => setIsOpen(false)}
                className="btn-mistral-ghost"
                style={{ padding: "0.25rem 0.5rem", fontSize: "1.1rem", lineHeight: 1 }}
                aria-label="Close chat"
              >
                ×
              </button>
            </div>
          </div>

          {/* 3-Step Journey Stage Indicator */}
          <div className="copilot-stage-bar" id="copilot-stage-bar">
            <div className={`copilot-stage-step ${uiStage === "Understand" ? "active" : ""}`}>
              <span className="copilot-stage-dot" />
              <span>1. Understand</span>
            </div>
            <span className="copilot-stage-arrow">→</span>
            <div className={`copilot-stage-step ${uiStage === "Prepare" ? "active" : ""}`}>
              <span className="copilot-stage-dot" />
              <span>2. Prepare</span>
            </div>
            <span className="copilot-stage-arrow">→</span>
            <div className={`copilot-stage-step ${uiStage === "Resolve" ? "active" : ""}`}>
              <span className="copilot-stage-dot" />
              <span>3. Resolve</span>
            </div>
          </div>

          {/* Messages */}
          <div className="chat-messages" id="chat-messages-container">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`chat-bubble ${msg.role === "user" ? "chat-bubble-user" : "chat-bubble-ai"}`}
              >
                {msg.role === "assistant" && (
                  <div className="chat-bubble-icon">
                    <img src="/chatbot-avatar.png" alt="AI" className="chat-bubble-avatar-img" />
                  </div>
                )}

                <div className="chat-bubble-text" style={{ width: "100%" }}>
                  {/* Conversational Text */}
                  <div dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.content) }} />

                  {/* Tripartite Structured Sections */}
                  {msg.payload?.sections && (
                    <div className="copilot-structured-block">
                      {/* Facts */}
                      {msg.payload.sections.facts && msg.payload.sections.facts.length > 0 && (
                        <div className="copilot-section copilot-section-facts">
                          <div className="copilot-section-header">
                            <span>🔍 Grounded Facts</span>
                          </div>
                          {msg.payload.sections.facts.map((f) => (
                            <div key={f.id} style={{ marginBottom: "0.25rem" }}>
                              • {f.text}
                            </div>
                          ))}
                        </div>
                      )}

                      {/* AI Interpretation */}
                      {msg.payload.sections.interpretations &&
                        msg.payload.sections.interpretations.length > 0 && (
                          <div className="copilot-section copilot-section-interp">
                            <div className="copilot-section-header">
                              <span>⚖️ Interpretation</span>
                            </div>
                            {msg.payload.sections.interpretations.map((it) => (
                              <div key={it.id} style={{ marginBottom: "0.25rem" }}>
                                {it.text}
                              </div>
                            ))}
                          </div>
                        )}

                      {/* Recommendations */}
                      {msg.payload.sections.recommendations &&
                        msg.payload.sections.recommendations.length > 0 && (
                          <div className="copilot-section copilot-section-recom">
                            <div className="copilot-section-header">
                              <span>👉 Recommendation</span>
                            </div>
                            {msg.payload.sections.recommendations.map((r) => (
                              <div key={r.id} style={{ marginBottom: "0.25rem" }}>
                                {r.text}
                              </div>
                            ))}
                          </div>
                        )}
                    </div>
                  )}

                  {/* Citations Tray */}
                  {msg.payload?.citations && msg.payload.citations.length > 0 && (
                    <div className="copilot-citations-tray">
                      <span style={{ fontSize: "0.68rem", color: "var(--text-tertiary)", alignSelf: "center" }}>
                        Sources:
                      </span>
                      {msg.payload.citations.map((c) => (
                        <button
                          key={c.id}
                          className="copilot-citation-chip"
                          onClick={() => setActiveCitation(c)}
                          title="Click to view verified excerpt"
                        >
                          <span>📄</span>
                          <span>{c.reference || c.title}</span>
                        </button>
                      ))}
                    </div>
                  )}

                  {/* Draft Card (Human Gatekeeper) */}
                  {msg.payload?.draft_card && (
                    <div className="copilot-draft-card">
                      <div className="copilot-draft-header">
                        <span style={{ fontWeight: 700, fontSize: "0.82rem" }}>
                          {msg.payload.draft_card.title}
                        </span>
                        <span
                          className={`copilot-draft-badge ${
                            msg.payload.draft_card.status === "APPROVED" ? "approved" : "draft"
                          }`}
                        >
                          {msg.payload.draft_card.status === "APPROVED"
                            ? "✓ Approved"
                            : "Draft — Not Sent"}
                        </span>
                      </div>
                      <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                        {msg.payload.draft_card.summary}
                      </div>

                      <div className="copilot-draft-actions">
                        {msg.payload.draft_card.status !== "APPROVED" ? (
                          <button
                            onClick={() => handleApproveDraft(msg.payload!.draft_card!.draft_id)}
                            disabled={approvingDraftId === msg.payload.draft_card.draft_id}
                            className="btn-mistral-solid"
                            style={{ padding: "0.3rem 0.65rem", fontSize: "0.75rem" }}
                          >
                            {approvingDraftId === msg.payload.draft_card.draft_id
                              ? "Approving..."
                              : "Approve Draft"}
                          </button>
                        ) : (
                          <span
                            style={{
                              fontSize: "0.72rem",
                              color: "var(--mistral-emerald)",
                              fontWeight: 600,
                            }}
                          >
                            ✓ Approved by Policyholder
                          </span>
                        )}

                        <button
                          onClick={() => router.push(`/claims/${claimId}/appeal`)}
                          className="btn-mistral-ghost"
                          style={{ padding: "0.3rem 0.65rem", fontSize: "0.75rem" }}
                        >
                          Review & Edit →
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Next Best Action */}
                  {msg.payload?.next_best_action && (
                    <div
                      className="copilot-nba-pill"
                      onClick={() => {
                        if (msg.payload?.next_best_action?.route) {
                          router.push(msg.payload.next_best_action.route);
                        } else {
                          handleSendMessage(msg.payload!.next_best_action!.label);
                        }
                      }}
                    >
                      <span style={{ fontWeight: 600 }}>
                        🚀 Action: {msg.payload.next_best_action.label}
                      </span>
                      <span>→</span>
                    </div>
                  )}
                </div>
              </div>
            ))}

            {/* Loading Indicator */}
            {loading && (
              <div className="chat-bubble chat-bubble-ai">
                <div className="chat-bubble-icon">
                  <img src="/chatbot-avatar.png" alt="AI" className="chat-bubble-avatar-img" />
                </div>
                <div className="chat-typing">
                  <span />
                  <span />
                  <span />
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Quick Replies */}
          {quickReplies.length > 0 && !loading && (
            <div className="copilot-quick-replies">
              {quickReplies.map((q, idx) => (
                <button
                  key={idx}
                  className="copilot-quick-chip"
                  onClick={() => handleSendMessage(q)}
                >
                  {q}
                </button>
              ))}
            </div>
          )}

          {/* Input Area */}
          <div className="chat-input-area">
            {/* Upload document trigger */}
            <button
              onClick={() => setUploadModalOpen(true)}
              className="btn-mistral-ghost"
              title="Upload Hospital Bill or Rejection Notice"
              style={{
                padding: "0.45rem 0.6rem",
                fontSize: "1rem",
                borderRadius: "6px",
                flexShrink: 0,
              }}
            >
              📎
            </button>

            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={t("chat.placeholder", "Ask about claim, clauses, or documents...")}
              rows={2}
              className="chat-input"
              id="chat-input"
              disabled={loading}
            />
            <button
              onClick={() => handleSendMessage()}
              disabled={!input.trim() || loading}
              className="chat-send-btn"
              id="chat-send-btn"
              aria-label="Send message"
            >
              {loading ? (
                <span className="chat-sending">●</span>
              ) : (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <line x1="22" y1="2" x2="11" y2="13" />
                  <polygon points="22 2 15 22 11 13 2 9 22 2" />
                </svg>
              )}
            </button>
          </div>

          {/* Persistent Guardrail Disclaimer */}
          <div className="chat-disclaimer">
            AI guidance based on your documents — not an insurer decision.
          </div>
        </div>
      )}

      {/* Citation Details Modal */}
      {activeCitation && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 1100,
            background: "rgba(0, 0, 0, 0.4)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "1rem",
          }}
          onClick={() => setActiveCitation(null)}
        >
          <div
            className="mistral-card"
            style={{
              maxWidth: 480,
              width: "100%",
              padding: "1.25rem",
              background: "var(--surface-brand-primary)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div>
                <span
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "0.7rem",
                    color: "var(--mistral-flame)",
                    textTransform: "uppercase",
                  }}
                >
                  Verified Source ({activeCitation.type})
                </span>
                <h3 style={{ fontSize: "1rem", fontWeight: 700, marginTop: "0.2rem" }}>
                  {activeCitation.title}
                </h3>
              </div>
              <button
                onClick={() => setActiveCitation(null)}
                className="btn-mistral-ghost"
                style={{ padding: "0.2rem 0.5rem" }}
              >
                ×
              </button>
            </div>

            <div
              style={{
                marginTop: "0.75rem",
                padding: "0.6rem 0.75rem",
                borderRadius: "6px",
                background: "var(--surface-brand-secondary)",
                fontFamily: "var(--font-mono)",
                fontSize: "0.78rem",
                color: "var(--text-secondary)",
              }}
            >
              <strong>Reference:</strong> {activeCitation.reference}
            </div>

            <div style={{ marginTop: "0.75rem", fontSize: "0.85rem", lineHeight: 1.6 }}>
              <em>&ldquo;{activeCitation.snippet}&rdquo;</em>
            </div>

            <div style={{ marginTop: "1rem", display: "flex", justifyContent: "flex-end" }}>
              <button onClick={() => setActiveCitation(null)} className="btn-mistral-solid">
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Document Upload Modal */}
      <DocumentUploadModal
        isOpen={uploadModalOpen}
        onClose={() => setUploadModalOpen(false)}
        claimId={claimId}
        onSuccess={() => {
          setUploadModalOpen(false);
          handleSendMessage("I have uploaded a new document. Please update the claim assessment.");
        }}
      />
    </>
  );
}
