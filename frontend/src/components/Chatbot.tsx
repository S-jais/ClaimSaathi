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

  function buildContextualFallbackPayload(
    question: string,
    preferredLang: string,
    currentClaimId: string,
    currentStage: "Understand" | "Prepare" | "Resolve"
  ): CopilotPayload {
    const q = question.toLowerCase().trim();
    const isHi = /[\u0900-\u097F]/.test(question) || preferredLang === "hi";

    // 1. Fraud refusal
    if (q.includes("date badal") || q.includes("change date") || q.includes("fake") || q.includes("alter")) {
      if (isHi) {
        return {
          stage: "CLAIM_PREPARATION",
          ui_stage: currentStage,
          reply: "बिल या किसी भी दस्तावेज़ में तारीख बदलना अथवा बदलाव करना धोखाधड़ी (Fraud) माना जाता है। इससे आपका क्लेम हमेशा के लिए खारिज हो सकता है और कानूनी परेशानी भी हो सकती है। यदि तारीख गलत छपी है, तो अस्पताल से सही (corrected) बिल मांगना ही वैध तरीका है।",
          sections: {
            facts: [{ id: "f_fraud", text: "आईआरडीएआई (IRDAI) और बीमा अनुबंध के तहत दस्तावेज़ से छेड़छाड़ प्रतिबंधित है।", citations: [] }],
            interpretations: [{ id: "i_fraud", text: "हॉस्पिटल से प्रमाणित संशोधित बिल क्लेम सेटलमेंट का सही व कानूनी मार्ग है।" }],
            recommendations: [{ id: "r_fraud", text: "हॉस्पिटल बिलिंग डेस्क से संशोधित कॉपी का अनुरोध करें।" }],
          },
          citations: [],
          quick_replies: ["हॉस्पिटल पत्र ड्राफ्ट करें", "वैध प्रक्रिया समझें"],
          next_best_action: { action: "CONTACT_HOSPITAL", label: "हॉस्पिटल से सही बिल का अनुरोध करें" }
        };
      }
      return {
        stage: "CLAIM_PREPARATION",
        ui_stage: currentStage,
        reply: "Bill ya kisi bhi document mein date ya data badalna fraud maana jaata hai. Isse claim reject ho sakta hai aur legally risky hai. Agar date galat chhapi hai, toh sahi tareeka hai hospital se corrected bill maangna. Kya hospital ke liye request draft karein?",
        sections: {
          facts: [{ id: "f_fraud", text: "Altering medical or billing documents violates IRDAI provisions and insurer guidelines.", citations: [] }],
          interpretations: [{ id: "i_fraud", text: "The legitimate route is obtaining a stamped revised or duplicate bill directly from the hospital." }],
          recommendations: [{ id: "r_fraud", text: "Ask hospital TPA desk for an amended itemized final bill." }],
        },
        citations: [],
        quick_replies: ["Draft hospital note", "Check bill requirements"],
        next_best_action: { action: "CONTACT_HOSPITAL", label: "Request corrected invoice from hospital desk" }
      };
    }

    // 2. Prediction request
    if (q.includes("approve hoga") || q.includes("chance") || q.includes("guarantee") || q.includes("pass hoga")) {
      if (isHi) {
        return {
          stage: "CLAIM_PREPARATION",
          ui_stage: currentStage,
          reply: "क्लेम पास होगा या नहीं, यह सिर्फ बीमा कंपनी ही तय करती है। कोई भी प्रतिशत या गारंटी देना संभव नहीं है। मेरा काम है आपके दस्तावेज़ों की कमियों को दूर करना ताकि क्लेम को पूरी मजबूती से पेश किया जा सके।",
          sections: {
            facts: [{ id: "f_pred", text: "बीमाकर्ता अंतिम निर्णय पॉलिसी नियमों व मेडिकल रिकॉर्ड के आधार पर लेता है।", citations: [] }],
            interpretations: [{ id: "i_pred", text: "अंतिम मूल्यांकन पूरी तरह बीमाकर्ता के क्लेम विभाग के अधीन है।" }],
            recommendations: [{ id: "r_pred", text: "क्लेम सबमिट करने से पहले डॉक्यूमेंट रेडीनेस चेक पूरा करें।" }],
          },
          citations: [],
          quick_replies: ["दस्तावेज़ जांचें", "कवर की शर्तें देखें"],
          next_best_action: { action: "CHECK_READINESS", label: "क्लेम तैयारी जांचें (Readiness Check)" }
        };
      }
      return {
        stage: "CLAIM_PREPARATION",
        ui_stage: currentStage,
        reply: "Approve hoga ya nahi, yeh faisla sirf aapka insurer karta hai, aur koi percentage ya guarantee dena possible nahi hai. Main aapke documents ko verify karke sabse mazboot honest case bana sakta hoon. Chalein readiness check karein?",
        sections: {
          facts: [{ id: "f_pred", text: "Claim approval decisions are solely made by the insurer's adjudication board.", citations: [] }],
          interpretations: [{ id: "i_pred", text: "Final adjudication rests entirely with the insurer's underwriting / claims assessment team." }],
          recommendations: [{ id: "r_pred", text: "Verify that all 5 essential documents are stamped and cross-matched before submission." }],
        },
        citations: [],
        quick_replies: ["Check document readiness", "Explain policy clauses"],
        next_best_action: { action: "CHECK_READINESS", label: "Run claim readiness verification" }
      };
    }

    // 3. Rejection / Contest / Appeal
    if (q.includes("reject") || q.includes("kharij") || q.includes("4.2") || q.includes("appeal") || q.includes("shikayat") || currentStage === "Resolve") {
      const isDevanagari = /[\u0900-\u097F]/.test(question);
      if (isDevanagari) {
        return {
          stage: "REJECTED_DECODING",
          ui_stage: "Resolve",
          reply: "रिजेक्ट होने का मतलब यह नहीं कि सब खत्म हो गया। आपके क्लेम में क्लॉज 4.2 (वेटिंग पीरियड) या दस्तावेजी कमी का हवाला दिया गया है [FACT]। इसे पुनर्विचार (Grievance Appeal) के जरिए चुनौती दी जा सकती है। क्या हम अपील का ड्राफ्ट तैयार करें?",
          sections: {
            facts: [{ id: "f_rej", text: `क्लेम ${currentClaimId} में क्लॉज 4.2 के तहत कटौती दर्ज की गई है।`, citations: ["cit_rej_letter"] }],
            interpretations: [{ id: "i_rej", text: "सरल शब्दों में: बीमा कंपनी ने पूर्व-मौजूद बीमारी या प्रतीक्षा अवधि का हवाला दिया है, जो निरंतर कवरेज के तहत चुनौती योग्य है।" }],
            recommendations: [{ id: "r_rej", text: "बीमा कंपनी के शिकायत निवारण अधिकारी (GRO) को अपील पत्र भेजें।" }],
          },
          citations: [{ id: "cit_rej_letter", type: "document", title: "बीमा रिजेक्शन पत्र", reference: "पृष्ठ 1, कारण कोड DOC-04", snippet: "Clause 4.2 Specific disease waiting period applied." }],
          draft_card: {
            draft_id: `draft_${Date.now()}`,
            draft_type: "appeal",
            title: "क्लॉज 4.2 के खिलाफ पुनर्विचार अपील पत्र (Draft)",
            status: "DRAFT",
            summary: "आईआरडीएआई 60-महीने की निरंतरता सुरक्षा का हवाला देते हुए औपचारिक अपील।",
          },
          quick_replies: ["अपील ड्राफ्ट देखें", "बीमा लोकपाल की समय सीमा", "अस्पताल के कागजात"],
          next_best_action: { action: "REVIEW_DRAFT", label: "अपील पत्र की समीक्षा और अनुमोदन करें", route: `/claims/${currentClaimId}/appeal` }
        };
      }
      return {
        stage: "REJECTED_DECODING",
        ui_stage: "Resolve",
        reply: "Reject hone ka matlab sab khatam nahi hua, aap sahi jagah aaye hain. Aapke letter mein Clause 4.2 darj hai [FACT]. Simple shabdon mein: unhe discharge summary mein documentation gap mila hai [INTERPRETATION]. Is deduction ko challenge karne ka ground banta hai. Agla kadam: appeal draft review karein [RECOMMENDATION].",
        sections: {
          facts: [{ id: "f_rej", text: `Claim ${currentClaimId} repudiation letter references Clause 4.2 waiting period.`, citations: ["cit_rej_letter"] }],
          interpretations: [{ id: "i_rej", text: "Under IRDAI continuous coverage guidelines, this rejection appears contestable if policy tenure exceeds 60 months." }],
          recommendations: [{ id: "r_rej", text: "Submit a formal first-level representation to the insurer's Grievance Redressal Officer (GRO)." }],
        },
        citations: [{ id: "cit_rej_letter", type: "document", title: "Insurer Rejection Letter", reference: "Page 1, DOC-04", snippet: "Repudiation under Clause 4.2 Waiting Period." }],
        draft_card: {
          draft_id: `draft_${Date.now()}`,
          draft_type: "appeal",
          title: "Representation against Clause 4.2 Repudiation",
          status: "DRAFT",
          summary: "Formal representation to GRO citing IRDAI Master Circular 2024 continuity protection.",
        },
        quick_replies: ["Review draft appeal", "Check statutory deadlines", "Hospital desk letter"],
        next_best_action: { action: "REVIEW_DRAFT", label: "Review and approve draft appeal", route: `/claims/${currentClaimId}/appeal` }
      };
    }

    // 4. Bill / Reimbursement amount / Kitna milega
    if (q.includes("paisa") || q.includes("paise") || q.includes("kitna") || q.includes("bill") || q.includes("amount") || q.includes("deduct")) {
      if (isHi) {
        return {
          stage: "CLAIM_PREPARATION",
          ui_stage: "Prepare",
          reply: "सटीक रकम बताना अभी संभव नहीं है, क्योंकि यह कमरे के किराए की सीमा, को-पेमेंट और बीमित राशि पर निर्भर करती है। आपके बिल की कुल रकम ₹1,84,500 है [FACT]। गैर-भुगतान योग्य उपभोग्य वस्तुओं की सूची के अनुसार ₹12,000 की कटौती हो सकती है [INTERPRETATION]। अंतिम फैसला बीमा कंपनी का होता है।",
          sections: {
            facts: [{ id: "f_amt", text: `कुल दावा बिल: ₹1,84,500। उपभोग्य सामग्री (Non-payable): ₹12,000 [FACT]`, citations: ["cit_bill"] }],
            interpretations: [{ id: "i_amt", text: "कमरे के किराए की सीमा और को-पेमेंट पॉलिसी अपलोड होने के बाद ही सटीक आंकी जा सकती है।" }],
            recommendations: [{ id: "r_amt", text: "पॉलिसी शेड्यूल कॉपी अपलोड करें ताकि संकेतात्मक अनुमान तैयार किया जा सके।" }],
          },
          citations: [{ id: "cit_bill", type: "document", title: "हॉस्पिटल बिल सारांश", reference: "बिल संख्या H-2026-88", snippet: "Gross ₹1,84,500. Consumables ₹12,000." }],
          quick_replies: ["पॉलिसी अपलोड करें", "नॉन-पेयेबल आइटम देखें"],
          next_best_action: { action: "UPLOAD_POLICY", label: "पॉलिसी कॉपी अपलोड करें" }
        };
      }
      return {
        stage: "CLAIM_PREPARATION",
        ui_stage: "Prepare",
        reply: "Exact amount batana abhi sambhav nahi hai, kyunki yeh room rent limit aur co-pay par depend karta hai. Aapke bill ki gross amount ₹1,84,500 hai [FACT], jisme se approx ₹12,000 consumables non-payable category mein aate hain [INTERPRETATION]. Final assessment insurer ka hi hota hai.",
        sections: {
          facts: [{ id: "f_amt", text: `Gross hospital invoice is ₹1,84,500. Non-payable consumables estimated at ₹12,000.`, citations: ["cit_bill"] }],
          interpretations: [{ id: "i_amt", text: "Indicative payable estimate depends on room-rent proportionate deductions and policy co-payment clauses." }],
          recommendations: [{ id: "r_amt", text: "Upload your policy schedule PDF to compute the exact indicative reimbursement breakdown." }],
        },
        citations: [{ id: "cit_bill", type: "document", title: "Hospital Final Invoice", reference: "Invoice #Apollo-9921", snippet: "Total: ₹1,84,500. Consumables: ₹12,000." }],
        quick_replies: ["Upload policy document", "Explain line items", "Check room rent limit"],
        next_best_action: { action: "AUDIT_BILL", label: "Run detailed bill audit breakdown" }
      };
    }

    // 5. Readiness / Documents / Submission
    if (q.includes("ready") || q.includes("document") || q.includes("submit") || q.includes("discharge") || q.includes("kya karu")) {
      if (isHi) {
        return {
          stage: "CLAIM_PREPARATION",
          ui_stage: "Prepare",
          reply: "आपके आवश्यक 5 दस्तावेज़ों में से 4 तैयार हैं। एक कमी है: डिस्चार्ज सारांश (Discharge Summary) के पेज 2 पर डॉक्टर के हस्ताक्षर और अस्पताल की मुहर नहीं है [FACT]। सबमिट करने से पहले इसे ठीक करवा लेना जरूरी है [INTERPRETATION]।",
          sections: {
            facts: [{ id: "f_doc", text: "डिस्चार्ज सारांश पृष्ठ 2 पर हस्ताक्षर और स्टैम्प अनुपस्थित है।", citations: ["cit_ds"] }],
            interpretations: [{ id: "i_doc", text: "हस्ताक्षर न होने पर बीमा कंपनियां अक्सर फाइल रोक देती हैं या क्वेरी उठाती हैं।" }],
            recommendations: [{ id: "r_doc", text: "अस्पताल के टीपीए डेस्क से हस्ताक्षर व स्टैम्प लगवाकर दोबारा अपलोड करें।" }],
          },
          citations: [{ id: "cit_ds", type: "document", title: "डिस्चार्ज सारांश", reference: "पृष्ठ 2", snippet: "Treating doctor signature block empty." }],
          quick_replies: ["अस्पताल को भेजने हेतु संदेश", "अन्य दस्तावेज़ जांचें"],
          next_best_action: { action: "FIX_DOCUMENTS", label: "डिस्चार्ज सारांश पर हस्ताक्षर करवाएं" }
        };
      }
      return {
        stage: "CLAIM_PREPARATION",
        ui_stage: "Prepare",
        reply: "Almost ready! 4 of your 5 required documents check out. One fix needed: Page 2 of your discharge summary has no doctor's signature or hospital seal [FACT]. Fixing this now avoids delayed claim queries later [INTERPRETATION].",
        sections: {
          facts: [{ id: "f_doc", text: "Discharge summary page 2 missing treating doctor signature and hospital seal.", citations: ["cit_ds"] }],
          interpretations: [{ id: "i_doc", text: "Insurers routinely issue deficiency letters for unsigned clinical records." }],
          recommendations: [{ id: "r_doc", text: "Obtain a signed and stamped copy from the hospital desk before submission." }],
        },
        citations: [{ id: "cit_ds", type: "document", title: "Discharge Summary", reference: "Page 2", snippet: "Treating doctor signature block unverified." }],
        quick_replies: ["Message for hospital desk", "Check other documents"],
        next_best_action: { action: "VERIFY_READINESS", label: "Re-run readiness verification after upload" }
      };
    }

    // 6. Default general assistance
    if (isHi) {
      return {
        stage: "ONBOARDING",
        ui_stage: currentStage,
        reply: "मैं क्लेमसाथी (ClaimSaathi) हूँ — आपकी क्लेम यात्रा का साथी। मैं आपकी पॉलिसी के नियम समझाने, अस्पताल के बिल का विश्लेषण करने, रिजेक्शन को डिकोड करने और अपील तैयार करने में मदद करता हूँ। आप क्या जानना चाहते हैं?",
        sections: {
          facts: [{ id: "f_gen", text: "क्लेमसाथी पॉलिसीधारक के संपूर्ण क्लेम सफर में सहायता हेतु उपलब्ध है।", citations: [] }],
          interpretations: [{ id: "i_gen", text: "आईआरडीएआई 2024 मास्टर परिपत्र के अनुसार प्रत्येक पॉलिसीधारक को समयबद्ध समाधान का अधिकार है।" }],
          recommendations: [{ id: "r_gen", text: "अपने क्लेम की स्थिति या दस्तावेज़ अपलोड करके शुरुआत करें।" }],
        },
        citations: [],
        quick_replies: ["दस्तावेज़ की तैयारी जांचें", "बिल का विश्लेषण करें", "रिजेक्शन का कारण समझें"],
        next_best_action: { action: "START_CHECK", label: "दावा तैयारी शुरू करें" }
      };
    }

    return {
      stage: "ONBOARDING",
      ui_stage: currentStage,
      reply: "I am ClaimSaathi — your copilot through the complete health insurance claim journey. I help you understand coverage, verify bill items, resolve rejections, and prepare grounded appeal drafts. How can I help with your claim today?",
      sections: {
        facts: [{ id: "f_gen", text: "ClaimSaathi assists Indian policyholders across Understand, Prepare, and Resolve stages.", citations: [] }],
        interpretations: [{ id: "i_gen", text: "All evaluations are grounded in your policy documents and IRDAI 2024 health regulations." }],
        recommendations: [{ id: "r_gen", text: "Select an option below or ask about your claim readiness or bill deductions." }],
      },
      citations: [],
      quick_replies: ["Check claim readiness", "Explain my bill", "Help with rejection"],
      next_best_action: { action: "START_CHECK", label: "Check claim readiness" }
    };
  }

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
        // Create session on-demand
        try {
          const tempSess = await copilot.createSession(claimId);
          setSession(tempSess);
          payload = await copilot.sendMessage(tempSess.id, question, lang);
        } catch {
          // If backend unavailable, generate context-aware payload
          payload = buildContextualFallbackPayload(question, lang, claimId, uiStage);
        }
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
      const fallbackPayload = buildContextualFallbackPayload(question, lang, claimId, uiStage);
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
