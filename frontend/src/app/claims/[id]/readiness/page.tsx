"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { claims, type ReadinessResult, type BillAuditReport } from "@/lib/api";
import { MistralNavbar } from "@/components/MistralNavbar";
import { DocumentUploadModal } from "@/components/DocumentUploadModal";
import { BillAuditCard } from "@/components/BillAuditCard";
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
  const [billAudit, setBillAudit] = useState<BillAuditReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Upload modal state
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [activeUploadDocType, setActiveUploadDocType] = useState<string>("hospital_bill");

  async function loadData() {
    setError(null);
    try {
      const [readinessData, auditData] = await Promise.all([
        claims.getReadiness(claimId),
        claims.getBillAudit(claimId),
      ]);
      setResult(readinessData);
      setBillAudit(auditData);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load claim readiness");
    }
  }

  useEffect(() => {
    let cancelled = false;
    async function init() {
      try {
        await loadData();
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    init();
    return () => {
      cancelled = true;
    };
  }, [claimId]);

  async function handleRefresh() {
    setRefreshing(true);
    await loadData();
    setRefreshing(false);
  }

  const openUploadFor = (docType: string) => {
    setActiveUploadDocType(docType);
    setUploadModalOpen(true);
  };

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
    discharge_summary: {
      label: "डिस्चार्ज सारांश",
      gap: "अस्पताल द्वारा जारी मूल डिस्चार्ज सारांश अनिवार्य है।",
    },
    hospital_bill: {
      label: "अंतिम अस्पताल बिल",
      gap: "विस्तृत मद-वार अस्पताल बिल संलग्न किया जाना आवश्यक है।",
    },
    claim_form: {
      label: "हस्ताक्षरित क्लेम फॉर्म",
      gap: "बीमित व्यक्ति एवं चिकित्सक द्वारा हस्ताक्षरित क्लेम फॉर्म आवश्यक है।",
    },
    policy: {
      label: "पॉलिसी दस्तावेज़ / हेल्थ कार्ड",
      gap: "सक्रिय पॉलिसी अनुसूची अथवा ई-हेल्थ कार्ड संलग्न करें।",
    },
    prescription: {
      label: "पर्चे एवं फार्मेसी बिल",
      gap: "चिकित्सक के पर्चे और संगत दवा बिल आवश्यक हैं।",
    },
    consultation_notes: {
      label: "परामर्श / ओपीडी नोट्स",
      gap: "अस्पताल में भर्ती से पूर्व के परामर्श नोट्स आवश्यक हैं।",
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
                  <span className="mistral-badge badge-ready">Audit & Readiness</span>
                </div>

                <h1 className="text-h1" style={{ marginBottom: "0.5rem" }}>
                  {t("readiness.title", "Claim Readiness & Bill Audit")}
                </h1>
                <p style={{ color: "var(--text-secondary)", fontSize: "0.95rem" }}>
                  {t("readiness.subtitle", "Automated IRDAI admissibility verification, cross-document checks & indicative bill audit")}
                </p>
              </div>

              {/* Action Buttons */}
              <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flexWrap: "wrap" }}>
                <button
                  onClick={() => openUploadFor("hospital_bill")}
                  className="btn-mistral-solid"
                  id="upload-doc-header-btn"
                  style={{ fontSize: "0.85rem", padding: "0.5rem 1rem" }}
                >
                  + Upload Document
                </button>

                <button
                  onClick={handleRefresh}
                  disabled={refreshing}
                  className="btn-mistral-outline"
                  id="readiness-refresh-btn"
                  style={{ fontSize: "0.85rem", padding: "0.5rem 1rem" }}
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
                      : (lang === "hi" ? `${result.missing_mandatory.length || 1} कमी पाई गई` : `${result.missing_mandatory.length || 1} Gate Unmet`)}
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
                    {result.requirements.filter((r) => r.is_satisfied).length} / {result.requirements.length}
                  </span>
                  <span className="text-eyebrow" style={{ color: "var(--text-secondary)" }}>
                    {lang === "hi" ? "स्वीकार्य सत्यापित" : "Verified Admissible"}
                  </span>
                </div>
                <p style={{ fontSize: "0.75rem", color: "var(--text-tertiary)", marginTop: "0.5rem" }}>
                  {result.missing_mandatory.length === 0
                    ? (lang === "hi" ? "सभी अनिवार्य दस्तावेज़ पूर्ण हैं" : "All mandatory files verified")
                    : `${result.missing_mandatory.length} mandatory item(s) pending`}
                </p>
              </div>

              <div className="mistral-cell">
                <p className="text-eyebrow" style={{ marginBottom: "0.5rem" }}>
                  {lang === "hi" ? "अगला सुधारात्मक कदम" : "Adjudication Route"}
                </p>
                <p style={{ fontSize: "0.9rem", fontWeight: 600, color: "var(--text-primary)", marginBottom: "0.25rem" }}>
                  {result.is_ready ? "Submit to TPA / Insurer" : "Fulfill Pending Checkpoints"}
                </p>
                <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>
                  {result.is_ready
                    ? "Your dossier is 100% compliant with standard IRDAI submission mandates."
                    : "Upload missing items below or re-audit after resolving discrepancy flags."}
                </p>
              </div>
            </div>
          )}

          {/* Cross-Document Consistency Verification Strip */}
          {result && result.cross_doc_checks && result.cross_doc_checks.length > 0 && (
            <div className="border-b-grid" style={{ padding: "1.5rem 2rem", backgroundColor: "var(--surface-brand-secondary)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.75rem" }}>
                <span className="text-eyebrow" style={{ color: "var(--text-primary)" }}>
                  Cross-Document Consistency Audit
                </span>
                <span className="mistral-badge badge-ready">Deterministic Verification</span>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "0.75rem" }}>
                {result.cross_doc_checks.map((check, idx) => (
                  <div
                    key={idx}
                    style={{
                      padding: "0.85rem 1rem",
                      backgroundColor: "var(--surface-brand-primary)",
                      border: `1px solid ${check.is_passed ? "var(--status-ready-border)" : "var(--status-danger-border)"}`,
                      borderRadius: "4px",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.3rem" }}>
                      {check.is_passed ? (
                        <PixelCheck size={14} className="text-emerald-500" />
                      ) : (
                        <PixelAlert size={14} className="text-amber-500" />
                      )}
                      <span style={{ fontSize: "0.85rem", fontWeight: 600, textTransform: "capitalize" }}>
                        {check.check_name.replace(/_/g, " ")}
                      </span>
                    </div>
                    <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)", lineHeight: 1.4 }}>
                      {check.message}
                    </p>
                    {check.remedy && (
                      <p style={{ fontSize: "0.75rem", color: "var(--mistral-flame)", marginTop: "0.35rem" }}>
                        Tip: {check.remedy}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Requirements Checklist Header */}
          <div className="mistral-cell-header">
            <span className="text-eyebrow">
              {lang === "hi" ? "वस्तुनिष्ठ चेकलिस्ट · स्वीकार्यता मानक" : "Mandatory Checklist · Admissibility Gates"}
            </span>
            <span className="text-eyebrow" style={{ color: "var(--text-tertiary)" }}>
              {lang === "hi" ? "पायथन नियम इंजन" : "Server-Side Verification Engine"}
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

                const itemStatus = req.status || (req.is_satisfied ? "VERIFIED" : "MISSING");

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
                          <span
                            className={`mistral-badge ${
                              itemStatus === "VERIFIED"
                                ? "badge-ready"
                                : itemStatus === "NEEDS_FIX"
                                ? "badge-danger"
                                : "badge-warning"
                            }`}
                            style={{ fontSize: "0.65rem" }}
                          >
                            {itemStatus}
                          </span>
                        </div>

                        {gap ? (
                          <p style={{ fontSize: "0.85rem", color: "var(--status-danger-text)", lineHeight: 1.5, marginTop: "0.25rem" }}>
                            ⚠ {gap}
                          </p>
                        ) : (
                          <p style={{ fontSize: "0.8rem", color: "var(--text-tertiary)" }}>
                            {req.filename
                              ? `Attached: ${req.filename} · Verified signature & stamp`
                              : `Document verified: ${req.satisfied_by_document_id || "OK"} · Tamper-evident hash logged`}
                          </p>
                        )}
                      </div>
                    </div>

                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexShrink: 0 }}>
                      <button
                        onClick={() => openUploadFor(req.requirement_type)}
                        className="btn-mistral-outline"
                        style={{ fontSize: "0.75rem", padding: "0.3rem 0.65rem" }}
                        id={`upload-btn-${req.requirement_type}`}
                      >
                        {req.is_satisfied ? "Replace" : "Upload"}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* IRDAI Hospital Bill Audit Card */}
          {billAudit && (
            <BillAuditCard
              claimId={claimId}
              auditReport={billAudit}
              onAuditUpdated={(updated) => setBillAudit(updated)}
              onRequestUpload={() => openUploadFor("hospital_bill")}
            />
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
            <p>{t("readiness.disclaimer", "Statutory Disclaimer: Readiness evaluation is based on standard IRDAI 2024 claims submission rules. All payable estimates are indicative and subject to your insurer's assessment.")}</p>
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

      {/* Upload Modal */}
      <DocumentUploadModal
        isOpen={uploadModalOpen}
        onClose={() => setUploadModalOpen(false)}
        claimId={claimId}
        defaultDocType={activeUploadDocType}
        onSuccess={() => {
          handleRefresh();
        }}
      />
    </div>
  );
}
