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

export default function RejectionDecoderPage() {
  const params = useParams();
  const claimId = (params?.id as string) || "CLM-20491";

  const [result, setResult] = useState<RejectionResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lang, setLang] = useState<"en" | "hi">("en");

  const t =
    lang === "hi"
      ? {
        title: "अस्वीकृति डिकोडर",
        subtitle: "IRDAI 2024 मास्टर परिपत्र पर आधारित त्रिपक्षीय विश्लेषण",
        factTag: "01. तथ्य (वस्तुनिष्ठ साक्ष्य)",
        interpTag: "02. AI विनियामक व्याख्या",
        recoTag: "03. व्यावहारिक अनुशंसा",
        confidence: "पुनर्प्राप्ति विश्वसनीयता",
        confidenceNote: "पॉलिसी क्लॉज मिलान दर्शाता है। यह अनुमोदन की गारंटी नहीं है।",
        buildAppeal: "अपील का मसौदा तैयार करें",
        disclaimer:
          "सांविधिक अस्वीकरण: यह विश्लेषण IRDAI 2024 मास्टर परिपत्र के प्रावधानों पर आधारित है। अंतिम दावा निर्णय केवल बीमाकर्ता का होगा।",
      }
      : {
        title: "Rejection Decoder",
        subtitle: "Tripartite schema analysis grounded in IRDAI 2024 Master Circular",
        factTag: "01. FACT (OBJECTIVE EVIDENCE)",
        interpTag: "02. AI REGULATORY INTERPRETATION",
        recoTag: "03. ACTIONABLE RECOMMENDATION",
        confidence: "Retrieval Confidence",
        confidenceNote: "Measures policy clause match. NOT an approval probability.",
        buildAppeal: "Build Appeal Draft",
        disclaimer:
          "Statutory Disclaimer: Analysis grounds strictly on IRDAI 2024 Master Circular provisions. Final claim settlement authority remains with the insurer.",
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
                    <PixelArrowLeft size={14} /> Back to Readiness Check
                  </Link>
                  <span style={{ color: "var(--border-secondary)" }}>/</span>
                  <span className="text-eyebrow">Claim {claimId}</span>
                  <span className="mistral-badge badge-danger">Repudiation Notice</span>
                </div>

                <h1 className="text-h1" style={{ marginBottom: "0.5rem" }}>{t.title}</h1>
                <p style={{ color: "var(--text-secondary)", fontSize: "0.95rem" }}>{t.subtitle}</p>
              </div>

              {/* Language Switcher */}
              <div style={{ display: "flex", border: "1px solid var(--border-primary)", borderRadius: "3px", overflow: "hidden" }}>
                <button
                  onClick={() => setLang("en")}
                  style={{
                    padding: "0.35rem 0.75rem",
                    fontSize: "0.75rem",
                    fontWeight: 600,
                    backgroundColor: lang === "en" ? "var(--surface-brand-secondary)" : "transparent",
                    color: lang === "en" ? "var(--text-primary)" : "var(--text-tertiary)",
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
                    backgroundColor: lang === "hi" ? "var(--surface-brand-secondary)" : "transparent",
                    color: lang === "hi" ? "var(--text-primary)" : "var(--text-tertiary)",
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
                  <span className="mistral-badge badge-ready">Statutory Alignment</span>
                </div>
                <div className="mistral-progress-track" style={{ marginTop: "0.75rem" }}>
                  <div className="mistral-progress-fill" style={{ width: `${result.confidence * 100}%` }} />
                </div>
                <p style={{ fontSize: "0.75rem", color: "var(--text-tertiary)", marginTop: "0.4rem" }}>
                  ⚠ {t.confidenceNote}
                </p>
              </div>

              <div className="mistral-cell">
                <p className="text-eyebrow" style={{ marginBottom: "0.4rem" }}>Contested Policy Clause</p>
                <span className="font-mistral" style={{ fontSize: "1.15rem", fontWeight: 700, color: "var(--text-primary)", display: "block" }}>
                  {result.clause_ref}
                </span>
                <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginTop: "0.25rem" }}>
                  Insurer invoked 24-month waiting period on Joint Replacement Surgery.
                </p>
              </div>

              <div className="mistral-cell">
                <p className="text-eyebrow" style={{ marginBottom: "0.4rem" }}>Governing Circular Rule</p>
                <span className="font-mistral" style={{ fontSize: "1.15rem", fontWeight: 700, color: "var(--mistral-flame)", display: "block" }}>
                  60-Month Moratorium Barrier
                </span>
                <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginTop: "0.25rem" }}>
                  Policyholder completed 78 continuous months. Exclusion invalid as a matter of law.
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
                  <span className="mistral-badge">Policyholder Claim Notice</span>
                </div>
                <p style={{ color: "var(--text-primary)", fontSize: "0.975rem", lineHeight: 1.7, fontWeight: 500 }}>
                  {result.fact_text}
                </p>
              </div>

              {/* Panel 2: AI INTERPRETATION */}
              <div className="mistral-cell" style={{ backgroundColor: "var(--surface-brand-secondary)" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.75rem" }}>
                  <span className="text-eyebrow" style={{ color: "var(--mistral-flame)" }}>
                    {t.interpTag}
                  </span>
                  <span className="mistral-badge badge-demo">IRDAI Moratorium Protection</span>
                </div>
                <div style={{ color: "var(--text-primary)", fontSize: "0.95rem", lineHeight: 1.7, whiteSpace: "pre-wrap" }}>
                  {result.ai_interpretation_text}
                </div>
              </div>

              {/* Panel 3: RECOMMENDATION */}
              <div className="mistral-cell" style={{ backgroundColor: "var(--surface-brand-primary)" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.75rem" }}>
                  <span className="text-eyebrow" style={{ color: "var(--mistral-emerald)" }}>
                    {t.recoTag}
                  </span>
                  <span className="mistral-badge badge-ready">Statutory Remedy Protocol</span>
                </div>
                <div style={{ color: "var(--text-primary)", fontSize: "0.95rem", lineHeight: 1.7, whiteSpace: "pre-wrap" }}>
                  {result.recommendation_text}
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
              <PixelArrowLeft size={16} /> Readiness Checklist
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
