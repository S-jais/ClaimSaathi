"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { claims, type Claim } from "@/lib/api";
import { MistralNavbar } from "@/components/MistralNavbar";
import {
  PixelArrowRight,
  PixelArrowLeft,
  PixelCheck,
  PixelAlert,
} from "@/components/PixelIcons";
import { useLanguage } from "@/context/LanguageContext";

export default function ClaimHubPage() {
  const { t, lang } = useLanguage();
  const params = useParams();
  const claimId = (params?.id as string) || "CLM-20491";
  const [claim, setClaim] = useState<Claim | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    claims
      .get(claimId)
      .then(setClaim)
      .catch(() => setClaim(null))
      .finally(() => setLoading(false));
  }, [claimId]);

  if (loading) {
    return (
      <div style={{ minHeight: "100vh", backgroundColor: "var(--surface-brand-primary)" }}>
        <MistralNavbar claimId={claimId} />
        <div className="mistral-main max-w-mistral border-grid-x" style={{ padding: "3rem 2rem" }}>
          <div style={{ height: "40px", width: "240px", backgroundColor: "var(--surface-brand-secondary)", marginBottom: "1.5rem" }} />
          <div style={{ height: "160px", width: "100%", backgroundColor: "var(--surface-brand-secondary)" }} />
        </div>
      </div>
    );
  }

  const currentClaim = claim || {
    id: claimId,
    claim_reference: claimId,
    claim_type: "reimbursement",
    status: "rejected",
    claim_amount: "184500",
    hospital_name: "Apollo Hospital, Bengaluru",
    admission_date: "2026-02-10",
    discharge_date: "2026-02-14",
    readiness_score: 85,
    is_demo: false,
    created_at: "2026-02-15T09:30:00Z",
    updated_at: "2026-02-28T14:15:00Z",
  };

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <MistralNavbar claimId={claimId} />

      <main className="mistral-main" style={{ flex: 1, display: "flex", flexDirection: "column" }}>
        <div className="max-w-mistral border-grid-x" style={{ flex: 1, display: "flex", flexDirection: "column" }}>
          {/* Top Header Stripe */}
          <div className="mistral-stripe" />

          {/* Header */}
          <section className="border-b-grid" style={{ padding: "2.5rem 2rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1.5rem" }}>
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.5rem" }}>
                  <Link
                    href="/dashboard"
                    style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem", color: "var(--text-secondary)", fontSize: "0.8rem", fontWeight: 600 }}
                  >
                    <PixelArrowLeft size={14} /> {t("claimHub.backToDashboard", "Back to Dashboard")}
                  </Link>
                  <span style={{ color: "var(--border-secondary)" }}>/</span>
                  <span className="text-eyebrow">{t("claimHub.commandCenter", "COMMAND CENTER")}</span>
                  <span className="mistral-badge badge-ready">{t("claimHub.activeRecord", "ACTIVE RECORD")}</span>
                </div>

                <h1 className="text-h1" style={{ marginBottom: "0.5rem" }}>
                  {t("claimHub.reference", "Claim Reference: {ref}").replace("{ref}", currentClaim.claim_reference)}
                </h1>
                <p style={{ color: "var(--text-secondary)", fontSize: "0.95rem" }}>
                  {currentClaim.hospital_name} · Total Knee Arthroplasty (Left) · {t("claimHub.incurred", "Incurred: ₹{amt}").replace("{amt}", Number(currentClaim.claim_amount || 0).toLocaleString(lang === "hi" ? "hi-IN" : "en-IN"))}
                </p>
              </div>

              <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
                <span className="mistral-badge badge-danger" style={{ fontSize: "0.85rem", padding: "0.4rem 0.8rem" }}>
                  <PixelAlert size={14} /> {t("claimHub.repudiatedBadge", "Repudiated by TPA")}
                </span>
                <span className="mistral-badge badge-ready" style={{ fontSize: "0.85rem", padding: "0.4rem 0.8rem" }}>
                  <PixelCheck size={14} /> {t("claimHub.shieldBadge", "78-Mo Moratorium Shield")}
                </span>
              </div>
            </div>
          </section>

          {/* 3 Core Workflow Modules */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", borderBottom: "1px solid var(--border-primary)" }} className="divide-grid-x">
            {/* 1. Readiness */}
            <div className="mistral-cell" style={{ display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
              <div>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.5rem" }}>
                  <span className="text-eyebrow" style={{ color: "var(--mistral-amber)" }}>{t("claimHub.stage01", "Stage 01")}</span>
                  <span className="mistral-badge badge-warning">Score: 85%</span>
                </div>
                <h3 className="text-h3" style={{ marginBottom: "0.5rem" }}>{t("claimHub.readinessAuditTitle", "Readiness Audit")}</h3>
                <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>
                  {t("claimHub.readinessAuditDesc", "Deterministic verification across 6 mandatory document requirements. 5 satisfied, 1 gap identified (Indoor Case Papers).")}
                </p>
              </div>
              <div style={{ marginTop: "1.5rem" }}>
                <Link
                  href={`/claims/${claimId}/readiness`}
                  className="btn-mistral-outline"
                  style={{ width: "100%" }}
                >
                  {t("claimHub.inspectChecklist", "Inspect Checklist")} <PixelArrowRight size={14} />
                </Link>
              </div>
            </div>

            {/* 2. Rejection Decoder */}
            <div className="mistral-cell" style={{ display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
              <div>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.5rem" }}>
                  <span className="text-eyebrow" style={{ color: "var(--mistral-flame)" }}>{t("claimHub.stage02", "Stage 02")}</span>
                  <span className="mistral-badge badge-ready">96% Confidence</span>
                </div>
                <h3 className="text-h3" style={{ marginBottom: "0.5rem" }}>{t("claimHub.rejectionDecoderTitle", "Rejection Decoder")}</h3>
                <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>
                  {t("claimHub.rejectionDecoderDesc", "Tripartite analysis decomposing the repudiation notice. Explains why Clause 4.2 invocation is invalid under IRDAI 2024 Chapter V.")}
                </p>
              </div>
              <div style={{ marginTop: "1.5rem" }}>
                <Link
                  href={`/claims/${claimId}/rejection`}
                  className="btn-mistral-solid"
                  style={{ width: "100%" }}
                >
                  {t("claimHub.decodeRepudiation", "Decode Repudiation")} <PixelArrowRight size={14} />
                </Link>
              </div>
            </div>

            {/* 3. Appeal Builder */}
            <div className="mistral-cell" style={{ display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
              <div>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.5rem" }}>
                  <span className="text-eyebrow" style={{ color: "var(--mistral-emerald)" }}>{t("claimHub.stage03", "Stage 03")}</span>
                  <span className="mistral-badge">Grievance Brief</span>
                </div>
                <h3 className="text-h3" style={{ marginBottom: "0.5rem" }}>{t("claimHub.appealDraftTitle", "Appeal Draft Builder")}</h3>
                <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>
                  {t("claimHub.appealDraftDesc", "Six-part structured First-Level Grievance brief with explicit user review & sign-off gatekeeper before PDF export.")}
                </p>
              </div>
              <div style={{ marginTop: "1.5rem" }}>
                <Link
                  href={`/claims/${claimId}/appeal`}
                  className="btn-mistral-outline"
                  style={{ width: "100%" }}
                >
                  {t("claimHub.reviewAppeal", "Review Appeal Brief")} <PixelArrowRight size={14} />
                </Link>
              </div>
            </div>
          </div>

          {/* Dossier Details Table */}
          <div className="mistral-cell-header">
            <span className="text-eyebrow">{t("claimHub.dossierHeader", "Claim Dossier & Grounding Evidence")}</span>
            <span className="text-eyebrow" style={{ color: "var(--text-tertiary)" }}>Apollo Bengaluru · Star Health</span>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))" }} className="divide-grid-x">
            <div className="mistral-cell">
              <span className="text-eyebrow" style={{ display: "block", marginBottom: "0.25rem" }}>{t("claimHub.policySchedule", "Policy Schedule")}</span>
              <p style={{ fontWeight: 600, color: "var(--text-primary)" }}>Star Health MediClassic Individual</p>
              <p style={{ fontSize: "0.825rem", color: "var(--text-secondary)" }}>Policy #SH-884920 · Sum Insured ₹5,00,000</p>
              <p style={{ fontSize: "0.75rem", color: "var(--mistral-emerald)", marginTop: "0.25rem", fontWeight: 600 }}>
                ✓ Inception: 12-Mar-2018 (78 Months Continuous)
              </p>
            </div>

            <div className="mistral-cell">
              <span className="text-eyebrow" style={{ display: "block", marginBottom: "0.25rem" }}>{t("claimHub.clinicalParticulars", "Clinical Particulars")}</span>
              <p style={{ fontWeight: 600, color: "var(--text-primary)" }}>Severe Osteoarthritis Grade IV</p>
              <p style={{ fontSize: "0.825rem", color: "var(--text-secondary)" }}>Procedure: Total Knee Arthroplasty (Left Knee)</p>
              <p style={{ fontSize: "0.75rem", color: "var(--text-tertiary)", marginTop: "0.25rem" }}>
                Treating Surgeon: Dr. S. Rao (Apollo Hospital)
              </p>
            </div>

            <div className="mistral-cell">
              <span className="text-eyebrow" style={{ display: "block", marginBottom: "0.25rem" }}>{t("claimHub.financialParticulars", "Financial Particulars")}</span>
              <p style={{ fontWeight: 600, color: "var(--text-primary)" }}>Admissible Claim: ₹1,84,500</p>
              <p style={{ fontSize: "0.825rem", color: "var(--text-secondary)" }}>Hospital Bill: ₹1,12,000 · Implant: ₹72,500</p>
              <p style={{ fontSize: "0.75rem", color: "var(--mistral-flame)", marginTop: "0.25rem", fontWeight: 600 }}>
                Repudiation reason: Clause 4.2 (Invalid after 60 mos)
              </p>
            </div>
          </div>

          {/* Statutory Notice Banner */}
          <div className="border-t-grid mistral-banner-notice">
            <PixelAlert size={16} />
            <p>
              <strong>{t("claimHub.statutoryNoticeTitle", "Regulatory Notice:")}</strong> {t("claimHub.statutoryNotice", "Under the IRDAI Master Circular 2024 (Chapter V, Section 5.3), health claims cannot be contested for pre-existing conditions after 60 continuous months of coverage. ClaimSaathi equips policyholders with structured legal grounding for first-level grievances.")}
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
