"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { claims, type ReadinessResult } from "@/lib/api";
import { MistralNavbar } from "@/components/MistralNavbar";
import {
  PixelArrowRight,
  PixelArrowLeft,
  PixelCheck,
  PixelAlert,
} from "@/components/PixelIcons";
import { useLanguage } from "@/context/LanguageContext";

export default function ClaimReadinessPage() {
  const params = useParams();
  const claimId = (params?.id as string) || "CLM-20491";

  const { t, lang } = useLanguage();
  const [result, setResult] = useState<ReadinessResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function fetchReadiness() {
    setError(null);
    try {
      const data = await claims.getReadiness(claimId);
      setResult(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load claim readiness");
    }
  }

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const data = await claims.getReadiness(claimId);
        if (!cancelled) setResult(data);
      } catch (err: unknown) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load claim readiness");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [claimId]);

  async function handleRefresh() {
    setRefreshing(true);
    await fetchReadiness();
    setRefreshing(false);
  }

  if (loading) {
    return (
      <div style={{ minHeight: "100vh", backgroundColor: "var(--surface-brand-primary)" }}>
        <MistralNavbar claimId={claimId} />
        <div className="mistral-main max-w-mistral border-grid-x" style={{ padding: "3rem 2rem" }}>
          <div style={{ height: "40px", width: "240px", backgroundColor: "var(--surface-brand-secondary)", marginBottom: "1.5rem" }} />
          <div style={{ height: "140px", width: "100%", backgroundColor: "var(--surface-brand-secondary)" }} />
        </div>
      </div>
    );
  }

  const docTranslations: Record<string, { label: string; gap?: string }> = {
    "discharge_summary": {
      label: "डिस्चार्ज सारांश",
      gap: "अस्पताल द्वारा जारी मूल डिस्चार्ज सारांश अनिवार्य है।",
    },
    "hospital_bill": {
      label: "अंतिम अस्पताल बिल",
      gap: "विस्तृत मद-वार अस्पताल बिल संलग्न किया जाना आवश्यक है।",
    },
    "payment_receipts": {
      label: "भुगतान रसीदें",
      gap: "अस्पताल द्वारा जारी हस्ताक्षरित भुगतान रसीद अनिवार्य है।",
    },
    "prescriptions": {
      label: "पर्चे एवं फार्मेसी बिल",
      gap: "चिकित्सक के पर्चे और संगत दवा बिल आवश्यक हैं।",
    },
    "diagnostic_reports": {
      label: "जाँच एवं लैब रिपोर्ट्स",
      gap: "इलाज का समर्थन करने वाली लैब व रेडियोलॉजी रिपोर्ट्स आवश्यक हैं।",
    },
    "indoor_case_papers": {
      label: "इंडोर केस पेपर्स (ICP) / ओटी नोट्स",
      gap: "बीमाकर्ता ने ओटी नोट्स और दैनिक डॉक्टर नोट्स की मांग की है। अस्पताल के मेडिकल रिकॉर्ड विभाग (MRD) से प्राप्त करें।",
    },
  };

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
                    href="/dashboard"
                    style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem", color: "var(--text-secondary)", fontSize: "0.8rem", fontWeight: 600 }}
                  >
                    <PixelArrowLeft size={14} /> {lang === "hi" ? "डैशबोर्ड पर वापस जाएं" : "Back to Dashboard"}
                  </Link>
                  <span style={{ color: "var(--border-secondary)" }}>/</span>
                  <span className="text-eyebrow">{lang === "hi" ? "क्लेम" : "Claim"} {claimId}</span>
                  <span className="mistral-badge badge-demo">Star Health</span>
                </div>

                <h1 className="text-h1" style={{ marginBottom: "0.5rem" }}>
                  {t("readiness.title", "Claim Readiness Verification")}
                </h1>
                <p style={{ color: "var(--text-secondary)", fontSize: "0.95rem" }}>
                  {t("readiness.subtitle", "Deterministic document audit & regulatory requirement check")}
                </p>
              </div>

              {/* Re-check Button */}
              <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                <button
                  onClick={handleRefresh}
                  disabled={refreshing}
                  className="btn-mistral-outline"
                  id="readiness-refresh-btn"
                >
                  {refreshing ? t("readiness.refreshing", "Auditing...") : t("readiness.refresh", "Re-Audit")}
                </button>
              </div>
            </div>
          </section>

          {error && (
            <div style={{ padding: "1rem 2rem", backgroundColor: "var(--status-danger-bg)", color: "var(--status-danger-text)", fontSize: "0.875rem" }}>
              {error}
            </div>
          )}

          {/* Readiness Score Metric Strip */}
          {result && (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", borderBottom: "1px solid var(--border-primary)" }} className="divide-grid-x">
              <div className="mistral-cell">
                <p className="text-eyebrow" style={{ marginBottom: "0.5rem" }}>{t("readiness.scoreLabel", "Readiness Score")}</p>
                <div style={{ display: "flex", alignItems: "baseline", gap: "0.75rem" }}>
                  <span className="font-mistral" style={{ fontSize: "2.5rem", fontWeight: 700, color: "var(--mistral-flame)" }}>
                    {result.score}%
                  </span>
                  <span className={`mistral-badge ${result.is_ready ? "badge-ready" : "badge-warning"}`}>
                    {result.is_ready 
                      ? (lang === "hi" ? "जमा करने हेतु तैयार" : "Ready to Submit")
                      : (lang === "hi" ? "1 महत्वपूर्ण कमी" : "1 Critical Gap")}
                  </span>
                </div>
                <div className="mistral-progress-track" style={{ marginTop: "0.75rem" }}>
                  <div className="mistral-progress-fill" style={{ width: `${result.score}%` }} />
                </div>
              </div>

              <div className="mistral-cell">
                <p className="text-eyebrow" style={{ marginBottom: "0.5rem" }}>
                  {lang === "hi" ? "दस्तावेज़ आवश्यकताएं" : "Document Requirements"}
                </p>
                <div style={{ display: "flex", alignItems: "baseline", gap: "0.75rem" }}>
                  <span className="font-mistral" style={{ fontSize: "2.5rem", fontWeight: 700, color: "var(--text-primary)" }}>
                    5 / 6
                  </span>
                  <span className="text-eyebrow" style={{ color: "var(--text-secondary)" }}>
                    {lang === "hi" ? "स्वीकार्य सत्यापित" : "Verified Admissible"}
                  </span>
                </div>
                <p style={{ fontSize: "0.75rem", color: "var(--text-tertiary)", marginTop: "0.5rem" }}>
                  {lang === "hi" ? "टीपीए द्वारा इंडोर केस पेपर्स (ICP) की मांग" : "Indoor Case Papers (ICPs) requested by TPA"}
                </p>
              </div>

              <div className="mistral-cell">
                <p className="text-eyebrow" style={{ marginBottom: "0.5rem" }}>
                  {lang === "hi" ? "अगला सुधारात्मक कदम" : "Next Remediation Step"}
                </p>
                <p style={{ fontSize: "0.9rem", fontWeight: 600, color: "var(--text-primary)", marginBottom: "0.25rem" }}>
                  {lang === "hi" ? "अस्वीकृति नोटिस समझें" : "Decode Rejection Notice"}
                </p>
                <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>
                  {lang === "hi" 
                    ? "78 महीनों की निरंतर कवरेज के बावजूद बीमाकर्ता ने त्रुटिवश क्लॉज 4.2 लागू किया।"
                    : "Insurer invoked Clause 4.2 in error despite 78 months continuous coverage."}
                </p>
              </div>
            </div>
          )}

          {/* Requirements Checklist Header */}
          <div className="mistral-cell-header">
            <span className="text-eyebrow">
              {lang === "hi" ? "वस्तुनिष्ठ चेकलिस्ट · 6 स्वीकार्यता मानक" : "Deterministic Checklist · 6 Admissibility Gates"}
            </span>
            <span className="text-eyebrow" style={{ color: "var(--text-tertiary)" }}>
              {lang === "hi" ? "पायथन नियम इंजन" : "Python Rules Engine"}
            </span>
          </div>

          {/* Checklist Items */}
          {result && (
            <div className="divide-grid-y">
              {result.requirements.map((req) => {
                const label = (lang === "hi" && docTranslations[req.requirement_type]?.label)
                  ? docTranslations[req.requirement_type].label
                  : req.label;

                const gap = (lang === "hi" && docTranslations[req.requirement_type]?.gap)
                  ? docTranslations[req.requirement_type].gap
                  : req.gap_reason;

                return (
                  <div
                    key={req.requirement_type}
                    className="mistral-cell"
                    style={{
                      display: "flex",
                      alignItems: "flex-start",
                      justifyContent: "space-between",
                      gap: "1.5rem",
                      backgroundColor: req.is_satisfied ? "var(--surface-brand-primary)" : "var(--surface-brand-secondary)",
                    }}
                    id={`req-${req.requirement_type}`}
                  >
                    <div style={{ display: "flex", alignItems: "flex-start", gap: "1rem" }}>
                      <div
                        style={{
                          width: 32,
                          height: 32,
                          borderRadius: "3px",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          backgroundColor: req.is_satisfied ? "var(--status-ready-bg)" : "var(--status-warn-bg)",
                          color: req.is_satisfied ? "var(--status-ready-text)" : "var(--status-warn-text)",
                          flexShrink: 0,
                          border: `1px solid ${req.is_satisfied ? "var(--status-ready-border)" : "var(--status-warn-border)"}`,
                        }}
                      >
                        {req.is_satisfied ? <PixelCheck size={16} /> : <PixelAlert size={16} />}
                      </div>

                      <div>
                        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.25rem", flexWrap: "wrap" }}>
                          <span style={{ fontWeight: 600, fontSize: "0.95rem" }}>{label}</span>
                          {req.is_mandatory && (
                            <span className="mistral-badge" style={{ fontSize: "0.65rem", padding: "1px 5px" }}>
                              {lang === "hi" ? "अनिवार्य" : "MANDATORY"}
                            </span>
                          )}
                        </div>

                        {gap ? (
                          <p style={{ fontSize: "0.85rem", color: "var(--status-danger-text)", lineHeight: 1.5, marginTop: "0.25rem" }}>
                            ⚠ {gap}
                          </p>
                        ) : (
                          <p style={{ fontSize: "0.8rem", color: "var(--text-tertiary)" }}>
                            {lang === "hi" 
                              ? `दस्तावेज़ सत्यापित: ${req.satisfied_by_document_id} · सुरक्षित हैश दर्ज` 
                              : `Document verified: ${req.satisfied_by_document_id} · Tamper-evident hash logged`}
                          </p>
                        )}
                      </div>
                    </div>

                    <span
                      className={`mistral-badge ${req.is_satisfied ? "badge-ready" : "badge-warning"}`}
                      style={{ flexShrink: 0 }}
                    >
                      {req.is_satisfied 
                        ? (lang === "hi" ? "पूर्ण" : "SATISFIED") 
                        : (lang === "hi" ? "कार्रवाई आवश्यक" : "ACTION REQUIRED")}
                    </span>
                  </div>
                );
              })}
            </div>
          )}

          {/* Issues & Flags */}
          {result && result.flags.length > 0 && (
            <div className="border-t-grid" style={{ padding: "1.5rem 2rem", backgroundColor: "var(--surface-brand-secondary)" }}>
              <p className="text-eyebrow" style={{ color: "var(--mistral-flame)", marginBottom: "0.75rem" }}>
                {lang === "hi" ? "विनियामक चेतावनियां एवं टिप्पणियां" : "Regulatory Alerts & Observations"}
              </p>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                {result.flags.map((flag, idx) => (
                  <div key={idx} style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.875rem", color: "var(--text-primary)" }}>
                    <PixelAlert size={14} className="text-amber-500" />
                    <span>{flag}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Statutory Disclaimer Banner */}
          <div className="border-t-grid mistral-banner-notice">
            <PixelAlert size={16} />
            <p>{t("readiness.disclaimer", "Statutory Disclaimer: Readiness evaluation is based on standard IRDAI 2024 claims submission rules. Final adjudication remains solely with the insurer.")}</p>
          </div>

          {/* Action Footer */}
          <div className="border-t-grid" style={{ padding: "1.75rem 2rem", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem" }}>
            <Link href="/dashboard" className="btn-mistral-outline">
              <PixelArrowLeft size={16} /> {lang === "hi" ? "डैशबोर्ड" : "Dashboard"}
            </Link>

            <Link
              href={`/claims/${claimId}/rejection`}
              className="btn-mistral-cta"
              id="proceed-rejection-btn"
            >
              <span className="cta-arrow-left">
                <PixelArrowRight size={18} />
              </span>
              <span className="cta-label">{t("readiness.decodeCta", "Decode Rejection Notice")}</span>
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
