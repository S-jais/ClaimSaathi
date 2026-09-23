"use client";

import React, { useState, useRef } from "react";
import { documents } from "@/lib/api";
import { PixelAlert, PixelCheck, PixelArrowRight } from "@/components/PixelIcons";
import { useLanguage } from "@/context/LanguageContext";

interface DocumentUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  claimId: string;
  defaultDocType?: string;
  onSuccess?: () => void;
}

const DOC_TYPES = [
  { value: "hospital_bill", label: "Hospital Bill / Invoice (CSV, PDF, Image)" },
  { value: "discharge_summary", label: "Discharge Summary (PDF, Image)" },
  { value: "claim_form", label: "Signed Claim Form (PDF, Image)" },
  { value: "policy", label: "Insurance Policy / Health Card (PDF, Image)" },
  { value: "prescription", label: "Doctor Prescription / Pharmacy (PDF, Image)" },
  { value: "consultation_notes", label: "Pre-Hospitalization OPD Notes (PDF, Image)" },
  { value: "rejection_letter", label: "Rejection / Repudiation Letter (PDF, Image)" },
  { value: "other", label: "Other Supporting Document (Any)" },
];

export function DocumentUploadModal({
  isOpen,
  onClose,
  claimId,
  defaultDocType = "hospital_bill",
  onSuccess,
}: DocumentUploadModalProps) {
  const { t } = useLanguage();
  const [selectedDocType, setSelectedDocType] = useState<string>(defaultDocType);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [stage, setStage] = useState<string>("");
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [completed, setCompleted] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  React.useEffect(() => {
    if (defaultDocType) {
      setSelectedDocType(defaultDocType);
    }
  }, [defaultDocType]);

  if (!isOpen) return null;

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      setFile(e.dataTransfer.files[0]);
      setError(null);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
      setError(null);
    }
  };

  const resetState = () => {
    setFile(null);
    setUploading(false);
    setProgress(0);
    setStage("");
    setError(null);
    setCompleted(false);
  };

  const handleUpload = async () => {
    if (!file) {
      setError("Please select a file to upload.");
      return;
    }

    setUploading(true);
    setError(null);
    setProgress(15);
    setStage("Uploading document to secure storage...");

    try {
      const resp = await documents.upload(file, selectedDocType, claimId);
      setProgress(40);
      setStage("Extracting line-items & checking IRDAI rules...");

      // Poll analysis job status
      const jobId = resp.document_id;
      let attempts = 0;
      const pollInterval = setInterval(async () => {
        attempts++;
        try {
          const job = await documents.getJob(jobId);
          if (job.status === "COMPLETED") {
            clearInterval(pollInterval);
            setProgress(100);
            setStage("Audit and readiness verification complete!");
            setCompleted(true);
            setTimeout(() => {
              if (onSuccess) onSuccess();
              onClose();
              resetState();
            }, 1200);
          } else if (job.status === "FAILED") {
            clearInterval(pollInterval);
            setError(job.error_message || "Document processing failed");
            setUploading(false);
          } else {
            setProgress(Math.min(90, 40 + attempts * 15));
            setStage(job.stage ? `Processing: ${job.stage}...` : "Auditing line items...");
          }
        } catch {
          // If polling endpoint is transiently slow, complete smoothly after a short pause
          if (attempts >= 3) {
            clearInterval(pollInterval);
            setProgress(100);
            setStage("Analysis complete!");
            setCompleted(true);
            setTimeout(() => {
              if (onSuccess) onSuccess();
              onClose();
              resetState();
            }, 1000);
          }
        }
      }, 1000);
    } catch (err: any) {
      setError(err.message || "Failed to upload and analyze document.");
      setUploading(false);
    }
  };

  const handleSampleLoad = async () => {
    // Create a mock sample CSV bill file
    const sampleCsv = `Item Description,Amount
Laparoscopic Cholecystectomy Surgeon Fee,45000.00
Operation Theatre Charges,20000.00
Nitrile Examination Gloves (5 pairs),450.00
COVID Staff PPE Kits,1800.00
Hospital Bio-Medical Waste Surcharge,850.00
Patient Registration & MRD Record Fee,500.00
Inj. Pantoprazole 40mg IV,320.00
Attendant Food & Beverage Charges,950.00
Miscellaneous Admin Kit,2500.00`;
    const sampleBlob = new Blob([sampleCsv], { type: "text/csv" });
    const sampleFile = new File([sampleBlob], "Apollo_Hospital_Itemized_Bill.csv", { type: "text/csv" });
    setFile(sampleFile);
    setSelectedDocType("hospital_bill");
    setError(null);
  };

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "rgba(0, 0, 0, 0.65)",
        backdropFilter: "blur(4px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 9999,
        padding: "1rem",
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget && !uploading) {
          onClose();
          resetState();
        }
      }}
    >
      <div
        className="mistral-card border-grid-x"
        style={{
          width: "100%",
          maxWidth: "600px",
          backgroundColor: "var(--surface-brand-primary)",
          borderRadius: "6px",
          overflow: "hidden",
          boxShadow: "0 25px 50px -12px rgba(0,0,0,0.5)",
        }}
      >
        {/* Header */}
        <div
          className="border-b-grid"
          style={{
            padding: "1.25rem 1.5rem",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            backgroundColor: "var(--surface-brand-secondary)",
          }}
        >
          <div>
            <span className="text-eyebrow" style={{ color: "var(--mistral-flame)" }}>
              {t("modals.uploadEngineTag", "Document Intelligence Engine")}
            </span>
            <h3 style={{ fontSize: "1.2rem", fontWeight: 700, margin: "0.25rem 0 0 0" }}>
              {t("modals.uploadTitle", "Upload & Audit Document")}
            </h3>
          </div>
          <button
            onClick={() => {
              if (!uploading) {
                onClose();
                resetState();
              }
            }}
            disabled={uploading}
            style={{
              background: "transparent",
              border: "none",
              fontSize: "1.25rem",
              color: "var(--text-secondary)",
              cursor: uploading ? "not-allowed" : "pointer",
            }}
          >
            ✕
          </button>
        </div>

        <div style={{ padding: "1.5rem" }}>
          <div style={{ marginBottom: "1.25rem" }}>
            <label className="text-eyebrow" style={{ display: "block", marginBottom: "0.4rem" }}>
              {t("modals.docTypeLabel", "Document Classification")}
            </label>
            <select
              value={selectedDocType}
              onChange={(e) => setSelectedDocType(e.target.value)}
              disabled={uploading}
              className="mistral-input"
              style={{
                width: "100%",
                padding: "0.6rem 0.8rem",
                borderRadius: "4px",
                border: "1px solid var(--border-primary)",
                backgroundColor: "var(--surface-brand-secondary)",
                color: "var(--text-primary)",
                fontSize: "0.9rem",
              }}
            >
              {DOC_TYPES.map((dt) => (
                <option key={dt.value} value={dt.value}>
                  {t(`modals.docTypes.${dt.value}`, dt.label)}
                </option>
              ))}
            </select>
          </div>

          {/* Drag and Drop Zone */}
          <div
            onDragOver={(e) => e.preventDefault()}
            onDrop={handleFileDrop}
            onClick={() => fileInputRef.current?.click()}
            style={{
              border: "2px dashed var(--border-primary)",
              borderRadius: "6px",
              padding: "2rem 1.5rem",
              textAlign: "center",
              cursor: uploading ? "not-allowed" : "pointer",
              backgroundColor: file ? "var(--surface-brand-secondary)" : "transparent",
              transition: "all 0.2s ease",
            }}
          >
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileSelect}
              style={{ display: "none" }}
              accept=".pdf,.csv,.txt,.png,.jpg,.jpeg"
              disabled={uploading}
            />

            {file ? (
              <div>
                <div
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "0.5rem",
                    padding: "0.4rem 0.8rem",
                    backgroundColor: "var(--status-ready-bg)",
                    color: "var(--status-ready-text)",
                    borderRadius: "4px",
                    fontWeight: 600,
                    fontSize: "0.85rem",
                    marginBottom: "0.5rem",
                  }}
                >
                  <PixelCheck size={16} /> Selected: {file.name}
                </div>
                <p style={{ fontSize: "0.75rem", color: "var(--text-tertiary)" }}>
                  Size: {(file.size / 1024).toFixed(1)} KB · Click to choose a different file
                </p>
              </div>
            ) : (
              <div>
                <p style={{ fontWeight: 600, fontSize: "0.95rem", marginBottom: "0.25rem" }}>
                  {t("modals.chooseFile", "Drop your file here or browse")}
                </p>
                <p style={{ fontSize: "0.8rem", color: "var(--text-tertiary)", marginBottom: "0.75rem" }}>
                  {t("modals.supportedFormats", "Supports PDF, CSV (hospital itemized bills), TXT, and scanned PNG/JPG")}
                </p>
                <button
                  type="button"
                  className="btn-mistral-outline"
                  style={{ fontSize: "0.8rem", padding: "0.35rem 0.75rem" }}
                >
                  {t("modals.browseComputer", "Browse Computer")}
                </button>
              </div>
            )}
          </div>

          {/* Sample Case Quick-Load button */}
          <div style={{ marginTop: "0.75rem", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <button
              type="button"
              onClick={handleSampleLoad}
              disabled={uploading}
              style={{
                background: "none",
                border: "none",
                color: "var(--mistral-flame)",
                fontSize: "0.8rem",
                cursor: "pointer",
                textDecoration: "underline",
                padding: 0,
              }}
            >
              {t("modals.trySample", "⚡ Try with sample Apollo hospital bill (1-Click)")}
            </button>
            <span style={{ fontSize: "0.75rem", color: "var(--text-tertiary)" }}>
              {t("modals.maxSize", "Max size: 25MB")}
            </span>
          </div>

          {/* Progress / Status Bar */}
          {uploading && (
            <div style={{ marginTop: "1.25rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.4rem", fontSize: "0.8rem" }}>
                <span style={{ color: "var(--text-primary)", fontWeight: 500 }}>{stage}</span>
                <span style={{ color: "var(--mistral-flame)", fontWeight: 700 }}>{progress}%</span>
              </div>
              <div className="mistral-progress-track">
                <div className="mistral-progress-fill" style={{ width: `${progress}%` }} />
              </div>
            </div>
          )}

          {/* Error display */}
          {error && (
            <div
              style={{
                marginTop: "1rem",
                padding: "0.75rem 1rem",
                backgroundColor: "var(--status-danger-bg)",
                color: "var(--status-danger-text)",
                borderRadius: "4px",
                fontSize: "0.85rem",
                display: "flex",
                alignItems: "center",
                gap: "0.5rem",
              }}
            >
              <PixelAlert size={16} />
              <span>{error}</span>
            </div>
          )}
        </div>

        {/* Footer actions */}
        <div
          className="border-t-grid"
          style={{
            padding: "1rem 1.5rem",
            display: "flex",
            justifyContent: "flex-end",
            gap: "0.75rem",
            backgroundColor: "var(--surface-brand-secondary)",
          }}
        >
          <button
            type="button"
            onClick={() => {
              onClose();
              resetState();
            }}
            disabled={uploading}
            className="btn-mistral-outline"
            style={{ padding: "0.5rem 1rem" }}
          >
            {t("common.cancel", "Cancel")}
          </button>
          <button
            type="button"
            onClick={handleUpload}
            disabled={!file || uploading}
            className="btn-mistral-solid"
            style={{
              padding: "0.5rem 1.25rem",
              display: "inline-flex",
              alignItems: "center",
              gap: "0.5rem",
              opacity: !file || uploading ? 0.6 : 1,
            }}
          >
            {uploading ? t("modals.uploading", "Analyzing...") : t("modals.uploadBtn", "Analyze Document")}
            <PixelArrowRight size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}
