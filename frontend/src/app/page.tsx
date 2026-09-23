"use client";

import { useState, useEffect, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { auth, getHumanErrorMessage, subscribeColdStart } from "@/lib/api";
import { MistralNavbar } from "@/components/MistralNavbar";
import { PixelArrowRight } from "@/components/PixelIcons";
import { useLanguage } from "@/context/LanguageContext";

export default function LoginPage() {
  const router = useRouter();
  const { t } = useLanguage();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [loading, setLoading] = useState(false);
  const [isColdStarting, setIsColdStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    return subscribeColdStart((status) => {
      setIsColdStarting(status);
    });
  }, []);

  async function handleSubmit(e?: FormEvent) {
    if (e) e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      if (mode === "login") {
        await auth.login(email, password);
      } else {
        await auth.register(email, password, fullName || undefined);
      }
      router.push("/dashboard");
    } catch (err: unknown) {
      const msg = getHumanErrorMessage(err);
      setError(msg);
    } finally {
      setLoading(false);
      setIsColdStarting(false);
    }
  }

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      {/* Mistral Navigation Bar */}
      <MistralNavbar />

      {/* Main Container */}
      <main className="mistral-main" style={{ flex: 1, display: "flex", flexDirection: "column" }}>
        <div className="max-w-mistral border-grid-x" style={{ flex: 1, display: "flex", flexDirection: "column" }}>
          {/* Top Hero Stripe */}
          <div className="mistral-stripe" />

          {/* Hero Section Header */}
          <section className="border-b-grid" style={{ padding: "clamp(2rem, 5vw, 4.5rem) clamp(1.25rem, 4vw, 3rem)" }}>
            <div style={{ maxWidth: "860px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "1.25rem" }}>
                <span className="text-eyebrow">{t("auth.track", "Paytm AI Hackathon · Track 2")}</span>
              </div>

              <h1 className="text-display" style={{ marginBottom: "1.25rem" }}>
                {t("auth.heroTitle", "Frontier claim intelligence.")}<br />
                {t("auth.heroTitleLine2", "In your hands.")}
              </h1>

              <p style={{ fontSize: "clamp(1rem, 1.5vw, 1.25rem)", color: "var(--text-secondary)", lineHeight: 1.6, maxWidth: "700px" }}>
                {t("auth.heroDesc", "We help policyholders navigate health claims, decode rejection notices, and construct legally grounded appeals with verifiable evidence — not guesswork.")}
              </p>

              {/* Accent bars */}
              <div style={{ marginTop: "1.75rem" }}>
                <div className="mistral-accent-bar">
                  <span />
                  <span />
                  <span />
                  <span />
                  <span />
                </div>
              </div>
            </div>
          </section>

          {/* Two-Column Grid: Features Left, Auth Right */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", flex: 1 }}>
            {/* Left Column: Platform Modules */}
            <div className="divide-grid-y" style={{ borderRight: "1px solid var(--border-primary)" }}>
              <div className="mistral-cell">
                <p className="text-eyebrow" style={{ marginBottom: "0.5rem" }}>{t("auth.module1Tag", "Module 01 / Pre-Submission")}</p>
                <h3 className="text-h3" style={{ marginBottom: "0.5rem" }}>{t("auth.module1Title", "Claim Readiness Engine")}</h3>
                <p style={{ color: "var(--text-secondary)", fontSize: "0.9rem", lineHeight: 1.6 }}>
                  {t("auth.module1Desc", "Deterministic Python rule validator across 6 mandatory document categories (discharge summaries, itemized invoices, implant barcode stickers, ICPs). No hallucinated readiness scores.")}
                </p>
                <div style={{ marginTop: "0.75rem", display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                  <span className="mistral-badge">{t("auth.module1Badge1", "Deterministic Checklist")}</span>
                  <span className="mistral-badge">{t("auth.module1Badge2", "Missing Gap Detection")}</span>
                </div>
              </div>

              <div className="mistral-cell">
                <p className="text-eyebrow" style={{ marginBottom: "0.5rem" }}>{t("auth.module2Tag", "Module 02 / Post-Rejection")}</p>
                <h3 className="text-h3" style={{ marginBottom: "0.5rem" }}>{t("auth.module2Title", "Rejection Decoder")}</h3>
                <p style={{ color: "var(--text-secondary)", fontSize: "0.9rem", lineHeight: 1.6 }}>
                  {t("auth.module2Desc", "Tripartite Fact-Interpretation-Recommendation extraction grounded in IRDAI Master Circular 2024. Cross-references 60-month moratorium protections.")}
                </p>
                <div style={{ marginTop: "0.75rem", display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                  <span className="mistral-badge">{t("auth.module2Badge1", "Tripartite Schema")}</span>
                  <span className="mistral-badge">{t("auth.module2Badge2", "Moratorium Rules")}</span>
                </div>
              </div>

              <div className="mistral-cell">
                <p className="text-eyebrow" style={{ marginBottom: "0.5rem" }}>{t("auth.module3Tag", "Module 03 / Escalation")}</p>
                <h3 className="text-h3" style={{ marginBottom: "0.5rem" }}>{t("auth.module3Title", "Appeal Draft Builder")}</h3>
                <p style={{ color: "var(--text-secondary)", fontSize: "0.9rem", lineHeight: 1.6 }}>
                  {t("auth.module3Desc", "Generates clause-by-clause legally grounded rebuttal letters for insurer Grievance Redressal Officers (GRO) and Insurance Ombudsman with citation-backed evidence.")}
                </p>
                <div style={{ marginTop: "0.75rem", display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                  <span className="mistral-badge">{t("auth.module3Badge1", "Clause-by-Clause Rebuttal")}</span>
                  <span className="mistral-badge">{t("auth.module3Badge2", "Ombudsman Ready")}</span>
                </div>
              </div>
            </div>

            {/* Right Column: Auth Compartment */}
            <div style={{ backgroundColor: "var(--surface-brand-primary)", display: "flex", flexDirection: "column" }}>
              {/* Tab Selector */}
              <div style={{ display: "flex", borderBottom: "1px solid var(--border-primary)" }}>
                <button
                  type="button"
                  onClick={() => { setMode("login"); setError(null); }}
                  style={{
                    flex: 1,
                    padding: "0.9rem 1.25rem",
                    fontFamily: "var(--font-mistral)",
                    fontWeight: 600,
                    fontSize: "0.95rem",
                    borderRight: "1px solid var(--border-primary)",
                    backgroundColor: mode === "login" ? "var(--surface-brand-secondary)" : "transparent",
                    color: mode === "login" ? "var(--text-primary)" : "var(--text-tertiary)",
                    transition: "all 0.15s ease",
                  }}
                >
                  {t("auth.signInBtn", "Sign In")}
                </button>
                <button
                  type="button"
                  onClick={() => { setMode("register"); setError(null); }}
                  style={{
                    flex: 1,
                    padding: "0.9rem 1.25rem",
                    fontFamily: "var(--font-mistral)",
                    fontWeight: 600,
                    fontSize: "0.95rem",
                    backgroundColor: mode === "register" ? "var(--surface-brand-secondary)" : "transparent",
                    color: mode === "register" ? "var(--text-primary)" : "var(--text-tertiary)",
                    transition: "all 0.15s ease",
                  }}
                >
                  {t("auth.createAccountBtn", "Create Account")}
                </button>
              </div>

              {/* Form Content */}
              <div style={{ padding: "clamp(1.5rem, 3vw, 2.5rem)", flex: 1, display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
                <div>
                  <div style={{ marginBottom: "1.75rem" }}>
                    <p className="text-eyebrow" style={{ marginBottom: "0.25rem" }}>
                      {mode === "login" ? t("auth.accessTitle", "Access your claims") : t("auth.newAccountTitle", "Create your account")}
                    </p>
                    <h2 className="text-h2">
                      {mode === "login" ? t("auth.accessSubtitle", "Sign in to track, audit, and appeal your claims") : t("auth.newAccountSubtitle", "Get started with AI-powered claim intelligence")}
                    </h2>
                  </div>

                  <form onSubmit={handleSubmit} id="login-form" style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
                    {mode === "register" && (
                      <div>
                        <label className="text-eyebrow" htmlFor="fullName" style={{ display: "block", marginBottom: "0.4rem" }}>
                          {t("auth.nameLabel", "Full Name")}
                        </label>
                        <input
                          id="fullName"
                          className="mistral-input"
                          type="text"
                          placeholder={t("auth.namePlaceholder", "Siddhartha Jaiswal")}
                          value={fullName}
                          onChange={(e) => setFullName(e.target.value)}
                          autoComplete="name"
                        />
                      </div>
                    )}

                    <div>
                      <label className="text-eyebrow" htmlFor="email" style={{ display: "block", marginBottom: "0.4rem" }}>
                        {t("auth.emailLabel", "Email Address")}
                      </label>
                      <input
                        id="email"
                        className="mistral-input"
                        type="email"
                        placeholder={t("auth.emailPlaceholder", "you@example.com")}
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                        autoComplete="email"
                      />
                    </div>

                    <div>
                      <label className="text-eyebrow" htmlFor="password" style={{ display: "block", marginBottom: "0.4rem" }}>
                        {t("auth.passwordLabel", "Password")}
                      </label>
                      <input
                        id="password"
                        className="mistral-input"
                        type="password"
                        placeholder={t("auth.passwordPlaceholder", "Enter your password")}
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        required
                        autoComplete={mode === "login" ? "current-password" : "new-password"}
                      />
                    </div>

                    {isColdStarting && !error && (
                      <div
                        style={{
                          padding: "0.75rem 1rem",
                          backgroundColor: "rgba(255, 130, 4, 0.12)",
                          border: "1px solid rgba(255, 130, 4, 0.35)",
                          color: "var(--mistral-flame)",
                          fontSize: "0.825rem",
                          borderRadius: "3px",
                          display: "flex",
                          alignItems: "center",
                          gap: "0.5rem",
                          lineHeight: 1.4,
                        }}
                      >
                        <span style={{ fontSize: "1rem" }}>⏳</span>
                        <span>{t("auth.coldStartNotice", "Backend server is waking up from idle. Please allow a few seconds on first request...")}</span>
                      </div>
                    )}

                    {error && (
                      <div
                        style={{
                          padding: "0.75rem 1rem",
                          backgroundColor: "var(--status-danger-bg)",
                          border: "1px solid var(--status-danger-border)",
                          color: "var(--status-danger-text)",
                          fontSize: "0.85rem",
                          borderRadius: "3px",
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                          gap: "0.75rem",
                          lineHeight: 1.4,
                        }}
                      >
                        <span>{error}</span>
                        <button
                          type="button"
                          onClick={() => handleSubmit()}
                          style={{
                            background: "transparent",
                            border: "1px solid var(--status-danger-border)",
                            color: "var(--status-danger-text)",
                            borderRadius: "3px",
                            padding: "2px 8px",
                            fontSize: "0.75rem",
                            cursor: "pointer",
                            whiteSpace: "nowrap",
                          }}
                        >
                          {t("common.retry", "Retry")}
                        </button>
                      </div>
                    )}

                    <button
                      id="submit-auth-btn"
                      type="submit"
                      disabled={loading}
                      className="btn-mistral-cta"
                      style={{
                        width: "100%",
                        height: "46px",
                        border: "1px solid var(--action-primary)",
                        marginTop: "0.5rem",
                      }}
                    >
                      <span className="cta-arrow-left">
                        <PixelArrowRight size={18} />
                      </span>
                      <span className="cta-label">
                        {loading
                          ? mode === "login"
                            ? t("auth.signingIn", "Signing in...")
                            : t("auth.creatingAccount", "Creating account...")
                          : mode === "login"
                          ? t("auth.signInBtn", "Sign In")
                          : t("auth.createAccountBtn", "Create Account")}
                      </span>
                      <span className="cta-arrow-right">
                        <PixelArrowRight size={18} />
                      </span>
                    </button>
                  </form>
                </div>

                {/* Regulatory Footnote */}
                <div style={{ marginTop: "2rem", paddingTop: "1.25rem", borderTop: "1px solid var(--border-primary)" }}>
                  <p style={{ fontSize: "0.75rem", color: "var(--text-tertiary)", lineHeight: 1.5 }}>
                    <strong>{t("rejection.disclaimer", "Statutory Disclaimer: ClaimSaathi is a customer-side AI guidance platform. It does not act as an insurer, broker, third-party administrator (TPA), or legal counsel. Claim approvals remain solely with licensed insurers under IRDAI regulations.")}</strong>
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Bottom Banner */}
          <div className="border-t-grid" style={{ padding: "1.25rem 2rem", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "1rem" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <span className="text-eyebrow">ClaimSaathi · Paytm AI Hackathon Track 2</span>
            </div>
            <span className="text-eyebrow" style={{ color: "var(--text-tertiary)" }}>
              {t("brand.irdaiAligned", "IRDAI Master Circular 2024 Grounded")}
            </span>
          </div>
        </div>
      </main>
    </div>
  );
}
