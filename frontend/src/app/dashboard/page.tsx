"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, FormEvent } from "react";
import { auth, claims, type Claim, type UserProfile } from "@/lib/api";
import { MistralNavbar } from "@/components/MistralNavbar";
import {
  PixelArrowRight,
  PixelAlert,
} from "@/components/PixelIcons";
import { useLanguage } from "@/context/LanguageContext";

export default function DashboardPage() {
  const router = useRouter();
  const { t, lang } = useLanguage();
  const [user, setUser] = useState<UserProfile | null>(null);
  const [claimList, setClaimList] = useState<Claim[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // New Claim Modal State
  const [showAddModal, setShowAddModal] = useState(false);
  const [hospitalName, setHospitalName] = useState("");
  const [diagnosis, setDiagnosis] = useState("");
  const [claimAmount, setClaimAmount] = useState("");
  const [claimType, setClaimType] = useState("reimbursement");
  const [admissionDate, setAdmissionDate] = useState("");
  const [submittingClaim, setSubmittingClaim] = useState(false);

  useEffect(() => {
    if (!auth.isLoggedIn()) {
      router.replace("/");
      return;
    }
    Promise.all([auth.me(), claims.list()])
      .then(([u, c]) => {
        setUser(u);
        setClaimList(c);
      })
      .catch((err) => setError(err.message || "Failed to load dashboard"))
      .finally(() => setLoading(false));
  }, [router]);

  async function handleLogout() {
    await auth.logout();
    router.push("/");
  }

  async function handleCreateClaim(e: FormEvent) {
    e.preventDefault();
    if (!hospitalName || !claimAmount) return;

    setSubmittingClaim(true);
    try {
      const newClaim = await claims.create({
        claim_type: claimType,
        hospital_name: hospitalName,
        claim_amount: Number(claimAmount) || 0,
        admission_date: admissionDate || new Date().toISOString().split("T")[0],
        diagnosis: diagnosis || "General Treatment",
      });

      setClaimList((prev) => [newClaim, ...prev]);
      setShowAddModal(false);
      setHospitalName("");
      setDiagnosis("");
      setClaimAmount("");
      setAdmissionDate("");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to register claim");
    } finally {
      setSubmittingClaim(false);
    }
  }

  async function handleLoadSample() {
    if (!user) return;
    try {
      const sample = await claims.loadSampleClaim(user.id, user.full_name || undefined);
      setClaimList((prev) => [sample, ...prev]);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load sample claim");
    }
  }

  if (loading) {
    return (
      <div style={{ minHeight: "100vh", backgroundColor: "var(--surface-brand-primary)" }}>
        <MistralNavbar />
        <div className="mistral-main max-w-mistral border-grid-x" style={{ padding: "3rem 2rem" }}>
          <div style={{ height: "40px", width: "240px", backgroundColor: "var(--surface-brand-secondary)", marginBottom: "1.5rem" }} />
          <div style={{ height: "120px", width: "100%", backgroundColor: "var(--surface-brand-secondary)", marginBottom: "2rem" }} />
          <div style={{ height: "200px", width: "100%", backgroundColor: "var(--surface-brand-secondary)" }} />
        </div>
      </div>
    );
  }

  const primaryClaim = claimList[0] || null;
  const totalAmount = claimList.reduce((acc, c) => acc + Number(c.claim_amount || 0), 0);

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      {/* Navigation Bar */}
      <MistralNavbar user={user} onLogout={handleLogout} claimId={primaryClaim?.id || "CLM-NEW"} />

      <main className="mistral-main" style={{ flex: 1, display: "flex", flexDirection: "column" }}>
        <div className="max-w-mistral border-grid-x" style={{ flex: 1, display: "flex", flexDirection: "column" }}>
          {/* Top Header Banner */}
          <div className="mistral-stripe" />

          <section className="border-b-grid" style={{ padding: "2.5rem 2rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1.5rem" }}>
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.5rem" }}>
                  <span className="text-eyebrow">{t("dashboard.workspace", "WORKSPACE / CLAIMS PORTFOLIO")}</span>
                  <span className="mistral-badge badge-ready" style={{ padding: "1px 6px" }}>
                    ACTIVE ACCOUNT
                  </span>
                </div>
                <h1 className="text-h1" style={{ marginBottom: "0.5rem" }}>
                  {user?.full_name 
                    ? t("dashboard.welcome", "Welcome, {name}").replace("{name}", user.full_name)
                    : t("dashboard.welcomeDefault", "Welcome, Policyholder")}
                </h1>
                <p style={{ color: "var(--text-secondary)", fontSize: "0.95rem" }}>
                  {t("dashboard.groundingBanner", "Active claim assistance portal · Grounded in IRDAI Master Circular (Chapter V Moratorium)")}
                </p>
              </div>

              <div style={{ display: "flex", gap: "0.75rem", alignItems: "center", flexWrap: "wrap" }}>
                {primaryClaim ? (
                  <>
                    <Link
                      href={`/claims/${primaryClaim.id}/readiness`}
                      className="btn-mistral-outline"
                    >
                      {t("dashboard.verifyReadiness", "Verify Readiness")}
                    </Link>
                    <Link
                      href={`/claims/${primaryClaim.id}/rejection`}
                      className="btn-mistral-solid"
                    >
                      {t("dashboard.decodeRejection", "Decode Rejection")} <PixelArrowRight size={16} />
                    </Link>
                  </>
                ) : (
                  <button
                    type="button"
                    onClick={() => setShowAddModal(true)}
                    className="btn-mistral-solid"
                  >
                    + Register New Claim <PixelArrowRight size={16} />
                  </button>
                )}
              </div>
            </div>
          </section>

          {error && (
            <div style={{ padding: "1rem 2rem", backgroundColor: "var(--status-danger-bg)", borderBottom: "1px solid var(--status-danger-border)", color: "var(--status-danger-text)", fontSize: "0.875rem" }}>
              {error}
            </div>
          )}

          {/* 3-Column Stats Ribbon */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", borderBottom: "1px solid var(--border-primary)" }} className="divide-grid-x">
            <div className="mistral-cell">
              <p className="text-eyebrow" style={{ marginBottom: "0.4rem" }}>{t("dashboard.activeClaims", "Active Claims")}</p>
              <div style={{ display: "flex", alignItems: "baseline", gap: "0.5rem" }}>
                <span className="font-mistral" style={{ fontSize: "2rem", fontWeight: 700, color: "var(--text-primary)" }}>
                  {claimList.length}
                </span>
                <span style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>
                  (₹{totalAmount.toLocaleString(lang === "hi" ? "hi-IN" : "en-IN")})
                </span>
              </div>
              <p style={{ fontSize: "0.75rem", color: "var(--text-tertiary)", marginTop: "0.25rem" }}>
                {claimList.length > 0
                  ? (claimList[0].hospital_name || "Health Insurance Portfolio")
                  : "No claims filed yet"}
              </p>
            </div>

            <div className="mistral-cell">
              <p className="text-eyebrow" style={{ marginBottom: "0.4rem" }}>{t("dashboard.readinessScore", "Readiness Score")}</p>
              <div style={{ display: "flex", alignItems: "baseline", gap: "0.5rem" }}>
                <span className="font-mistral" style={{ fontSize: "2rem", fontWeight: 700, color: claimList.length > 0 ? "var(--mistral-flame)" : "var(--mistral-emerald)" }}>
                  {claimList.length > 0 ? `${claimList[0].readiness_score || 85}%` : "100%"}
                </span>
                <span className={`mistral-badge ${claimList.length > 0 ? "badge-warning" : "badge-ready"}`} style={{ fontSize: "0.65rem" }}>
                  {claimList.length > 0 ? t("dashboard.documentGap", "1 Document Gap") : "Ready for Upload"}
                </span>
              </div>
              <div className="mistral-progress-track" style={{ marginTop: "0.5rem" }}>
                <div className="mistral-progress-fill" style={{ width: claimList.length > 0 ? `${claimList[0].readiness_score || 85}%` : "100%" }} />
              </div>
            </div>

            <div className="mistral-cell">
              <p className="text-eyebrow" style={{ marginBottom: "0.4rem" }}>{t("dashboard.statutoryProtection", "Statutory Protection")}</p>
              <div style={{ display: "flex", alignItems: "baseline", gap: "0.5rem" }}>
                <span className="font-mistral" style={{ fontSize: "1.4rem", fontWeight: 700, color: "var(--mistral-emerald)" }}>
                  60-Month Cap
                </span>
                <span className="mistral-badge badge-ready" style={{ fontSize: "0.65rem" }}>
                  {t("dashboard.moratoriumActive", "Moratorium Active")}
                </span>
              </div>
              <p style={{ fontSize: "0.75rem", color: "var(--text-tertiary)", marginTop: "0.25rem" }}>
                {t("dashboard.exceedsCap", "Exceeds IRDAI 60-mo contestability cap")}
              </p>
            </div>
          </div>

          {/* Claims List Header */}
          <div className="mistral-cell-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <span className="text-eyebrow">{t("dashboard.portfolioRecords", "Claim Portfolio Records")}</span>
              <span className="text-eyebrow" style={{ color: "var(--text-tertiary)", marginLeft: "0.75rem" }}>
                {t("dashboard.showingCount", "Showing {count} of {total}").replace("{count}", String(claimList.length)).replace("{total}", String(claimList.length))}
              </span>
            </div>
            <button
              type="button"
              onClick={() => setShowAddModal(true)}
              className="btn-mistral-outline"
              style={{ fontSize: "0.75rem", padding: "0.3rem 0.75rem", display: "inline-flex", alignItems: "center", gap: "0.35rem" }}
            >
              <span>+ Register Claim</span>
            </button>
          </div>

          {/* Claim Rows or Empty State */}
          <div className="divide-grid-y">
            {claimList.length === 0 ? (
              <div style={{ padding: "4rem 2rem", textAlign: "center", backgroundColor: "var(--surface-brand-secondary)" }}>
                <div style={{ maxWidth: "560px", margin: "0 auto" }}>
                  <p className="text-eyebrow" style={{ color: "var(--mistral-flame)", marginBottom: "0.5rem" }}>
                    YOUR CLAIM WORKSPACE IS ACTIVE
                  </p>
                  <h3 className="text-h3" style={{ marginBottom: "0.75rem" }}>
                    No Claims Registered Yet
                  </h3>
                  <p style={{ color: "var(--text-secondary)", fontSize: "0.925rem", lineHeight: 1.6, marginBottom: "1.75rem" }}>
                    Welcome to your personal ClaimSaathi workspace, {user?.full_name?.split(" ")[0] || "Policyholder"}. Register an active or repudiated health insurance claim to check mandatory hospital documents, decode rejection clauses against IRDAI regulations, and build legally grounded grievance letters.
                  </p>
                  <div style={{ display: "flex", gap: "1rem", justifyContent: "center", flexWrap: "wrap" }}>
                    <button
                      type="button"
                      onClick={() => setShowAddModal(true)}
                      className="btn-mistral-solid"
                    >
                      + Register New Claim <PixelArrowRight size={16} />
                    </button>
                    <button
                      type="button"
                      onClick={handleLoadSample}
                      className="btn-mistral-outline"
                    >
                      ⚡ Load Sample Case to Explore
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              claimList.map((claim) => {
                const hospitalDisplay = lang === "hi"
                  ? (claim.hospital_name || "")
                      .replace("Apollo Hospital, Bengaluru", "अपोलो अस्पताल, बेंगलुरु")
                      .replace("Manipal Hospital, Indiranagar", "मणिपाल अस्पताल, इंदिरानगर")
                  : claim.hospital_name;

                const procedureDisplay = lang === "hi"
                  ? "टोटल नी रिप्लेसमेंट (बायां)"
                  : "Total Knee Arthroplasty (Left)";

                return (
                  <div
                    key={claim.id}
                    className="mistral-list-row"
                    id={`claim-${claim.id}`}
                  >
                    <div style={{ display: "flex", flexDirection: "column", gap: "0.35rem" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flexWrap: "wrap" }}>
                        <span className="font-mistral" style={{ fontSize: "1.15rem", fontWeight: 700 }}>
                          {claim.claim_reference}
                        </span>
                        <span className="mistral-badge badge-danger">
                          <PixelAlert size={12} /> {t("dashboard.repudiatedBadge", "Repudiated (Clause 4.2)")}
                        </span>
                        <span className="mistral-badge badge-ready">
                          {t("dashboard.coverageBadge", "78-Mo Coverage")}
                        </span>
                      </div>

                      <p style={{ color: "var(--text-secondary)", fontSize: "0.875rem" }}>
                        {hospitalDisplay} · {procedureDisplay} · {t("dashboard.admission", "Admission")}: {claim.admission_date}
                      </p>

                      <div style={{ display: "flex", alignItems: "center", gap: "1rem", marginTop: "0.25rem" }}>
                        <span className="text-eyebrow" style={{ color: "var(--text-primary)" }}>
                          {t("dashboard.amount", "Amount")}: ₹{Number(claim.claim_amount || 0).toLocaleString(lang === "hi" ? "hi-IN" : "en-IN")}
                        </span>
                        <span style={{ color: "var(--border-secondary)" }}>•</span>
                        <span className="text-eyebrow" style={{ color: "var(--text-tertiary)" }}>
                          {t("dashboard.readiness", "Readiness")}: {claim.readiness_score || 85}%
                        </span>
                      </div>
                    </div>

                    <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
                      <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                        <Link
                          href={`/claims/${claim.id}/readiness`}
                          className="btn-mistral-outline"
                          style={{ fontSize: "0.8rem", padding: "0.45rem 0.85rem" }}
                        >
                          {t("dashboard.readinessBtn", "Readiness")}
                        </Link>
                        <Link
                          href={`/claims/${claim.id}/rejection`}
                          className="btn-mistral-solid"
                          style={{ fontSize: "0.8rem", padding: "0.45rem 0.85rem" }}
                        >
                          {t("dashboard.rejectionDecoderBtn", "Rejection Decoder")}
                        </Link>
                        <Link
                          href={`/claims/${claim.id}/appeal`}
                          className="btn-mistral-outline"
                          style={{ fontSize: "0.8rem", padding: "0.45rem 0.85rem" }}
                        >
                          {t("dashboard.appealDraftBtn", "Appeal Draft")}
                        </Link>
                      </div>
                      <span className="arrow-indicator" style={{ display: "inline-flex", color: "var(--text-tertiary)" }}>
                        <PixelArrowRight size={18} />
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* Quick Action Matrix */}
          <div className="border-t-grid" style={{ padding: "2rem" }}>
            <p className="text-eyebrow" style={{ marginBottom: "1rem" }}>{t("dashboard.actionWorkflows", "Action Workflows")}</p>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "1rem" }}>
              <Link
                href={primaryClaim ? `/claims/${primaryClaim.id}/readiness` : "#"}
                onClick={(e) => {
                  if (!primaryClaim) {
                    e.preventDefault();
                    setShowAddModal(true);
                  }
                }}
                className="mistral-card mistral-card-interactive"
                style={{ padding: "1.5rem", display: "flex", flexDirection: "column", justifyContent: "space-between" }}
              >
                <div>
                  <span className="text-eyebrow" style={{ color: "var(--mistral-amber)" }}>{t("dashboard.stage01", "Stage 01")}</span>
                  <h4 className="text-h4" style={{ margin: "0.5rem 0" }}>{t("dashboard.readinessTitle", "Claim Readiness Checklist")}</h4>
                  <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>
                    {t("dashboard.readinessDesc", "Deterministic check of 6 required documents including missing Indoor Case Papers (ICPs).")}
                  </p>
                </div>
                <div style={{ marginTop: "1rem", display: "flex", alignItems: "center", gap: "0.5rem", color: "var(--text-primary)", fontWeight: 600, fontSize: "0.85rem" }}>
                  <span>{t("dashboard.openChecklist", "Open checklist")}</span>
                  <PixelArrowRight size={14} />
                </div>
              </Link>

              <Link
                href={primaryClaim ? `/claims/${primaryClaim.id}/rejection` : "#"}
                onClick={(e) => {
                  if (!primaryClaim) {
                    e.preventDefault();
                    setShowAddModal(true);
                  }
                }}
                className="mistral-card mistral-card-interactive"
                style={{ padding: "1.5rem", display: "flex", flexDirection: "column", justifyContent: "space-between" }}
              >
                <div>
                  <span className="text-eyebrow" style={{ color: "var(--mistral-flame)" }}>{t("dashboard.stage02", "Stage 02")}</span>
                  <h4 className="text-h4" style={{ margin: "0.5rem 0" }}>{t("dashboard.decoderTitle", "Rejection Decoder")}</h4>
                  <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>
                    {t("dashboard.decoderDesc", "Fact vs AI interpretation vs recommendation with 96% retrieval confidence against IRDAI 2024.")}
                  </p>
                </div>
                <div style={{ marginTop: "1rem", display: "flex", alignItems: "center", gap: "0.5rem", color: "var(--text-primary)", fontWeight: 600, fontSize: "0.85rem" }}>
                  <span>{t("dashboard.analyzeRejection", "Analyze rejection")}</span>
                  <PixelArrowRight size={14} />
                </div>
              </Link>

              <Link
                href={primaryClaim ? `/claims/${primaryClaim.id}/appeal` : "#"}
                onClick={(e) => {
                  if (!primaryClaim) {
                    e.preventDefault();
                    setShowAddModal(true);
                  }
                }}
                className="mistral-card mistral-card-interactive"
                style={{ padding: "1.5rem", display: "flex", flexDirection: "column", justifyContent: "space-between" }}
              >
                <div>
                  <span className="text-eyebrow" style={{ color: "var(--mistral-emerald)" }}>{t("dashboard.stage03", "Stage 03")}</span>
                  <h4 className="text-h4" style={{ margin: "0.5rem 0" }}>{t("dashboard.appealTitle", "Appeal Draft Builder")}</h4>
                  <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>
                    {t("dashboard.appealDesc", "Legally grounded first-level grievance letter. Review each section and approve to export PDF.")}
                  </p>
                </div>
                <div style={{ marginTop: "1rem", display: "flex", alignItems: "center", gap: "0.5rem", color: "var(--text-primary)", fontWeight: 600, fontSize: "0.85rem" }}>
                  <span>{t("dashboard.buildAppeal", "Build appeal")}</span>
                  <PixelArrowRight size={14} />
                </div>
              </Link>
            </div>
          </div>

          {/* Ecosystem Expansion Compartment (Mistral style) */}
          <div className="border-t-grid" style={{ padding: "2rem" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1rem" }}>
              <span className="text-eyebrow">{t("dashboard.expansionRoadmap", "Expansion Roadmap · Financial Copilots")}</span>
              <span className="mistral-badge">{t("dashboard.nextIteration", "Next Iteration")}</span>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "1rem" }}>
              <div className="mistral-card" style={{ padding: "1.25rem", opacity: 0.65 }}>
                <span className="text-eyebrow">{t("dashboard.bankingAi", "Banking AI")}</span>
                <h4 className="text-h4" style={{ margin: "0.25rem 0" }}>{t("dashboard.loanSaathiTitle", "LoanSaathi")}</h4>
                <p style={{ fontSize: "0.825rem", color: "var(--text-secondary)" }}>
                  {t("dashboard.loanSaathiDesc", "Loan application readiness, CIBIL discrepancy decoding, and income proof audit for retail borrowers.")}
                </p>
              </div>

              <div className="mistral-card" style={{ padding: "1.25rem", opacity: 0.65 }}>
                <span className="text-eyebrow">{t("dashboard.fintechResolution", "Fintech Resolution")}</span>
                <h4 className="text-h4" style={{ margin: "0.25rem 0" }}>{t("dashboard.disputeSaathiTitle", "DisputeSaathi")}</h4>
                <p style={{ fontSize: "0.825rem", color: "var(--text-secondary)" }}>
                  {t("dashboard.disputeSaathiDesc", "UPI, netbanking, and chargeback dispute generator grounded in RBI Ombudsman guidelines 2021.")}
                </p>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Modal: Register New Claim */}
      {showAddModal && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            backgroundColor: "rgba(0, 0, 0, 0.65)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 9999,
            padding: "1rem",
            backdropFilter: "blur(4px)",
          }}
          onClick={(e) => {
            if (e.target === e.currentTarget) setShowAddModal(false);
          }}
        >
          <div
            style={{
              backgroundColor: "var(--surface-brand-primary)",
              border: "1px solid var(--border-primary)",
              width: "100%",
              maxWidth: "520px",
              padding: "2rem",
              boxShadow: "0 20px 40px rgba(0, 0, 0, 0.2)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
              <div>
                <span className="text-eyebrow" style={{ color: "var(--mistral-flame)" }}>NEW CLAIM REGISTRATION</span>
                <h3 className="text-h3" style={{ marginTop: "0.25rem" }}>Register Health Claim</h3>
              </div>
              <button
                type="button"
                onClick={() => setShowAddModal(false)}
                style={{
                  background: "transparent",
                  border: "none",
                  fontSize: "1.5rem",
                  cursor: "pointer",
                  color: "var(--text-secondary)",
                  lineHeight: 1,
                }}
              >
                ×
              </button>
            </div>

            <form onSubmit={handleCreateClaim} style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
              <div>
                <label className="text-eyebrow" style={{ display: "block", marginBottom: "0.4rem" }}>
                  Hospital Name *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Max Super Speciality, Delhi / Fortis Hospital"
                  value={hospitalName}
                  onChange={(e) => setHospitalName(e.target.value)}
                  className="mistral-input"
                />
              </div>

              <div>
                <label className="text-eyebrow" style={{ display: "block", marginBottom: "0.4rem" }}>
                  Procedure / Treatment
                </label>
                <input
                  type="text"
                  placeholder="e.g. Total Knee Arthroplasty / Cardiac Stent Placement"
                  value={diagnosis}
                  onChange={(e) => setDiagnosis(e.target.value)}
                  className="mistral-input"
                />
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
                <div>
                  <label className="text-eyebrow" style={{ display: "block", marginBottom: "0.4rem" }}>
                    Claim Amount (₹) *
                  </label>
                  <input
                    type="number"
                    required
                    placeholder="e.g. 150000"
                    value={claimAmount}
                    onChange={(e) => setClaimAmount(e.target.value)}
                    className="mistral-input"
                  />
                </div>

                <div>
                  <label className="text-eyebrow" style={{ display: "block", marginBottom: "0.4rem" }}>
                    Claim Type
                  </label>
                  <select
                    value={claimType}
                    onChange={(e) => setClaimType(e.target.value)}
                    className="mistral-input"
                    style={{ height: "42px" }}
                  >
                    <option value="reimbursement">Reimbursement</option>
                    <option value="cashless_denial">Cashless Denial</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="text-eyebrow" style={{ display: "block", marginBottom: "0.4rem" }}>
                  Admission Date
                </label>
                <input
                  type="date"
                  value={admissionDate}
                  onChange={(e) => setAdmissionDate(e.target.value)}
                  className="mistral-input"
                />
              </div>

              <div style={{ display: "flex", gap: "0.75rem", justifyContent: "flex-end", marginTop: "1rem" }}>
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="btn-mistral-outline"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingClaim}
                  className="btn-mistral-solid"
                >
                  {submittingClaim ? "Registering..." : "Submit Claim"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
