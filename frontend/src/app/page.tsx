"use client";

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { auth } from "@/lib/api";
import { MistralNavbar } from "@/components/MistralNavbar";
import { PixelLogo, PixelArrowRight, PixelCheck } from "@/components/PixelIcons";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
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
      const msg = err instanceof Error ? err.message : "Authentication failed. Please verify credentials.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  function handleQuickDemo() {
    setEmail("ramesh.kumar@demo.claimsaathi.in");
    setPassword("DemoPass@2026!");
    setMode("login");
    setError(null);
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
                <span className="text-eyebrow">Paytm AI Hackathon · Track 2</span>
                <span style={{ color: "var(--border-secondary)" }}>/</span>
                <span className="text-eyebrow" style={{ color: "var(--mistral-flame)" }}>IRDAI 2024 Master Circular Grounded</span>
              </div>

              <h1 className="text-display" style={{ marginBottom: "1.25rem" }}>
                Frontier claim intelligence.<br />
                In your hands.
              </h1>

              <p style={{ fontSize: "clamp(1rem, 1.5vw, 1.25rem)", color: "var(--text-secondary)", lineHeight: 1.6, maxWidth: "700px" }}>
                We help policyholders navigate health claims, decode rejection notices, and construct legally grounded appeals with verifiable evidence — not guesswork.
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
            {/* Left Column: Mistral-style Platform Modules */}
            <div className="divide-grid-y" style={{ borderRight: "1px solid var(--border-primary)" }}>
              <div className="mistral-cell">
                <p className="text-eyebrow" style={{ marginBottom: "0.5rem" }}>Module 01 / Pre-Submission</p>
                <h3 className="text-h3" style={{ marginBottom: "0.5rem" }}>Claim Readiness Engine</h3>
                <p style={{ color: "var(--text-secondary)", fontSize: "0.9rem", lineHeight: 1.6 }}>
                  Deterministic Python rule validator across 6 mandatory document categories (discharge summaries, itemized invoices, implant barcode stickers, ICPs). No hallucinated readiness scores.
                </p>
                <div style={{ marginTop: "0.75rem", display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                  <span className="mistral-badge">Deterministic Checklist</span>
                  <span className="mistral-badge">Missing Gap Detection</span>
                </div>
              </div>

              <div className="mistral-cell">
                <p className="text-eyebrow" style={{ marginBottom: "0.5rem" }}>Module 02 / Post-Repudiation</p>
                <h3 className="text-h3" style={{ marginBottom: "0.5rem" }}>Rejection Decoder</h3>
                <p style={{ color: "var(--text-secondary)", fontSize: "0.9rem", lineHeight: 1.6 }}>
                  Rigorous tripartite separation enforced by schema: strictly separates objective <strong style={{ color: "var(--text-primary)" }}>FACT</strong> from <strong style={{ color: "var(--text-primary)" }}>AI INTERPRETATION</strong> and actionable <strong style={{ color: "var(--text-primary)" }}>RECOMMENDATION</strong>.
                </p>
                <div style={{ marginTop: "0.75rem", display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                  <span className="mistral-badge">Strict Schema Separation</span>
                  <span className="mistral-badge">Retrieval Confidence</span>
                </div>
              </div>

              <div className="mistral-cell">
                <p className="text-eyebrow" style={{ marginBottom: "0.5rem" }}>Module 03 / Escalation</p>
                <h3 className="text-h3" style={{ marginBottom: "0.5rem" }}>Appeal Draft Builder</h3>
                <p style={{ color: "var(--text-secondary)", fontSize: "0.9rem", lineHeight: 1.6 }}>
                  Constructs structured First-Level Grievance letters grounded in the IRDAI 2024 Master Circular 60-month moratorium rule. Server-side gatekeeper ensures explicit user sign-off prior to PDF export.
                </p>
                <div style={{ marginTop: "0.75rem", display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                  <span className="mistral-badge">IRDAI 2024 Chapter V</span>
                  <span className="mistral-badge">Gatekeeper Review</span>
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
                  Sign in
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
                  Create account
                </button>
              </div>

              {/* Form Content */}
              <div style={{ padding: "clamp(1.5rem, 3vw, 2.5rem)", flex: 1, display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
                <div>
                  <div style={{ marginBottom: "1.75rem" }}>
                    <p className="text-eyebrow" style={{ marginBottom: "0.25rem" }}>
                      {mode === "login" ? "Welcome back" : "Get started"}
                    </p>
                    <h2 className="text-h2">
                      {mode === "login" ? "Access your claim workspace" : "Register a new account"}
                    </h2>
                  </div>

                  <form onSubmit={handleSubmit} id="login-form" style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
                    {mode === "register" && (
                      <div>
                        <label className="text-eyebrow" htmlFor="fullName" style={{ display: "block", marginBottom: "0.4rem" }}>
                          Full Name
                        </label>
                        <input
                          id="fullName"
                          className="mistral-input"
                          type="text"
                          placeholder="e.g. Ramesh Kumar"
                          value={fullName}
                          onChange={(e) => setFullName(e.target.value)}
                          autoComplete="name"
                        />
                      </div>
                    )}

                    <div>
                      <label className="text-eyebrow" htmlFor="email" style={{ display: "block", marginBottom: "0.4rem" }}>
                        Email Address
                      </label>
                      <input
                        id="email"
                        className="mistral-input"
                        type="email"
                        placeholder="you@example.com"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                        autoComplete="email"
                      />
                    </div>

                    <div>
                      <label className="text-eyebrow" htmlFor="password" style={{ display: "block", marginBottom: "0.4rem" }}>
                        Password
                      </label>
                      <input
                        id="password"
                        className="mistral-input"
                        type="password"
                        placeholder="••••••••"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        required
                        autoComplete={mode === "login" ? "current-password" : "new-password"}
                      />
                    </div>

                    {error && (
                      <div
                        style={{
                          padding: "0.75rem 1rem",
                          backgroundColor: "var(--status-danger-bg)",
                          border: "1px solid var(--status-danger-border)",
                          color: "var(--status-danger-text)",
                          fontSize: "0.85rem",
                          borderRadius: "3px",
                        }}
                      >
                        {error}
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
                        {loading ? "Authenticating..." : mode === "login" ? "Sign in to ClaimSaathi" : "Create Account"}
                      </span>
                      <span className="cta-arrow-right">
                        <PixelArrowRight size={18} />
                      </span>
                    </button>
                  </form>

                  {/* 1-Click Demo Fill Shortcut */}
                  <div
                    style={{
                      marginTop: "2rem",
                      padding: "1.25rem",
                      border: "1px solid var(--border-primary)",
                      backgroundColor: "var(--surface-brand-secondary)",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.5rem" }}>
                      <span className="mistral-badge badge-demo">Instant Demo</span>
                      <span className="text-eyebrow">Evaluator Bypass</span>
                    </div>
                    <p style={{ fontSize: "0.825rem", color: "var(--text-secondary)", marginBottom: "0.75rem", lineHeight: 1.5 }}>
                      Test the end-to-end flow with pre-seeded Ramesh Kumar knee replacement claim (<strong style={{ color: "var(--text-primary)" }}>₹1,84,500</strong> under Star Health, repudiated under Clause 4.2).
                    </p>
                    <button
                      type="button"
                      onClick={handleQuickDemo}
                      className="btn-mistral-outline"
                      style={{ width: "100%", fontSize: "0.825rem", padding: "0.5rem 1rem" }}
                      id="use-demo-creds-btn"
                    >
                      <PixelCheck size={14} /> Fill Demo Credentials & Sign In
                    </button>
                  </div>
                </div>

                {/* Regulatory Footnote */}
                <div style={{ marginTop: "2rem", paddingTop: "1.25rem", borderTop: "1px solid var(--border-primary)" }}>
                  <p style={{ fontSize: "0.75rem", color: "var(--text-tertiary)", lineHeight: 1.5 }}>
                    <strong>Statutory Disclaimer:</strong> ClaimSaathi is a customer-side AI guidance platform. It does not act as an insurer, broker, third-party administrator (TPA), or legal counsel. Claim approvals remain solely with licensed insurers under IRDAI regulations.
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Bottom Banner */}
          <div className="border-t-grid" style={{ padding: "1.25rem 2rem", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "1rem" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
              <PixelLogo size={18} />
              <span className="text-eyebrow">ClaimSaathi Core Engine · Version 2026.1</span>
            </div>
            <span className="text-eyebrow" style={{ color: "var(--text-tertiary)" }}>
              Grounded in IRDAI Master Circular (5 Sept 2024)
            </span>
          </div>
        </div>
      </main>
    </div>
  );
}
