"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { chat, type ChatMessage } from "@/lib/api";
import { useLanguage } from "@/context/LanguageContext";

interface ChatbotProps {
  claimId?: string;
}

// Simple markdown renderer for bold/italic/lists
function renderMarkdown(text: string): string {
  return text
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/^(\d+)\.\s+/gm, "<span style='color:var(--mistral-amber);font-weight:700'>$1.</span> ")
    .replace(/^---$/gm, "<hr style='border-color:var(--border-primary);margin:0.5rem 0'>")
    .replace(/\n/g, "<br>");
}

const SUGGESTED = [
  { en: "Explain my reimbursement calculation", hi: "मेरे रिइम्बर्समेंट की गणना समझाइए" },
  { en: "What non-medical items were deducted?", hi: "कौन से गैर-चिकित्सीय खर्चे काटे गए?" },
  { en: "Which documents are still missing?", hi: "कौन से दस्तावेज़ गायब हैं?" },
  { en: "Why was my claim rejected?", hi: "मेरा क्लेम क्यों खारिज हुआ?" },
  { en: "Explain the 60-month moratorium", hi: "60 महीने का मोरेटोरियम समझाइए" },
  { en: "How do I file an appeal?", hi: "अपील कैसे दर्ज करें?" },
];

export default function Chatbot({ claimId = "CLM-20491" }: ChatbotProps) {
  const { lang, t } = useLanguage();
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content: lang === "hi"
        ? "नमस्ते! मैं ClaimSaathi सहायक हूं। CLM-20491 के बारे में कोई भी प्रश्न पूछें — अस्वीकृति, दस्तावेज़, या अपील।"
        : "Hello! I'm your ClaimSaathi Companion, scoped to claim CLM-20491. Ask me about your rejection, missing documents, IRDAI rights, or how to appeal.",
      timestamp: new Date().toISOString(),
    }
  ]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => { scrollToBottom(); }, [messages, streamingText, scrollToBottom]);

  async function sendMessage(question: string) {
    if (!question.trim() || streaming) return;

    const userMsg: ChatMessage = {
      role: "user",
      content: question.trim(),
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setStreaming(true);
    setStreamingText("");

    let accumulated = "";

    await chat.stream(
      question.trim(),
      claimId,
      messages,
      (chunk) => {
        accumulated += chunk;
        setStreamingText(accumulated);
      },
      () => {
        // Done streaming — commit to messages
        const assistantMsg: ChatMessage = {
          role: "assistant",
          content: accumulated,
          timestamp: new Date().toISOString(),
        };
        setMessages(prev => [...prev, assistantMsg]);
        setStreamingText("");
        setStreaming(false);
      },
      () => {
        setStreaming(false);
        setStreamingText("");
      },
    );
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  }

  const suggestedQuestions = SUGGESTED.map(s => lang === "hi" ? s.hi : s.en);

  return (
    <>
      {/* Floating Chat Button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="chat-fab"
          aria-label="Open ClaimSaathi AI Companion"
          id="open-chatbot-btn"
        >
          <div className="chat-fab-inner">
            <img
              src="/chatbot-avatar.png"
              alt="ClaimSaathi AI Companion"
              className="chat-fab-img"
            />
            <span className="chat-fab-pulse" />
          </div>
          <span className="chat-fab-label">AI Saathi</span>
        </button>
      )}

      {/* Chat Panel */}
      {isOpen && (
        <div className="chat-panel" id="chatbot-panel">
          {/* Header */}
          <div className="chat-header">
            <div style={{ display: "flex", alignItems: "center", gap: "0.65rem" }}>
              <div className="chat-avatar">
                <img
                  src="/chatbot-avatar.png"
                  alt="ClaimSaathi"
                  className="chat-avatar-img"
                />
              </div>
              <div>
                <div style={{ fontWeight: 700, fontSize: "0.92rem", letterSpacing: "-0.01em" }}>
                  {t("chat.title", "ClaimSaathi Companion")}
                </div>
                <div style={{ fontSize: "0.72rem", color: "var(--mistral-emerald)", display: "flex", alignItems: "center", gap: "0.35rem" }}>
                  <span style={{ width: 6, height: 6, borderRadius: "50%", backgroundColor: "var(--mistral-emerald)", display: "inline-block", boxShadow: "0 0 6px rgba(16, 185, 129, 0.6)" }} />
                  {t("chat.status", "Online • Scoped to Claim")}
                </div>
              </div>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="btn-mistral-ghost"
              style={{ padding: "0.25rem 0.5rem", fontSize: "1.1rem", lineHeight: 1 }}
              aria-label="Close chat"
            >
              ×
            </button>
          </div>

          {/* Messages */}
          <div className="chat-messages" id="chat-messages-container">
            {messages.map((msg, i) => (
              <div
                key={i}
                className={`chat-bubble ${msg.role === "user" ? "chat-bubble-user" : "chat-bubble-ai"}`}
              >
                {msg.role === "assistant" && (
                  <div className="chat-bubble-icon">
                    <img
                      src="/chatbot-avatar.png"
                      alt="AI"
                      className="chat-bubble-avatar-img"
                    />
                  </div>
                )}
                <div
                  className="chat-bubble-text"
                  dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.content) }}
                />
              </div>
            ))}

            {/* Streaming response */}
            {streaming && streamingText && (
              <div className="chat-bubble chat-bubble-ai">
                <div className="chat-bubble-icon">
                  <img
                    src="/chatbot-avatar.png"
                    alt="AI"
                    className="chat-bubble-avatar-img"
                  />
                </div>
                <div
                  className="chat-bubble-text"
                  dangerouslySetInnerHTML={{ __html: renderMarkdown(streamingText) }}
                />
              </div>
            )}

            {/* Typing indicator */}
            {streaming && !streamingText && (
              <div className="chat-bubble chat-bubble-ai">
                <div className="chat-bubble-icon">
                  <img
                    src="/chatbot-avatar.png"
                    alt="AI"
                    className="chat-bubble-avatar-img"
                  />
                </div>
                <div className="chat-typing">
                  <span /><span /><span />
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Suggested questions (only shown when no conversation yet) */}
          {messages.length === 1 && !streaming && (
            <div className="chat-suggestions">
              {suggestedQuestions.map((q, i) => (
                <button
                  key={i}
                  className="chat-suggestion-chip"
                  onClick={() => sendMessage(q)}
                  id={`chat-suggestion-${i}`}
                >
                  {q}
                </button>
              ))}
            </div>
          )}

          {/* Input */}
          <div className="chat-input-area">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={t("chat.placeholder", "Ask about claim, clauses, or documents...")}
              rows={2}
              className="chat-input"
              id="chat-input"
              disabled={streaming}
            />
            <button
              onClick={() => sendMessage(input)}
              disabled={!input.trim() || streaming}
              className="chat-send-btn"
              id="chat-send-btn"
              aria-label="Send message"
            >
              {streaming ? (
                <span className="chat-sending">●</span>
              ) : (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <line x1="22" y1="2" x2="11" y2="13" />
                  <polygon points="22 2 15 22 11 13 2 9 22 2" />
                </svg>
              )}
            </button>
          </div>

          {/* Disclaimer */}
          <div className="chat-disclaimer">
            AI guidance only · Not legal or financial advice · Decision remains with insurer
          </div>
        </div>
      )}
    </>
  );
}
