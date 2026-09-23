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

  const { lang, t } = useLanguage();
  const [result, setResult] = useState<RejectionResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

  // Multilingual fallback texts for the 3-part schema
  const factText =
    lang === "hi"
      ? "बीमाकर्ता का दावा अस्वीकृति पत्र दिनांक 14 फरवरी 2026, जिसमें क्लॉज 4.2 (जोड़ों के प्रतिस्थापन के लिए 24 महीने की प्रतीक्षा अवधि) का हवाला देकर ₹1,84,500 की प्रतिपूर्ति खारिज की गई है। हालांकि, पॉलिसी रिकॉर्ड दर्शाते हैं कि पॉलिसी 12 मार्च 2018 को जारी की गई थी और दावा प्रस्तुति के समय 78 निरंतर महीने पूरे हो चुके थे।"
      : lang === "hinglish"
      ? "Insurer ka claim rejection letter dated 14 Feb 2026, jisme Clause 4.2 (Joint replacement ke liye 24-month waiting period) cite karke ₹1,84,500 ka reimbursement reject kiya gaya hai. Lekin policy records show karte hain ki policy 12 March 2018 ko issue hui thi aur claim ke waqt 78 continuous months poore ho chuke the."
      : result?.fact_text || "Insurer repudiation letter dated 14 February 2026 citing Clause 4.2 (24-month waiting period for Joint Replacement Surgery) to disallow reimbursement of ₹1,84,500. However, policy schedules verify original inception on 12 March 2018 with 78 continuous months completed at claim inception.";

  const interpText =
    lang === "hi"
      ? "IRDAI मास्टर सर्कुलर 2024 (अध्याय V, धारा 5.3) के तहत 60 महीने का सांविधिक मोरेटोरियम लागू होता है। इसके अनुसार, 5 वर्ष (60 महीने) की निरंतर कवरेज पूर्ण होने के पश्चात, सिद्ध धोखाधड़ी (Fraud) के अलावा किसी भी आधार (जैसे प्रतीक्षा अवधि या पूर्व-विद्यमान बीमारी) पर क्लेम खारिज नहीं किया जा सकता। अतः बीमाकर्ता का 24-महीने की प्रतीक्षा अवधि का हवाला देना कानूनी रूप से अमान्य और शून्य है।"
      : lang === "hinglish"
      ? "IRDAI Master Circular 2024 (Chapter V, Section 5.3) ke under 60-month statutory moratorium apply hota hai. Iske mutabik, 5 saal (60 months) continuous coverage complete hone ke baad fraud ke alawa kisi bhi ground (jaise waiting period ya pre-existing disease) par claim reject nahi kiya ja sakta. Isliye insurer ka Clause 4.2 cite karna legally invalid aur void hai."
      : result?.ai_interpretation_text || "Under IRDAI Master Circular 2024 (Chapter V, Section 5.3), a 60-month statutory moratorium applies. After 5 years of continuous coverage, no health claim may be contested on non-disclosure or waiting period grounds except proven fraud. The insurer's invocation of Clause 4.2 is legally void and unenforceable.";

  const recoText =
    lang === "hi"
      ? "बीमाकर्ता के शिकायत निवारण अधिकारी (GRO) को IRDAI मोरेटोरियम क्लॉज के संदर्भ के साथ औपचारिक शिकायत दर्ज करें। यदि 15 दिनों में समाधान नहीं होता है, तो बीमा लोकपाल (Insurance Ombudsman) के समक्ष अपील दायर करें। नीचे दिए गए बटन से कानूनी रूप से संरचित अपील पत्र तैयार करें।"
      : lang === "hinglish"
      ? "Insurer ke Grievance Redressal Officer (GRO) ko IRDAI moratorium clause quote karte hue formal representation file karein. Agar 15 din mein redressal na mile, toh Insurance Ombudsman ke paas appeal karein. Niche diye gaye button se legal appeal letter export karein."
      : result?.recommendation_text || "Submit a formal representation to the insurer's Grievance Redressal Officer (GRO) citing Section 5.3 statutory moratorium protections. If unresolved within 15 days, escalate to the Insurance Ombudsman. Click below to generate your clause-by-clause grievance appeal draft.";

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
                    <PixelArrowLeft size={14} /> {t("readiness.backToDashboard", "Back to Readiness Check")}
                  </Link>
                  <span style={{ color: "var(--border-secondary)" }}>/</span>
                  <span className="text-eyebrow">{t("rejection.claim", "Claim")} {claimId}</span>
                  <span className="mistral-badge badge-danger">{t("claimHub.repudiatedBadge", "Repudiated by TPA")}</span>
                </div>

                <h1 className="text-h1" style={{ marginBottom: "0.5rem" }}>{t("rejection.title", "Rejection Decoder")}</h1>
                <p style={{ color: "var(--text-secondary)", fontSize: "0.95rem" }}>{t("rejection.subtitle", "Tripartite schema analysis grounded in IRDAI 2024 Master Circular")}</p>
              </div>
            </div>
          </section>

          {/* Confidence Metric Strip */}
          {result && (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", borderBottom: "1px solid var(--border-primary)" }} className="divide-grid-x">
              <div className="mistral-cell">
                <p className="text-eyebrow" style={{ marginBottom: "0.4rem" }}>{t("rejection.confidence", "Retrieval Confidence")}</p>
                <div style={{ display: "flex", alignItems: "baseline", gap: "0.75rem" }}>
                  <span className="font-mistral" style={{ fontSize: "2.5rem", fontWeight: 700, color: "var(--mistral-emerald)" }}>
                    {Math.round(result.confidence * 100)}%
                  </span>
                  <span className="mistral-badge badge-ready">{t("claimHub.shieldBadge", "Statutory Alignment")}</span>
                </div>
                <div className="mistral-progress-track" style={{ marginTop: "0.75rem" }}>
                  <div className="mistral-progress-fill" style={{ width: `${result.confidence * 100}%` }} />
                </div>
                <p style={{ fontSize: "0.75rem", color: "var(--text-tertiary)", marginTop: "0.4rem" }}>
                  ⚠ {t("rejection.confidenceNote", "Measures policy clause match against statutory rules. NOT an approval probability.")}
                </p>
              </div>

              <div className="mistral-cell">
                <p className="text-eyebrow" style={{ marginBottom: "0.4rem" }}>{t("rejection.clauseInvoked", "Clause Invoked by Insurer")}</p>
                <span className="font-mistral" style={{ fontSize: "1.15rem", fontWeight: 700, color: "var(--text-primary)", display: "block" }}>
                  {result.clause_ref || "Clause 4.2"}
                </span>
                <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginTop: "0.25rem" }}>
                  {lang === "hi"
                    ? "बीमाकर्ता ने जॉइंट रिप्लेसमेंट सर्जरी पर 24 महीने की प्रतीक्षा अवधि लागू की।"
                    : lang === "hinglish"
                    ? "Insurer ne joint replacement surgery par 24-month waiting period invoke kiya."
                    : "Insurer invoked 24-month waiting period on Joint Replacement Surgery."}
                </p>
              </div>

              <div className="mistral-cell">
                <p className="text-eyebrow" style={{ marginBottom: "0.4rem" }}>{t("rejection.statutoryRule", "Statutory Grounding Rule")}</p>
                <span className="font-mistral" style={{ fontSize: "1.15rem", fontWeight: 700, color: "var(--mistral-flame)", display: "block" }}>
                  {lang === "hi" ? "60-माह मोरेटोरियम अवरोध" : lang === "hinglish" ? "60-Month Moratorium Barrier" : "60-Month Moratorium Barrier"}
                </span>
                <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginTop: "0.25rem" }}>
                  {lang === "hi"
                    ? "पॉलिसीधारक ने 78 निरंतर महीने पूरे किए हैं। कानूनी रूप से यह अपवर्जन अमान्य एवं शून्य है।"
                    : lang === "hinglish"
                    ? "Policyholder ne 78 continuous months complete kiye hain. Exclusion legally void hai."
                    : "Policyholder completed 78 continuous months. Exclusion invalid as a matter of law."}
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
                    {t("rejection.factTag", "01. FACT (OBJECTIVE EVIDENCE)")}
                  </span>
                  <span className="mistral-badge">{t("dashboard.activeAccount", "Policyholder Notice")}</span>
                </div>
                <p style={{ color: "var(--text-primary)", fontSize: "0.975rem", lineHeight: 1.7, fontWeight: 500 }}>
                  {factText}
                </p>
              </div>

              {/* Panel 2: AI INTERPRETATION */}
              <div className="mistral-cell" style={{ backgroundColor: "var(--surface-brand-secondary)" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.75rem" }}>
                  <span className="text-eyebrow" style={{ color: "var(--mistral-flame)" }}>
                    {t("rejection.interpTag", "02. AI REGULATORY INTERPRETATION")}
                  </span>
                  <span className="mistral-badge badge-flame">{t("dashboard.moratoriumActive", "IRDAI Protection")}</span>
                </div>
                <div style={{ color: "var(--text-primary)", fontSize: "0.95rem", lineHeight: 1.7, whiteSpace: "pre-wrap" }}>
                  {interpText}
                </div>
              </div>

              {/* Panel 3: RECOMMENDATION */}
              <div className="mistral-cell" style={{ backgroundColor: "var(--surface-brand-primary)" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.75rem" }}>
                  <span className="text-eyebrow" style={{ color: "var(--mistral-emerald)" }}>
                    {t("rejection.recoTag", "03. ACTIONABLE RECOMMENDATION")}
                  </span>
                  <span className="mistral-badge badge-ready">{t("readiness.nextRemediation", "Next Step")}</span>
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
            <p>{t("rejection.disclaimer", "Statutory Disclaimer: Analysis grounds strictly on IRDAI 2024 Master Circular provisions. Final claim settlement authority remains with the insurer.")}</p>
          </div>

          {/* Action Footer */}
          <div className="border-t-grid" style={{ padding: "1.75rem 2rem", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem" }}>
            <Link href={`/claims/${claimId}/readiness`} className="btn-mistral-outline">
              <PixelArrowLeft size={16} /> {t("readiness.checklistHeader", "Readiness Checklist")}
            </Link>

            <Link
              href={`/claims/${claimId}/appeal`}
              className="btn-mistral-cta"
              id="proceed-appeal-btn"
            >
              <span className="cta-arrow-left">
                <PixelArrowRight size={18} />
              </span>
              <span className="cta-label">{t("rejection.buildAppeal", "Build Appeal Draft")}</span>
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
