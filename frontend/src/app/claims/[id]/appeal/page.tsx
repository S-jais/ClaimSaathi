"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { claims, type AppealDraft } from "@/lib/api";
import { MistralNavbar } from "@/components/MistralNavbar";
import {
  PixelArrowRight,
  PixelArrowLeft,
  PixelCheck,
  PixelAlert,
} from "@/components/PixelIcons";
import { useLanguage } from "@/context/LanguageContext";

type SectionKey =
  | "claim_summary"
  | "rejection_reason"
  | "relevant_clause"
  | "factual_clarification"
  | "supporting_evidence_list"
  | "requested_action";

const SECTION_ORDER: { key: SectionKey; labelKey: string; prefix: string }[] = [
  { key: "claim_summary", labelKey: "appeal.sec1", prefix: "01" },
  { key: "rejection_reason", labelKey: "appeal.sec2", prefix: "02" },
  { key: "relevant_clause", labelKey: "appeal.sec3", prefix: "03" },
  { key: "factual_clarification", labelKey: "appeal.sec4", prefix: "04" },
  { key: "supporting_evidence_list", labelKey: "appeal.sec5", prefix: "05" },
  { key: "requested_action", labelKey: "appeal.sec6", prefix: "06" },
];

export default function AppealBuilderPage() {
  const params = useParams();
  const claimId = (params?.id as string) || "CLM-20491";

  const { t: translate, lang } = useLanguage();
  const [draft, setDraft] = useState<AppealDraft | null>(null);
  const [loading, setLoading] = useState(true);
  const [approving, setApproving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editedContent, setEditedContent] = useState<Record<string, string>>({});
  const [activeEdit, setActiveEdit] = useState<SectionKey | null>(null);
  const [previewMode, setPreviewMode] = useState(false);
  const [downloadSuccess, setDownloadSuccess] = useState(false);

  useEffect(() => {
    claims
      .getAppealDraft(claimId, "latest")
      .then((d) => {
        setDraft(d);
        if (d.content_json) {
          const initial: Record<string, string> = {};
          SECTION_ORDER.forEach((s) => {
            initial[s.key] = d.content_json![s.key]?.content || "";
          });
          setEditedContent(initial);
        }
      })
      .catch((err) => setError(err.message || "Failed to load appeal draft"))
      .finally(() => setLoading(false));
  }, [claimId]);

  async function handleApprove() {
    if (!draft) return;
    setApproving(true);
    try {
      const approved = await claims.approveDraft(claimId, draft.id);
      setDraft(approved);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to approve draft");
    } finally {
      setApproving(false);
    }
  }

  function handleDownload() {
    setDownloadSuccess(true);
    const element = document.createElement("a");
    const file = new Blob([
      `CLAIMSAATHI LEGAL APPEAL BRIEF\n` +
      `Claim Reference: ${claimId}\n` +
      `Date: ${new Date().toLocaleDateString(lang === "hi" ? "hi-IN" : "en-IN")}\n` +
      `Statutory Authority: IRDAI Master Circular 2024 (Chapter V, Section 5.3)\n\n` +
      SECTION_ORDER.map(s => `[${translate(s.labelKey, s.key).toUpperCase()}]\n${editedContent[s.key] || ""}\n\n`).join("")
    ], { type: "text/plain;charset=utf-8" });
    element.href = URL.createObjectURL(file);
    element.download = `Appeal_Brief_${claimId}.txt`;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  }

  const isApproved = draft?.status === "approved";

  if (loading) {
    return (
      <div style={{ minHeight: "100vh", backgroundColor: "var(--surface-brand-primary)" }}>
        <MistralNavbar claimId={claimId} />
        <div className="mistral-main max-w-mistral border-grid-x" style={{ padding: "3rem 2rem" }}>
          <div style={{ height: "40px", width: "280px", backgroundColor: "var(--surface-brand-secondary)", marginBottom: "1.5rem" }} />
          <div style={{ height: "200px", width: "100%", backgroundColor: "var(--surface-brand-secondary)" }} />
        </div>
      </div>
    );
  }

  const t = {
    backToRejection: translate("appeal.backToRejection", "Back to Rejection Decoder"),
    claim: translate("appeal.claim", "Claim"),
    approvedBadge: translate("appeal.approvedBadge", "APPROVED FOR SUBMISSION"),
    pendingBadge: translate("appeal.pendingBadge", "REVIEW PENDING"),
    title: translate("appeal.title", "Appeal Draft Builder"),
    subtitle: translate("appeal.subtitle", "Formal First-Level Grievance brief grounded in IRDAI Master Circular 2024 Chapter V (60-Month Moratorium)"),
    editMode: translate("appeal.editMode", "Edit Mode"),
    previewDoc: translate("appeal.previewMode", "Preview Document"),
    recordingApproval: translate("appeal.recordingApproval", "Recording Approval..."),
    approveForExport: translate("appeal.approveForExport", "Approve for Export"),
    downloadBtn: translate("appeal.downloadBtn", "Download Appeal Brief (.TXT/PDF)"),
    gatekeeperTitleApproved: translate("appeal.gatekeeperTitleApproved", "✓ Policyholder Approval Verified & Audited."),
    gatekeeperTitlePending: translate("appeal.gatekeeperTitlePending", "Gatekeeper Verification Protocol:"),
    gatekeeperBodyApproved: translate("appeal.gatekeeperBodyApproved", "Approved. Document unlocked for download and submission to your insurer."),
    gatekeeperBodyPending: translate("appeal.gatekeeperBodyPending", "You must review every clause below. Edit any fact if required. You retain sole authority over final submission to the insurer."),
    downloadSuccess: translate("appeal.downloadSuccess", "Appeal Brief downloaded successfully. You can attach this with your 2018-2026 renewal receipts and submit to Star Health Grievance Redressal Officer (GRO)."),
    sectionPrefix: translate("appeal.sectionPrefix", "SECTION"),
    editBtn: translate("appeal.editBtn", "Edit Section"),
    saveBtn: translate("appeal.saveBtn", "Save"),
    confirmEdits: translate("appeal.confirmEdits", "Confirm Edits"),
    statutoryTitle: translate("appeal.statutoryTitle", "IRDAI Statutory Notice:"),
    statutoryBody: translate("appeal.statutoryBody", "ClaimSaathi generates customer-side grievance briefs grounded in the IRDAI 2024 Master Circular. Policyholders must verify dates and submit directly to the Insurer Grievance Redressal Officer (GRO). If unaddressed within 30 days, file with the Insurance Ombudsman under Rule 17 of the Insurance Ombudsman Rules, 2017."),
    rejectionDecoderLink: translate("appeal.rejectionDecoderLink", "Rejection Decoder"),
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
                    href={`/claims/${claimId}/rejection`}
                    style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem", color: "var(--text-secondary)", fontSize: "0.8rem", fontWeight: 600 }}
                  >
                    <PixelArrowLeft size={14} /> {t.backToRejection}
                  </Link>
                  <span style={{ color: "var(--border-secondary)" }}>/</span>
                  <span className="text-eyebrow">{t.claim} {claimId}</span>
                  <span className={`mistral-badge ${isApproved ? "badge-ready" : "badge-warning"}`}>
                    {isApproved ? t.approvedBadge : t.pendingBadge}
                  </span>
                </div>

                <h1 className="text-h1" style={{ marginBottom: "0.5rem" }}>{t.title}</h1>
                <p style={{ color: "var(--text-secondary)", fontSize: "0.95rem" }}>
                  {t.subtitle}
                </p>
              </div>

              {/* Controls */}
              <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                <button
                  type="button"
                  onClick={() => setPreviewMode(!previewMode)}
                  className="btn-mistral-outline"
                >
                  {previewMode ? t.editMode : t.previewDoc}
                </button>

                {!isApproved ? (
                  <button
                    type="button"
                    onClick={handleApprove}
                    disabled={approving}
                    className="btn-mistral-solid"
                    id="approve-appeal-btn"
                  >
                    <PixelCheck size={16} /> {approving ? t.recordingApproval : t.approveForExport}
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={handleDownload}
                    className="btn-mistral-solid"
                    style={{ backgroundColor: "var(--mistral-emerald)", borderColor: "var(--mistral-emerald)" }}
                    id="download-appeal-btn"
                  >
                    <PixelCheck size={16} /> {t.downloadBtn}
                  </button>
                )}
              </div>
            </div>
          </section>

          {/* Gatekeeper Banner */}
          <div className="border-b-grid mistral-banner-notice" style={{ backgroundColor: isApproved ? "var(--status-ready-bg)" : "var(--surface-brand-secondary)" }}>
            <PixelAlert size={16} />
            <div>
              <strong style={{ color: "var(--text-primary)" }}>
                {isApproved ? t.gatekeeperTitleApproved : t.gatekeeperTitlePending}
              </strong>{" "}
              {isApproved ? t.gatekeeperBodyApproved : t.gatekeeperBodyPending}
            </div>
          </div>

          {error && (
            <div style={{ padding: "1rem 2rem", backgroundColor: "var(--status-danger-bg)", color: "var(--status-danger-text)", fontSize: "0.875rem" }}>
              {error}
            </div>
          )}

          {downloadSuccess && (
            <div style={{ padding: "1rem 2rem", backgroundColor: "var(--status-ready-bg)", borderBottom: "1px solid var(--status-ready-border)", color: "var(--status-ready-text)", fontSize: "0.875rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <PixelCheck size={16} /> {t.downloadSuccess}
            </div>
          )}

          {/* Six-Section Appeal Letter */}
          {draft?.content_json && (
            <div className="divide-grid-y">
              {SECTION_ORDER.map(({ key, labelKey, prefix }) => {
                const section = draft.content_json![key];
                const isEditing = activeEdit === key && !previewMode && !isApproved;
                const sectionTitle = translate(labelKey, section?.title || key);

                return (
                  <div key={key} className="mistral-cell" id={`section-${key}`}>
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.75rem" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                        <span className="text-eyebrow" style={{ color: "var(--mistral-flame)" }}>
                          {t.sectionPrefix} {prefix}
                        </span>
                        <span style={{ color: "var(--border-secondary)" }}>•</span>
                        <h4 className="text-h4" style={{ margin: 0 }}>
                          {sectionTitle}
                        </h4>
                      </div>

                      {!previewMode && !isApproved && (
                        <button
                          type="button"
                          onClick={() => setActiveEdit(isEditing ? null : key)}
                          className="btn-mistral-ghost"
                          style={{ fontSize: "0.75rem", padding: "0.25rem 0.6rem" }}
                        >
                          {isEditing ? t.saveBtn : t.editBtn}
                        </button>
                      )}
                    </div>

                    {isEditing ? (
                      <div>
                        <textarea
                          className="mistral-textarea"
                          rows={6}
                          value={editedContent[key] || ""}
                          onChange={(e) =>
                            setEditedContent((prev) => ({ ...prev, [key]: e.target.value }))
                          }
                          id={`edit-${key}`}
                        />
                        <button
                          type="button"
                          onClick={() => setActiveEdit(null)}
                          className="btn-mistral-outline"
                          style={{ marginTop: "0.5rem", fontSize: "0.8rem", padding: "0.35rem 0.75rem" }}
                        >
                          {t.confirmEdits}
                        </button>
                      </div>
                    ) : (
                      <p
                        style={{
                          whiteSpace: "pre-wrap",
                          lineHeight: 1.75,
                          color: "var(--text-primary)",
                          fontSize: "0.925rem",
                        }}
                      >
                        {editedContent[key] || section?.content || ""}
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* Statutory Disclaimer Banner */}
          <div className="border-t-grid mistral-banner-notice">
            <PixelAlert size={16} />
            <p>
              <strong>{t.statutoryTitle}</strong> {t.statutoryBody}
            </p>
          </div>

          {/* Footer Action Strip */}
          <div className="border-t-grid" style={{ padding: "1.75rem 2rem", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem" }}>
            <Link href={`/claims/${claimId}/rejection`} className="btn-mistral-outline">
              <PixelArrowLeft size={16} /> {t.rejectionDecoderLink}
            </Link>

            {!isApproved ? (
              <button
                type="button"
                onClick={handleApprove}
                disabled={approving}
                className="btn-mistral-cta"
                id="approve-appeal-footer-btn"
              >
                <span className="cta-arrow-left">
                  <PixelArrowRight size={18} />
                </span>
                <span className="cta-label">{t.approveForExport}</span>
                <span className="cta-arrow-right">
                  <PixelArrowRight size={18} />
                </span>
              </button>
            ) : (
              <button
                type="button"
                onClick={handleDownload}
                className="btn-mistral-solid"
                style={{ backgroundColor: "var(--mistral-emerald)", borderColor: "var(--mistral-emerald)" }}
              >
                <PixelCheck size={16} /> {t.downloadBtn}
              </button>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
