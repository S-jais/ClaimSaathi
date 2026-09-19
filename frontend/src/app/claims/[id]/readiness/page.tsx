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

export default function ClaimReadinessPage() {
  const params = useParams();
  const claimId = (params?.id as string) || "CLM-20491";

  const [result, setResult] = useState<ReadinessResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lang, setLang] = useState<"en" | "hi">("en");

  const t =
    lang === "hi"
      ? {
        title: "दावा तैयारी सत्यापन",
        subtitle: "दस्तावेज़ ऑडिट एवं विनियामक आवश्यकता परीक्षण",
        satisfied: "सत्यापित",
        missing: "कार्रवाई आवश्यक",
        score: "तैयारी स्कोर",
        refresh: "पुनः जांचें",
        decodeCta: "अस्वीकृति पत्र समझें",
        disclaimer:
          "सांविधिक अस्वीकरण: तैयारी मूल्यांकन IRDAI 2024 दावा प्रस्तुति नियमों पर आधारित है। अंतिम निर्णय केवल बीमाकर्ता का होगा।",
      }
      : {
        title: "Claim Readiness Verification",
        subtitle: "Deterministic document audit & regulatory requirement check",
        satisfied: "SATISFIED",
        missing: "ACTION REQUIRED",
        score: "Readiness Score",
        refresh: "Re-Audit",
        decodeCta: "Decode Rejection Notice",
        disclaimer:
          "Statutory Disclaimer: Readiness evaluation is based on standard IRDAI 2024 claims submission rules. Final adjudication remains solely with the insurer.",
      };

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
                    <PixelArrowLeft size={14} /> Back to Dashboard
                  </Link>
                  <span style={{ color: "var(--border-secondary)" }}>/</span>
                  <span className="text-eyebrow">Claim {claimId}</span>
                  <span className="mistral-badge badge-demo">Star Health</span>
                </div>

                <h1 className="text-h1" style={{ marginBottom: "0.5rem" }}>{t.title}</h1>
                <p style={{ color: "var(--text-secondary)", fontSize: "0.95rem" }}>{t.subtitle}</p>
              </div>

              {/* Language Switcher & Re-check Button */}
              <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
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

                <button
                  onClick={handleRefresh}
                  disabled={refreshing}
                  className="btn-mistral-outline"
                  id="readiness-refresh-btn"
                >
                  {refreshing ? "Auditing..." : t.refresh}
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
                <p className="text-eyebrow" style={{ marginBottom: "0.5rem" }}>{t.score}</p>
                <div style={{ display: "flex", alignItems: "baseline", gap: "0.75rem" }}>
                  <span className="font-mistral" style={{ fontSize: "2.5rem", fontWeight: 700, color: "var(--mistral-flame)" }}>
                    {result.score}%
                  </span>
                  <span className={`mistral-badge ${result.is_ready ? "badge-ready" : "badge-warning"}`}>
                    {result.is_ready ? "Ready to Submit" : "1 Critical Gap"}
                  </span>
                </div>
                <div className="mistral-progress-track" style={{ marginTop: "0.75rem" }}>
                  <div className="mistral-progress-fill" style={{ width: `${result.score}%` }} />
                </div>
              </div>

              <div className="mistral-cell">
                <p className="text-eyebrow" style={{ marginBottom: "0.5rem" }}>Document Requirements</p>
                <div style={{ display: "flex", alignItems: "baseline", gap: "0.75rem" }}>
                  <span className="font-mistral" style={{ fontSize: "2.5rem", fontWeight: 700, color: "var(--text-primary)" }}>
                    5 / 6
                  </span>
                  <span className="text-eyebrow" style={{ color: "var(--text-secondary)" }}>
                    Verified Admissible
                  </span>
                </div>
                <p style={{ fontSize: "0.75rem", color: "var(--text-tertiary)", marginTop: "0.5rem" }}>
                  Indoor Case Papers (ICPs) requested by TPA
                </p>
              </div>

              <div className="mistral-cell">
                <p className="text-eyebrow" style={{ marginBottom: "0.5rem" }}>Next Remediation Step</p>
                <p style={{ fontSize: "0.9rem", fontWeight: 600, color: "var(--text-primary)", marginBottom: "0.25rem" }}>
                  Decode Rejection Notice
                </p>
                <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>
                  Insurer invoked Clause 4.2 in error despite 78 months continuous coverage.
                </p>
              </div>
            </div>
          )}

          {/* Requirements Checklist Header */}
          <div className="mistral-cell-header">
            <span className="text-eyebrow">Deterministic Checklist · 6 Admissibility Gates</span>
            <span className="text-eyebrow" style={{ color: "var(--text-tertiary)" }}>Python Rules Engine</span>
          </div>

          {/* Checklist Items */}
          {result && (
            <div className="divide-grid-y">
              {result.requirements.map((req) => (
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
                        <span style={{ fontWeight: 600, fontSize: "0.95rem" }}>{req.label}</span>
                        {req.is_mandatory && (
                          <span className="mistral-badge" style={{ fontSize: "0.65rem", padding: "1px 5px" }}>
                            MANDATORY
                          </span>
                        )}
                      </div>

                      {req.gap_reason ? (
                        <p style={{ fontSize: "0.85rem", color: "var(--status-danger-text)", lineHeight: 1.5, marginTop: "0.25rem" }}>
                          ⚠ {req.gap_reason}
                        </p>
                      ) : (
                        <p style={{ fontSize: "0.8rem", color: "var(--text-tertiary)" }}>
                          Document verified: {req.satisfied_by_document_id} · Tamper-evident hash logged
                        </p>
                      )}
                    </div>
                  </div>

                  <span
                    className={`mistral-badge ${req.is_satisfied ? "badge-ready" : "badge-warning"}`}
                    style={{ flexShrink: 0 }}
                  >
                    {req.is_satisfied ? t.satisfied : t.missing}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Issues & Flags */}
          {result && result.flags.length > 0 && (
            <div className="border-t-grid" style={{ padding: "1.5rem 2rem", backgroundColor: "var(--surface-brand-secondary)" }}>
              <p className="text-eyebrow" style={{ color: "var(--mistral-flame)", marginBottom: "0.75rem" }}>
                Regulatory Alerts & Observations
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
            <p>{t.disclaimer}</p>
          </div>

          {/* Action Footer */}
          <div className="border-t-grid" style={{ padding: "1.75rem 2rem", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem" }}>
            <Link href="/dashboard" className="btn-mistral-outline">
              <PixelArrowLeft size={16} /> Dashboard
            </Link>

            <Link
              href={`/claims/${claimId}/rejection`}
              className="btn-mistral-cta"
              id="proceed-rejection-btn"
            >
              <span className="cta-arrow-left">
                <PixelArrowRight size={18} />
              </span>
              <span className="cta-label">{t.decodeCta}</span>
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
