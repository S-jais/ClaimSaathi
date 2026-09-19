"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { claims, type RejectionResult } from "@/lib/api";
import { MistralNavbar } from "@/components/MistralNavbar";
import {
  PixelArrowRight,
  PixelArrowLeft,
  PixelAlert,
} from "@/components/PixelIcons";
import { useLanguage } from "@/context/LanguageContext";

export default function RejectionDecoderPage() {
  const params = useParams();
  const claimId = (params?.id as string) || "CLM-20491";

  const { lang, setLang } = useLanguage();
  const [result, setResult] = useState<RejectionResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const t =
    lang === "hi"
      ? {
        title: "अस्वीकृति डिकोडर",
        subtitle: "IRDAI 2024 मास्टर परिपत्र पर आधारित त्रिपक्षीय विश्लेषण",
        backToDashboard: "डैशबोर्ड पर वापस जाएं",
        backToReadiness: "तैयारी जाँच पर वापस जाएं",
        claim: "क्लेम",
        repudiationNotice: "अस्वीकृति नोटिस",
        statutoryAlignment: "सांविधिक सामंजस्य",
        contestedClause: "विवादित पॉलिसी क्लॉज",
        contestedClauseDesc: "बीमाकर्ता ने जॉइंट रिप्लेसमेंट सर्जरी पर 24 महीने की प्रतीक्षा अवधि लागू की।",
        governingRule: "लागू विनियामक नियम",
        governingRuleTitle: "60-माह मोरेटोरियम अवरोध",
        governingRuleDesc: "पॉलिसीधारक ने 78 निरंतर महीने पूरे किए हैं। कानूनी रूप से यह अपवर्जन अमान्य एवं शून्य है।",
        factTag: "01. तथ्य (वस्तुनिष्ठ साक्ष्य)",
        factBadge: "पॉलिसीधारक क्लेम सूचना",
        interpTag: "02. AI विनियामक व्याख्या",
        interpBadge: "IRDAI मोरेटोरियम संरक्षण",
        recoTag: "03. व्यावहारिक अनुशंसा",
        recoBadge: "सांविधिक उपचार प्रक्रिया",
        confidence: "पुनर्प्राप्ति विश्वसनीयता",
        confidenceNote: "वैधानिक नियमों के विरुद्ध पॉलिसी क्लॉज मिलान दर्शाता है। यह अनुमोदन की गारंटी नहीं है।",
        buildAppeal: "अपील का मसौदा तैयार करें",
        readinessChecklist: "तैयारी चेकलिस्ट",
        disclaimer:
          "सांविधिक अस्वीकरण: यह विश्लेषण केवल IRDAI 2024 मास्टर परिपत्र के प्रावधानों पर आधारित है। अंतिम दावा निपटान निर्णय पूरी तरह बीमाकर्ता के अधिकार क्षेत्र में रहेगा।",
        factDefault:
          "बीमाकर्ता का दावा अस्वीकृति पत्र दिनांक 14 फरवरी 2026, जिसमें क्लॉज 4.2 (जोड़ों के प्रतिस्थापन के लिए 24 महीने की प्रतीक्षा अवधि) का हवाला देकर ₹1,84,500 की प्रतिपूर्ति खारिज की गई है। हालांकि, पॉलिसी रिकॉर्ड दर्शाते हैं कि पॉलिसी 12 मार्च 2018 को जारी की गई थी और दावा प्रस्तुति के समय 78 निरंतर महीने पूरे हो चुके थे।",
        interpDefault:
          "IRDAI मास्टर सर्कुलर 2024 (अध्याय V, धारा 5.3) के तहत 60 महीने का सांविधिक मोरेटोरियम लागू होता है। इसके अनुसार, 5 वर्ष (60 महीने) की निरंतर कवरेज पूर्ण होने के पश्चात, सिद्ध धोखाधड़ी (Fraud) के अलावा किसी भी आधार (जैसे प्रतीक्षा अवधि या पूर्व-विद्यमान बीमारी) पर क्लेम खारिज नहीं किया जा सकता। अतः बीमाकर्ता का 24-महीने की प्रतीक्षा अवधि का हवाला देना कानूनी रूप से अमान्य और शून्य है।",
        recoDefault:
          "बीमाकर्ता के शिकायत निवारण अधिकारी (GRO) को IRDAI मोरेटोरियम क्लॉज के संदर्भ के साथ औपचारिक शिकायत दर्ज करें। यदि 15 दिनों में समाधान नहीं होता है, तो बीमा लोकपाल (Insurance Ombudsman) के समक्ष अपील दायर करें। नीचे दिए गए बटन से कानूनी रूप से संरचित अपील पत्र तैयार करें।",
      }
      : {
        title: "Rejection Decoder",
        subtitle: "Tripartite schema analysis grounded in IRDAI 2024 Master Circular",
        backToDashboard: "Back to Dashboard",
        backToReadiness: "Back to Readiness Check",
        claim: "Claim",
        repudiationNotice: "Repudiation Notice",
        statutoryAlignment: "Statutory Alignment",
        contestedClause: "Contested Policy Clause",
        contestedClauseDesc: "Insurer invoked 24-month waiting period on Joint Replacement Surgery.",
        governingRule: "Governing Circular Rule",
        governingRuleTitle: "60-Month Moratorium Barrier",
        governingRuleDesc: "Policyholder completed 78 continuous months. Exclusion invalid as a matter of law.",
        factTag: "01. FACT (OBJECTIVE EVIDENCE)",
        factBadge: "Policyholder Claim Notice",
        interpTag: "02. AI REGULATORY INTERPRETATION",
        interpBadge: "IRDAI Moratorium Protection",
        recoTag: "03. ACTIONABLE RECOMMENDATION",
        recoBadge: "Statutory Remedy Protocol",
        confidence: "Retrieval Confidence",
        confidenceNote: "Measures policy clause match. NOT an approval probability.",
        buildAppeal: "Build Appeal Draft",
        readinessChecklist: "Readiness Checklist",
        disclaimer:
          "Statutory Disclaimer: Analysis grounds strictly on IRDAI 2024 Master Circular provisions. Final claim settlement authority remains with the insurer.",
        factDefault: "",
        interpDefault: "",
        recoDefault: "",
      };

  useEffect(() => {
    claims
      .getRejection(claimId)
      .then(setResult)
      .catch((err) => setError(err.message || "Failed to decode rejection"))
      .finally(() => setLoading(false));
  }, [claimId]);

  if (loading) {
    return (
      <div style={{ minHeight: "100vh", backgroundColor: "var(--surface-brand-primary)" }}>
        <MistralNavbar claimId={claimId} />
        <div className="mistral-main max-w-mistral border-grid-x" style={{ padding: "3rem 2rem" }}>
          <div style={{ height: "40px", width: "260px", backgroundColor: "var(--surface-brand-secondary)", marginBottom: "1.5rem" }} />
          <div style={{ height: "180px", width: "100%", backgroundColor: "var(--surface-brand-secondary)" }} />
        </div>
      </div>
    );
  }

  const factText = (lang === "hi" && t.factDefault) ? t.factDefault : (result?.fact_text || "");
  const interpText = (lang === "hi" && t.interpDefault) ? t.interpDefault : (result?.ai_interpretation_text || "");
  const recoText = (lang === "hi" && t.recoDefault) ? t.recoDefault : (result?.recommendation_text || "");

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <MistralNavbar claimId={claimId} />

      <main className="mistral-main" style={{ flex: 1, display: "flex", flexDirection: "column" }}>
        <div className="max-w-mistral border-grid-x" style={{ flex: 1, display: "flex", flexDirection: "column" }}>
          {/* Header Bar */}
          <div className="mistral-stripe" />

          <section className="border-b-grid" style={{ padding: "2rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem" }}>
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.5rem" }}>
                  <Link
                    href={`/claims/${claimId}/readiness`}
                    style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem", color: "var(--text-secondary)", fontSize: "0.8rem", fontWeight: 600 }}
                  >
                    <PixelArrowLeft size={14} /> {t.backToReadiness}
                  </Link>
                  <span style={{ color: "var(--border-secondary)" }}>/</span>
                  <span className="text-eyebrow">{t.claim} {claimId}</span>
                  <span className="mistral-badge badge-danger">{t.repudiationNotice}</span>
                </div>

                <h1 className="text-h1" style={{ marginBottom: "0.5rem" }}>{t.title}</h1>
                <p style={{ color: "var(--text-secondary)", fontSize: "0.95rem" }}>{t.subtitle}</p>
              </div>

              {/* Language Switcher synchronized with LanguageContext */}
              <div style={{ display: "flex", border: "1px solid var(--border-primary)", borderRadius: "3px", overflow: "hidden" }}>
                <button
                  onClick={() => setLang("en")}
                  style={{
                    padding: "0.35rem 0.75rem",
                    fontSize: "0.75rem",
                    fontWeight: 600,
                    backgroundColor: lang === "en" ? "var(--surface-brand-secondary)" : "transparent",
                    color: lang === "en" ? "var(--text-primary)" : "var(--text-tertiary)",
                    cursor: "pointer",
                    border: "none",
                  }}
                >
                  EN
                </button>
                <button
                  onClick={() => setLang("hi")}
                  style={{
                    padding: "0.35rem 0.75rem",
                    fontSize: "0.75rem",
                    fontWeight: 600,
                    borderLeft: "1px solid var(--border-primary)",
                    borderTop: "none",
                    borderRight: "none",
                    borderBottom: "none",
                    backgroundColor: lang === "hi" ? "var(--surface-brand-secondary)" : "transparent",
                    color: lang === "hi" ? "var(--text-primary)" : "var(--text-tertiary)",
                    cursor: "pointer",
                  }}
                >
                  हिन्दी
                </button>
              </div>
            </div>
          </section>

          {/* Confidence Metric Strip */}
          {result && (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", borderBottom: "1px solid var(--border-primary)" }} className="divide-grid-x">
              <div className="mistral-cell">
                <p className="text-eyebrow" style={{ marginBottom: "0.4rem" }}>{t.confidence}</p>
                <div style={{ display: "flex", alignItems: "baseline", gap: "0.75rem" }}>
                  <span className="font-mistral" style={{ fontSize: "2.5rem", fontWeight: 700, color: "var(--mistral-emerald)" }}>
                    {Math.round(result.confidence * 100)}%
                  </span>
                  <span className="mistral-badge badge-ready">{t.statutoryAlignment}</span>
                </div>
                <div className="mistral-progress-track" style={{ marginTop: "0.75rem" }}>
                  <div className="mistral-progress-fill" style={{ width: `${result.confidence * 100}%` }} />
                </div>
                <p style={{ fontSize: "0.75rem", color: "var(--text-tertiary)", marginTop: "0.4rem" }}>
                  ⚠ {t.confidenceNote}
                </p>
              </div>

              <div className="mistral-cell">
                <p className="text-eyebrow" style={{ marginBottom: "0.4rem" }}>{t.contestedClause}</p>
                <span className="font-mistral" style={{ fontSize: "1.15rem", fontWeight: 700, color: "var(--text-primary)", display: "block" }}>
                  {result.clause_ref}
                </span>
                <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginTop: "0.25rem" }}>
                  {t.contestedClauseDesc}
                </p>
              </div>

              <div className="mistral-cell">
                <p className="text-eyebrow" style={{ marginBottom: "0.4rem" }}>{t.governingRule}</p>
                <span className="font-mistral" style={{ fontSize: "1.15rem", fontWeight: 700, color: "var(--mistral-flame)", display: "block" }}>
                  {t.governingRuleTitle}
                </span>
                <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginTop: "0.25rem" }}>
                  {t.governingRuleDesc}
                </p>
              </div>
            </div>
          )}

          {error && (
            <div style={{ padding: "1.25rem 2rem", backgroundColor: "var(--status-danger-bg)", color: "var(--status-danger-text)" }}>
              {error}
            </div>
          )}

          {/* Tripartite Breakdown Section */}
          {result && (
            <div className="divide-grid-y">
              {/* Panel 1: FACT */}
              <div className="mistral-cell" style={{ backgroundColor: "var(--surface-brand-primary)" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.75rem" }}>
                  <span className="text-eyebrow" style={{ color: "var(--text-tertiary)" }}>
                    {t.factTag}
                  </span>
                  <span className="mistral-badge">{t.factBadge}</span>
                </div>
                <p style={{ color: "var(--text-primary)", fontSize: "0.975rem", lineHeight: 1.7, fontWeight: 500 }}>
                  {factText}
                </p>
              </div>

              {/* Panel 2: AI INTERPRETATION */}
              <div className="mistral-cell" style={{ backgroundColor: "var(--surface-brand-secondary)" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.75rem" }}>
                  <span className="text-eyebrow" style={{ color: "var(--mistral-flame)" }}>
                    {t.interpTag}
                  </span>
                  <span className="mistral-badge badge-flame">{t.interpBadge}</span>
                </div>
                <div style={{ color: "var(--text-primary)", fontSize: "0.95rem", lineHeight: 1.7, whiteSpace: "pre-wrap" }}>
                  {interpText}
                </div>
              </div>

              {/* Panel 3: RECOMMENDATION */}
              <div className="mistral-cell" style={{ backgroundColor: "var(--surface-brand-primary)" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.75rem" }}>
                  <span className="text-eyebrow" style={{ color: "var(--mistral-emerald)" }}>
                    {t.recoTag}
                  </span>
                  <span className="mistral-badge badge-ready">{t.recoBadge}</span>
                </div>
                <div style={{ color: "var(--text-primary)", fontSize: "0.95rem", lineHeight: 1.7, whiteSpace: "pre-wrap" }}>
                  {recoText}
                </div>
              </div>
            </div>
          )}

          {/* Regulatory Disclaimer Banner */}
          <div className="border-t-grid mistral-banner-notice">
            <PixelAlert size={16} />
            <p>{t.disclaimer}</p>
          </div>

          {/* Action Footer */}
          <div className="border-t-grid" style={{ padding: "1.75rem 2rem", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem" }}>
            <Link href={`/claims/${claimId}/readiness`} className="btn-mistral-outline">
              <PixelArrowLeft size={16} /> {t.readinessChecklist}
            </Link>

            <Link
              href={`/claims/${claimId}/appeal`}
              className="btn-mistral-cta"
              id="proceed-appeal-btn"
            >
              <span className="cta-arrow-left">
                <PixelArrowRight size={18} />
              </span>
              <span className="cta-label">{t.buildAppeal}</span>
              <span className="cta-arrow-right">
                <PixelArrowRight size={18} />
              </span>
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
}
