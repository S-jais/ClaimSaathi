"use client";

import React, { useState } from "react";
import { type BillAuditReport, type AuditedLineItem, claims } from "@/lib/api";
import { PixelAlert, PixelCheck, PixelArrowRight } from "@/components/PixelIcons";
import { useLanguage } from "@/context/LanguageContext";

interface BillAuditCardProps {
  claimId: string;
  auditReport: BillAuditReport;
  onAuditUpdated?: (newReport: BillAuditReport) => void;
  onRequestUpload?: () => void;
}

export function BillAuditCard({
  claimId,
  auditReport,
  onAuditUpdated,
  onRequestUpload,
}: BillAuditCardProps) {
  const { t, lang } = useLanguage();
  const [items, setItems] = useState<AuditedLineItem[]>(auditReport.items || []);
  const [editingItemId, setEditingItemId] = useState<string | null>(null);
  const [editAmount, setEditAmount] = useState<string>("");
  const [filterClass, setFilterClass] = useState<string>("ALL");
  const [recalculating, setRecalculating] = useState(false);
  const [selectedExplItem, setSelectedExplItem] = useState<AuditedLineItem | null>(null);

  React.useEffect(() => {
    setItems(auditReport.items || []);
  }, [auditReport]);

  const formatRupees = (paise: number) => {
    return `₹${(paise / 100).toLocaleString(lang === "hi" ? "hi-IN" : "en-IN", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
  };

  const handleStartEdit = (item: AuditedLineItem) => {
    setEditingItemId(item.item_id);
    setEditAmount((item.amount_paise / 100).toString());
  };

  const handleSaveEdit = async (itemId: string) => {
    const parsedAmt = parseFloat(editAmount);
    if (isNaN(parsedAmt) || parsedAmt < 0) return;

    const newAmountPaise = Math.round(parsedAmt * 100);
    const updatedItems = items.map((it) =>
      it.item_id === itemId ? { ...it, amount_paise: newAmountPaise } : it
    );
    setItems(updatedItems);
    setEditingItemId(null);

    // Trigger dynamic re-audit
    setRecalculating(true);
    try {
      const resp = await claims.postBillAudit(claimId, {
        items: updatedItems.map((it) => ({
          description: it.description,
          amount_paise: it.amount_paise,
          category: it.category,
        })),
      });
      if (onAuditUpdated) onAuditUpdated(resp);
    } catch {
      // offline fallback
    } finally {
      setRecalculating(false);
    }
  };

  const filteredItems = items.filter((it) => {
    if (filterClass === "ALL") return true;
    return it.classification === filterClass;
  });

  return (
    <div className="border-t-grid" style={{ backgroundColor: "var(--surface-brand-primary)" }}>
      {/* Section Header */}
      <div
        className="border-b-grid"
        style={{
          padding: "1.5rem 2rem",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "1rem",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.25rem" }}>
            <span className="text-eyebrow" style={{ color: "var(--mistral-flame)" }}>
              IRDAI Compliance Engine
            </span>
            <span className="mistral-badge badge-ready">Catalog v{auditReport.rules_version}</span>
          </div>
          <h2 style={{ fontSize: "1.35rem", fontWeight: 700 }}>
            {t("billAudit.title", "Hospital Bill Audit & Indicative Payable Waterfall")}
          </h2>
        </div>

        <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
          {onRequestUpload && (
            <button onClick={onRequestUpload} className="btn-mistral-solid" style={{ fontSize: "0.85rem", padding: "0.4rem 0.85rem" }}>
              {t("readiness.uploadBtn", "+ Upload New Bill")}
            </button>
          )}
        </div>
      </div>

      {/* Indicative Payable Banner (MANDATORY LABEL & STRICT NO EXPECTED SETTLEMENT) */}
      <div
        style={{
          padding: "1.75rem 2rem",
          backgroundColor: "var(--surface-brand-secondary)",
          borderBottom: "1px solid var(--border-primary)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "1.5rem",
        }}
      >
        <div>
          <p className="text-eyebrow" style={{ color: "var(--text-secondary)", marginBottom: "0.4rem" }}>
            {auditReport.estimate_label}
          </p>
          <div style={{ display: "flex", alignItems: "baseline", gap: "1rem" }}>
            <span
              className="font-mistral"
              style={{
                fontSize: "2.75rem",
                fontWeight: 800,
                color: "var(--status-ready-text)",
                letterSpacing: "-0.02em",
              }}
            >
              {formatRupees(auditReport.indicative_payable_paise)}
            </span>
            <span className="text-eyebrow" style={{ color: "var(--text-tertiary)" }}>
              of {formatRupees(auditReport.gross_billed_paise)} billed
            </span>
          </div>
        </div>

        <div style={{ display: "flex", gap: "1rem" }}>
          <div
            style={{
              padding: "0.75rem 1rem",
              backgroundColor: "var(--surface-brand-primary)",
              border: "1px solid var(--border-primary)",
              borderRadius: "4px",
              textAlign: "center",
            }}
          >
            <p className="text-eyebrow" style={{ color: "var(--status-danger-text)" }}>{t("billAudit.nonPayableAmount", "Non-Payable")}</p>
            <p style={{ fontWeight: 700, fontSize: "1.1rem" }}>
              {formatRupees(auditReport.commonly_non_payable_paise)}
            </p>
          </div>

          <div
            style={{
              padding: "0.75rem 1rem",
              backgroundColor: "var(--surface-brand-primary)",
              border: "1px solid var(--border-primary)",
              borderRadius: "4px",
              textAlign: "center",
            }}
          >
            <p className="text-eyebrow" style={{ color: "var(--mistral-flame)" }}>{t("billAudit.statusQuestioned", "Needs Review")}</p>
            <p style={{ fontWeight: 700, fontSize: "1.1rem" }}>
              {formatRupees(auditReport.needs_review_paise)}
            </p>
          </div>
        </div>
      </div>

      {/* Waterfall Breakdown Strip */}
      <div className="border-b-grid" style={{ padding: "1.5rem 2rem" }}>
        <p className="text-eyebrow" style={{ marginBottom: "1rem" }}>
          Admissibility Waterfall (Integer-Paise Precision)
        </p>
        <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
          {auditReport.waterfall.map((step, idx) => {
            const isNegative = step.step_key.includes("deduction") || step.step_key.includes("adjustment") || step.step_key.includes("capping");
            const isTotal = step.step_key === "indicative_payable_estimate";

            return (
              <div
                key={idx}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "0.6rem 0.85rem",
                  borderRadius: "4px",
                  backgroundColor: isTotal ? "var(--surface-brand-secondary)" : "transparent",
                  border: isTotal ? "1px solid var(--border-primary)" : "none",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                  <span
                    style={{
                      fontSize: "0.85rem",
                      fontWeight: isTotal ? 700 : 500,
                      color: isTotal ? "var(--text-primary)" : "var(--text-secondary)",
                    }}
                  >
                    {step.label}
                  </span>
                  {step.status !== "APPLIED" && (
                    <span className="mistral-badge" style={{ fontSize: "0.65rem" }}>
                      {step.status}
                    </span>
                  )}
                  {step.notes && (
                    <span style={{ fontSize: "0.75rem", color: "var(--text-tertiary)" }}>
                      ({step.notes})
                    </span>
                  )}
                </div>

                <span
                  style={{
                    fontFamily: "var(--font-mono, monospace)",
                    fontWeight: isTotal ? 700 : 600,
                    fontSize: isTotal ? "1.1rem" : "0.95rem",
                    color: isTotal
                      ? "var(--status-ready-text)"
                      : isNegative && step.amount_paise > 0
                      ? "var(--status-danger-text)"
                      : "var(--text-primary)",
                  }}
                >
                  {isNegative && step.amount_paise > 0 ? "- " : ""}
                  {formatRupees(step.amount_paise)}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Line Items Categorization Table */}
      <div style={{ padding: "1.5rem 2rem" }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "0.75rem",
            marginBottom: "1rem",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <span className="text-eyebrow">Line Items Breakdown</span>
            <span style={{ fontSize: "0.8rem", color: "var(--text-tertiary)" }}>
              ({items.length} items extracted)
            </span>
          </div>

          {/* Filter Pills */}
          <div style={{ display: "flex", gap: "0.4rem" }}>
            {[
              { id: "ALL", label: `All (${items.length})` },
              { id: "PAYABLE_MEDICAL", label: `Payable (${auditReport.payable_medical_count})` },
              { id: "COMMONLY_NON_PAYABLE", label: `Non-Payable (${auditReport.non_payable_count})` },
              { id: "NEEDS_REVIEW", label: `Needs Review (${auditReport.needs_review_count})` },
            ].map((f) => (
              <button
                key={f.id}
                onClick={() => setFilterClass(f.id)}
                className={filterClass === f.id ? "btn-mistral-solid" : "btn-mistral-outline"}
                style={{ fontSize: "0.75rem", padding: "0.25rem 0.6rem" }}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        {/* Table */}
        <div
          style={{
            border: "1px solid var(--border-primary)",
            borderRadius: "4px",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "2fr 1.2fr 1fr 1fr 1fr",
              padding: "0.6rem 1rem",
              backgroundColor: "var(--surface-brand-secondary)",
              borderBottom: "1px solid var(--border-primary)",
              fontSize: "0.75rem",
              fontWeight: 600,
              color: "var(--text-tertiary)",
              textTransform: "uppercase",
            }}
          >
            <span>Description</span>
            <span>Category</span>
            <span>Classification</span>
            <span style={{ textAlign: "right" }}>Amount</span>
            <span style={{ textAlign: "center" }}>Action / Info</span>
          </div>

          <div className="divide-grid-y">
            {filteredItems.map((item) => {
              const isEditing = editingItemId === item.item_id;

              return (
                <div
                  key={item.item_id}
                  style={{
                    display: "grid",
                    gridTemplateColumns: "2fr 1.2fr 1fr 1fr 1fr",
                    padding: "0.75rem 1rem",
                    alignItems: "center",
                    fontSize: "0.85rem",
                    backgroundColor: "var(--surface-brand-primary)",
                  }}
                >
                  <div style={{ fontWeight: 500, color: "var(--text-primary)" }}>
                    {item.description}
                  </div>

                  <div style={{ color: "var(--text-secondary)", fontSize: "0.8rem" }}>
                    {item.category || "Unspecified"}
                  </div>

                  <div>
                    {item.classification === "PAYABLE_MEDICAL" && (
                      <span className="mistral-badge badge-ready" style={{ fontSize: "0.7rem" }}>
                        Payable
                      </span>
                    )}
                    {item.classification === "COMMONLY_NON_PAYABLE" && (
                      <span className="mistral-badge badge-danger" style={{ fontSize: "0.7rem" }}>
                        Non-Payable
                      </span>
                    )}
                    {item.classification === "NEEDS_REVIEW" && (
                      <span className="mistral-badge badge-warning" style={{ fontSize: "0.7rem" }}>
                        Review
                      </span>
                    )}
                  </div>

                  <div style={{ textAlign: "right", fontFamily: "var(--font-mono, monospace)" }}>
                    {isEditing ? (
                      <input
                        type="number"
                        step="0.01"
                        value={editAmount}
                        onChange={(e) => setEditAmount(e.target.value)}
                        style={{
                          width: "80px",
                          padding: "0.2rem 0.4rem",
                          fontSize: "0.85rem",
                          border: "1px solid var(--mistral-flame)",
                          borderRadius: "3px",
                          backgroundColor: "var(--surface-brand-secondary)",
                          color: "var(--text-primary)",
                          textAlign: "right",
                        }}
                      />
                    ) : (
                      formatRupees(item.amount_paise)
                    )}
                  </div>

                  <div style={{ textAlign: "center", display: "flex", justifyContent: "center", gap: "0.4rem" }}>
                    {isEditing ? (
                      <button
                        onClick={() => handleSaveEdit(item.item_id)}
                        disabled={recalculating}
                        className="btn-mistral-solid"
                        style={{ fontSize: "0.7rem", padding: "0.2rem 0.5rem" }}
                      >
                        Save
                      </button>
                    ) : (
                      <>
                        <button
                          onClick={() => handleStartEdit(item)}
                          className="btn-mistral-outline"
                          style={{ fontSize: "0.7rem", padding: "0.2rem 0.4rem" }}
                          title="Edit amount"
                        >
                          Edit
                        </button>
                        {item.explanation && (
                          <button
                            onClick={() => setSelectedExplItem(item)}
                            className="btn-mistral-outline"
                            style={{ fontSize: "0.7rem", padding: "0.2rem 0.4rem", color: "var(--mistral-flame)" }}
                            title="View IRDAI rule explanation"
                          >
                            Why?
                          </button>
                        )}
                      </>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Modal / Popover for IRDAI rule explanation */}
      {selectedExplItem && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            backgroundColor: "rgba(0,0,0,0.6)",
            backdropFilter: "blur(3px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 10000,
            padding: "1rem",
          }}
          onClick={() => setSelectedExplItem(null)}
        >
          <div
            className="mistral-card border-grid-x"
            style={{
              maxWidth: "500px",
              width: "100%",
              backgroundColor: "var(--surface-brand-primary)",
              borderRadius: "6px",
              overflow: "hidden",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div
              className="border-b-grid"
              style={{
                padding: "1rem 1.25rem",
                backgroundColor: "var(--surface-brand-secondary)",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <div>
                <span className="text-eyebrow" style={{ color: "var(--mistral-flame)" }}>
                  {selectedExplItem.rule_id || "IRDAI Deduction Code"}
                </span>
                <h4 style={{ margin: "0.2rem 0 0 0", fontSize: "1.05rem" }}>
                  {selectedExplItem.description}
                </h4>
              </div>
              <button
                onClick={() => setSelectedExplItem(null)}
                style={{ background: "none", border: "none", fontSize: "1.2rem", cursor: "pointer", color: "var(--text-secondary)" }}
              >
                ✕
              </button>
            </div>

            <div style={{ padding: "1.25rem" }}>
              {selectedExplItem.guideline_reference && (
                <div style={{ marginBottom: "0.75rem" }}>
                  <p className="text-eyebrow" style={{ color: "var(--text-tertiary)" }}>Guideline Authority</p>
                  <p style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--text-primary)" }}>
                    {selectedExplItem.guideline_reference}
                  </p>
                </div>
              )}

              <div style={{ marginBottom: "0.75rem" }}>
                <p className="text-eyebrow" style={{ color: "var(--text-tertiary)" }}>IRDAI Admissibility Rule</p>
                <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>
                  {selectedExplItem.explanation}
                </p>
              </div>

              {selectedExplItem.patient_remedy && (
                <div
                  style={{
                    padding: "0.75rem",
                    backgroundColor: "var(--surface-brand-secondary)",
                    borderRadius: "4px",
                    borderLeft: "3px solid var(--mistral-flame)",
                  }}
                >
                  <p className="text-eyebrow" style={{ color: "var(--mistral-flame)", marginBottom: "0.25rem" }}>
                    Patient Remedy / Recommended Action
                  </p>
                  <p style={{ fontSize: "0.82rem", color: "var(--text-primary)", lineHeight: 1.4 }}>
                    {selectedExplItem.patient_remedy}
                  </p>
                </div>
              )}
            </div>

            <div
              className="border-t-grid"
              style={{ padding: "0.75rem 1.25rem", textAlign: "right", backgroundColor: "var(--surface-brand-secondary)" }}
            >
              <button onClick={() => setSelectedExplItem(null)} className="btn-mistral-solid" style={{ fontSize: "0.8rem", padding: "0.35rem 0.8rem" }}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
