"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { auth, type UserProfile } from "@/lib/api";
import { MistralNavbar } from "@/components/MistralNavbar";
import {
  PixelArrowLeft,
  PixelCheck,
  PixelSettings,
} from "@/components/PixelIcons";
import { useLanguage, type SupportedLanguage } from "@/context/LanguageContext";

export default function SettingsPage() {
  const { lang, setLang, t, availableLanguages } = useLanguage();
  const [user, setUser] = useState<UserProfile | null>(null);

  useEffect(() => {
    if (auth.isLoggedIn()) {
      auth.me().then(setUser).catch(() => {});
    }
  }, []);

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      {/* Navbar without any corner language toggle */}
      <MistralNavbar user={user} onLogout={() => auth.logout().then(() => window.location.href = "/")} />

      <main className="mistral-main" style={{ flex: 1, display: "flex", flexDirection: "column" }}>
        <div className="max-w-mistral border-grid-x" style={{ flex: 1, display: "flex", flexDirection: "column" }}>
          {/* Top Header Stripe */}
          <div className="mistral-stripe" />

          {/* Settings Header */}
          <section className="border-b-grid" style={{ padding: "2.5rem 2rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1.5rem" }}>
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.5rem" }}>
                  <Link
                    href="/dashboard"
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "0.4rem",
                      color: "var(--text-secondary)",
                      fontSize: "0.8rem",
                      fontWeight: 600,
                    }}
                  >
                    <PixelArrowLeft size={14} /> {t("settings.backToDashboard", "Back to Dashboard")}
                  </Link>
                  <span style={{ color: "var(--border-secondary)" }}>/</span>
                  <span className="text-eyebrow">PREFERENCES</span>
                  <span className="mistral-badge badge-ready">CONFIGURED</span>
                </div>

                <h1 className="text-h1" style={{ marginBottom: "0.5rem", display: "flex", alignItems: "center", gap: "0.75rem" }}>
                  <PixelSettings size={28} />
                  {t("settings.title", "Settings & Preferences")}
                </h1>
                <p style={{ color: "var(--text-secondary)", fontSize: "0.95rem", maxWidth: "680px" }}>
                  {t("settings.subtitle", "Manage your display language, account profile, and privacy preferences.")}
                </p>
              </div>
            </div>
          </section>

          {/* Content Grid */}
          <div className="divide-grid-y" style={{ flex: 1 }}>
            {/* 1. Language Selection Section */}
            <section className="mistral-cell" style={{ padding: "2rem" }}>
              <div style={{ marginBottom: "1.5rem" }}>
                <span className="text-eyebrow" style={{ color: "var(--mistral-amber)", marginBottom: "0.35rem", display: "block" }}>
                  LOCALIZATION
                </span>
                <h2 className="text-h2" style={{ marginBottom: "0.25rem" }}>
                  {t("settings.languageSectionTitle", "Language")}
                </h2>
                <p style={{ color: "var(--text-secondary)", fontSize: "0.9rem" }}>
                  {t("settings.languageSectionSubtitle", "Choose your preferred language across ClaimSaathi")}
                </p>
              </div>

              {/* 3 Language Option Cards */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
                  gap: "1rem",
                }}
              >
                {availableLanguages.map((item) => {
                  const isSelected = lang === item.code;
                  return (
                    <button
                      key={item.code}
                      onClick={() => setLang(item.code)}
                      style={{
                        display: "flex",
                        flexDirection: "column",
                        alignItems: "flex-start",
                        textAlign: "left",
                        padding: "1.25rem 1.5rem",
                        backgroundColor: isSelected
                          ? "var(--surface-brand-secondary)"
                          : "transparent",
                        border: isSelected
                          ? "2px solid var(--mistral-amber)"
                          : "1px solid var(--border-primary)",
                        borderRadius: "4px",
                        cursor: "pointer",
                        transition: "all 0.15s ease",
                        position: "relative",
                        outline: "none",
                      }}
                      onMouseEnter={(e) => {
                        if (!isSelected) {
                          e.currentTarget.style.borderColor = "var(--border-secondary)";
                          e.currentTarget.style.backgroundColor = "var(--surface-brand-primary)";
                        }
                      }}
                      onMouseLeave={(e) => {
                        if (!isSelected) {
                          e.currentTarget.style.borderColor = "var(--border-primary)";
                          e.currentTarget.style.backgroundColor = "transparent";
                        }
                      }}
                    >
                      {/* Top row: Flag + Title + Selected Badge */}
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                          width: "100%",
                          marginBottom: "0.5rem",
                        }}
                      >
                        <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
                          <span style={{ fontSize: "1.4rem" }}>{item.flag}</span>
                          <span
                            style={{
                              fontSize: "1.05rem",
                              fontWeight: 700,
                              color: "var(--text-primary)",
                            }}
                          >
                            {item.code === "en"
                              ? t("settings.enName", "English")
                              : item.code === "hi"
                              ? t("settings.hiName", "हिन्दी")
                              : t("settings.hinglishName", "Hinglish")}
                          </span>
                        </div>

                        {isSelected ? (
                          <span
                            className="mistral-badge badge-ready"
                            style={{
                              display: "inline-flex",
                              alignItems: "center",
                              gap: "0.3rem",
                              fontSize: "0.75rem",
                              padding: "2px 8px",
                            }}
                          >
                            <PixelCheck size={12} />
                            {t("settings.activeBadge", "Active")}
                          </span>
                        ) : (
                          <span
                            style={{
                              width: "18px",
                              height: "18px",
                              borderRadius: "50%",
                              border: "1px solid var(--border-secondary)",
                            }}
                          />
                        )}
                      </div>

                      {/* Description */}
                      <p
                        style={{
                          fontSize: "0.82rem",
                          color: "var(--text-secondary)",
                          lineHeight: 1.5,
                          margin: 0,
                        }}
                      >
                        {item.code === "en"
                          ? t("settings.enDesc", "Standard professional English across all workflows")
                          : item.code === "hi"
                          ? t("settings.hiDesc", "शुद्ध एवं प्रामाणिक देवनागरी हिन्दी भाषा")
                          : t("settings.hinglishDesc", "Conversational Hindi written in English script (e.g. Apni details yahan dekhein)")}
                      </p>
                    </button>
                  );
                })}
              </div>
            </section>

            {/* 2. Account Profile Section */}
            <section className="mistral-cell" style={{ padding: "2rem" }}>
              <div style={{ marginBottom: "1.25rem" }}>
                <span className="text-eyebrow" style={{ color: "var(--text-tertiary)", marginBottom: "0.35rem", display: "block" }}>
                  IDENTITY & PROFILE
                </span>
                <h2 className="text-h2" style={{ marginBottom: "0.25rem" }}>
                  {t("settings.accountSectionTitle", "Account Profile")}
                </h2>
                <p style={{ color: "var(--text-secondary)", fontSize: "0.9rem" }}>
                  {t("settings.accountSectionSubtitle", "Current authenticated user session")}
                </p>
              </div>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
                  gap: "1.5rem",
                  padding: "1.25rem",
                  backgroundColor: "var(--surface-brand-secondary)",
                  border: "1px solid var(--border-primary)",
                  borderRadius: "4px",
                }}
              >
                <div>
                  <span className="text-eyebrow" style={{ fontSize: "0.7rem", color: "var(--text-tertiary)", display: "block", marginBottom: "0.25rem" }}>
                    {t("settings.fullNameLabel", "Full Name")}
                  </span>
                  <span style={{ fontSize: "0.95rem", fontWeight: 600, color: "var(--text-primary)" }}>
                    {user?.full_name || "Siddhartha Jaiswal (Demo)"}
                  </span>
                </div>

                <div>
                  <span className="text-eyebrow" style={{ fontSize: "0.7rem", color: "var(--text-tertiary)", display: "block", marginBottom: "0.25rem" }}>
                    {t("settings.emailLabel", "Email Address")}
                  </span>
                  <span style={{ fontSize: "0.95rem", fontWeight: 600, color: "var(--text-primary)" }}>
                    {user?.email || "siddhartha.jaiswal@demo.claimsaathi.in"}
                  </span>
                </div>

                <div>
                  <span className="text-eyebrow" style={{ fontSize: "0.7rem", color: "var(--text-tertiary)", display: "block", marginBottom: "0.25rem" }}>
                    {t("settings.statusLabel", "Account Status")}
                  </span>
                  <span className="mistral-badge badge-ready" style={{ fontSize: "0.75rem", padding: "2px 8px" }}>
                    {user?.is_demo
                      ? t("settings.guestStatus", "Guest / Demo Account")
                      : t("settings.activeStatus", "Active Policyholder")}
                  </span>
                </div>
              </div>
            </section>

            {/* 3. Security & Governance Section */}
            <section className="mistral-cell" style={{ padding: "2rem" }}>
              <div style={{ marginBottom: "1.25rem" }}>
                <span className="text-eyebrow" style={{ color: "var(--text-tertiary)", marginBottom: "0.35rem", display: "block" }}>
                  DATA SAFEGUARD
                </span>
                <h2 className="text-h2" style={{ marginBottom: "0.25rem" }}>
                  {t("settings.privacySectionTitle", "Security & Data Governance")}
                </h2>
                <p style={{ color: "var(--text-secondary)", fontSize: "0.9rem" }}>
                  {t("settings.privacySectionSubtitle", "Policyholder protections enforced across all modules")}
                </p>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "1rem" }}>
                <div style={{ padding: "1.25rem", border: "1px solid var(--border-primary)", borderRadius: "4px" }}>
                  <h4 style={{ fontSize: "0.95rem", fontWeight: 700, marginBottom: "0.35rem", color: "var(--text-primary)" }}>
                    🛡️ {t("settings.privacyItem1Title", "Zero Audio Retention")}
                  </h4>
                  <p style={{ fontSize: "0.83rem", color: "var(--text-secondary)", lineHeight: 1.5, margin: 0 }}>
                    {t("settings.privacyItem1Desc", "Voice interactions are processed in volatile memory. Audio recordings are never stored on server disks.")}
                  </p>
                </div>

                <div style={{ padding: "1.25rem", border: "1px solid var(--border-primary)", borderRadius: "4px" }}>
                  <h4 style={{ fontSize: "0.95rem", fontWeight: 700, marginBottom: "0.35rem", color: "var(--text-primary)" }}>
                    📜 {t("settings.privacyItem2Title", "IRDAI Master Circular 2024 Alignment")}
                  </h4>
                  <p style={{ fontSize: "0.83rem", color: "var(--text-secondary)", lineHeight: 1.5, margin: 0 }}>
                    {t("settings.privacyItem2Desc", "All claim audits, moratorium calculations, and appeal drafts are strictly cited from official regulatory rules.")}
                  </p>
                </div>

                <div style={{ padding: "1.25rem", border: "1px solid var(--border-primary)", borderRadius: "4px" }}>
                  <h4 style={{ fontSize: "0.95rem", fontWeight: 700, marginBottom: "0.35rem", color: "var(--text-primary)" }}>
                    ✋ {t("settings.privacyItem3Title", "Human-in-the-Loop Gatekeeper")}
                  </h4>
                  <p style={{ fontSize: "0.83rem", color: "var(--text-secondary)", lineHeight: 1.5, margin: 0 }}>
                    {t("settings.privacyItem3Desc", "Draft representations are never dispatched automatically. Explicit customer review and approval is required.")}
                  </p>
                </div>
              </div>
            </section>
          </div>
        </div>
      </main>
    </div>
  );
}
