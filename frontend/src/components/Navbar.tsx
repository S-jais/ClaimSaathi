"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useSyncExternalStore } from "react";
import BrandLogo from "./BrandLogo";
import {
  PixelArrowRight,
  PixelSun,
  PixelMoon,
} from "./PixelIcons";
import { useLanguage } from "@/context/LanguageContext";

interface NavbarProps {
  claimId?: string;
  user?: { full_name: string | null; email: string; is_demo?: boolean } | null;
  onLogout?: () => void;
}

const emptySubscribe = () => () => {};

function useIsMounted() {
  return useSyncExternalStore(
    emptySubscribe,
    () => true,
    () => false
  );
}

function useIsDark() {
  return useSyncExternalStore(
    (callback) => {
      if (typeof window === "undefined") return () => {};
      const observer = new MutationObserver(callback);
      observer.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
      return () => observer.disconnect();
    },
    () => typeof document !== "undefined" && document.documentElement.classList.contains("dark"),
    () => false
  );
}

export function Navbar({ claimId, user, onLogout }: NavbarProps) {
  const pathname = usePathname();
  const mounted = useIsMounted();
  const isDark = useIsDark();
  const { lang, toggleLang, t } = useLanguage();

  const toggleTheme = () => {
    const nextDark = !isDark;
    if (typeof document !== "undefined") {
      if (nextDark) {
        document.documentElement.classList.add("dark");
        localStorage.setItem("theme", "dark");
      } else {
        document.documentElement.classList.remove("dark");
        localStorage.setItem("theme", "light");
      }
    }
  };

  const activeClaimId = claimId || "CLM-20491";

  return (
    <header className="mistral-nav" data-header>
      <div className="mistral-nav-inner">
        {/* Left section: Brand Logo & Navigation */}
        <div className="mistral-nav-left">
          <Link href="/dashboard" className="mistral-nav-brand-link" aria-label="Go to Dashboard">
            <BrandLogo variant={isDark ? "dark" : "light"} size={26} />
          </Link>

          {/* Desktop Navigation Links */}
          <nav className="mistral-nav-links">
            <Link
              href="/dashboard"
              className={`mistral-nav-item ${pathname === "/dashboard" ? "active" : ""}`}
            >
              {t("nav.dashboard", "Dashboard")}
            </Link>

            <Link
              href={`/claims/${activeClaimId}/readiness`}
              className={`mistral-nav-item ${pathname?.includes("/readiness") ? "active" : ""}`}
            >
              {t("nav.readiness", "Readiness Check")}
            </Link>

            <Link
              href={`/claims/${activeClaimId}/rejection`}
              className={`mistral-nav-item ${pathname?.includes("/rejection") ? "active" : ""}`}
            >
              {t("nav.rejection", "Rejection Decoder")}
            </Link>

            <Link
              href={`/claims/${activeClaimId}/appeal`}
              className={`mistral-nav-item ${pathname?.includes("/appeal") ? "active" : ""}`}
            >
              {t("nav.appeal", "Appeal Builder")}
            </Link>
          </nav>
        </div>

        {/* Right section: User info, Language toggle, Theme toggle & CTA */}
        <div className="mistral-nav-right">
          {user && (
            <div className="mistral-nav-user">
              <span className="mistral-nav-user-name">
                {user.full_name?.split(" ")[0] || user.email.split("@")[0]}
              </span>
            </div>
          )}

          {/* Language Selector Toggle */}
          <button
            onClick={toggleLang}
            className="btn-nav-lang"
            title={lang === "en" ? "हिन्दी में बदलें" : "Switch to English"}
            aria-label="Toggle language"
          >
            <span>🌐</span>
            <span>{lang === "en" ? "हिन्दी" : "EN"}</span>
          </button>

          {/* Theme Toggle Button */}
          {mounted && (
            <button
              onClick={toggleTheme}
              className="btn-nav-icon"
              title={isDark ? "Switch to Light theme" : "Switch to Dark theme"}
              aria-label="Toggle theme"
            >
              {isDark ? <PixelSun size={18} /> : <PixelMoon size={18} />}
            </button>
          )}

          {/* Action CTA Button */}
          {onLogout ? (
            <button onClick={onLogout} className="btn-mistral-cta" id="sign-out-btn">
              <span className="cta-label">{t("nav.signOut", "Sign out")}</span>
              <span className="cta-arrow-right">
                <PixelArrowRight size={18} />
              </span>
            </button>
          ) : pathname !== "/" ? (
            <Link href="/dashboard" className="btn-mistral-cta">
              <span className="cta-label">{t("nav.dashboard", "Dashboard")}</span>
              <span className="cta-arrow-right">
                <PixelArrowRight size={18} />
              </span>
            </Link>
          ) : (
            <a
              href="#login-form"
              className="btn-mistral-cta"
              onClick={(e) => {
                e.preventDefault();
                document.getElementById("email")?.focus();
              }}
            >
              <span className="cta-label">{t("nav.signIn", "Sign in")}</span>
              <span className="cta-arrow-right">
                <PixelArrowRight size={18} />
              </span>
            </a>
          )}
        </div>
      </div>
    </header>
  );
}

export const MistralNavbar = Navbar;
export default Navbar;
