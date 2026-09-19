"use client";

import React from "react";

export type LogoVariant = "full" | "icon-only" | "favicon" | "monochrome" | "dark" | "light";

interface BrandLogoProps {
  variant?: LogoVariant;
  size?: number;
  className?: string;
  showTagline?: boolean;
}

/**
 * ClaimSaathi Pixel Art Mark
 * Supportive helping hand (Saathi) cradling and safeguarding
 * an insurance document on a 24x24 pixel grid.
 */
export function HelpingHandDocumentMark({
  size = 28,
  variant = "dark",
  className = "",
}: {
  size?: number;
  variant?: LogoVariant;
  className?: string;
}) {
  const isMono = variant === "monochrome";
  const isLight = variant === "light";

  const docBg = isMono ? "currentColor" : isLight ? "#0284C7" : "#38BDF8";
  const docFold = isMono ? "currentColor" : isLight ? "#0369A1" : "#0284C7";
  const docLines = isMono ? "currentColor" : isLight ? "#FFFFFF" : "#F0F9FF";
  const seal = isMono ? "currentColor" : "#10B981";

  const handBase = isMono ? "currentColor" : isLight ? "#0F172A" : "#64748B";
  const handPalm = isMono ? "currentColor" : isLight ? "#2563EB" : "#3B82F6";
  const handThumb = isMono ? "currentColor" : isLight ? "#1D4ED8" : "#60A5FA";

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      style={{ display: "inline-block", flexShrink: 0, verticalAlign: "middle" }}
      aria-label="ClaimSaathi Helping Hand & Document Logo"
    >
      <rect x="10" y="2" width="8" height="12" fill={docBg} />
      <polygon points="18,2 21,5 18,5" fill={docFold} />
      <rect x="18" y="5" width="3" height="9" fill={docBg} />

      <rect x="12" y="4" width="4" height="1.5" fill={docLines} opacity="0.9" />
      <rect x="12" y="7" width="7" height="1.5" fill={docLines} opacity="0.8" />
      <rect x="12" y="10" width="5" height="1.5" fill={docLines} opacity="0.8" />

      <rect x="17" y="10" width="2" height="2" fill={seal} />

      <rect x="2" y="18" width="4" height="4" fill={handBase} />
      <rect x="4" y="16" width="4" height="4" fill={handBase} />

      <rect x="7" y="15" width="12" height="3" fill={handPalm} />
      <rect x="6" y="17" width="11" height="2" fill={handBase} />

      <rect x="7" y="12" width="3" height="4" fill={handThumb} />
      <rect x="18" y="13" width="3" height="3" fill={handThumb} />
    </svg>
  );
}

export default function BrandLogo({
  variant = "dark",
  size = 26,
  className = "",
  showTagline = false,
}: BrandLogoProps) {
  if (variant === "icon-only" || variant === "favicon") {
    return <HelpingHandDocumentMark size={size} variant={variant} className={className} />;
  }

  const isLight = variant === "light";
  const isMono = variant === "monochrome";

  const primaryTextColor = isMono ? "currentColor" : isLight ? "#0F172A" : "#F8FAFC";
  const saathiColor = isMono ? "currentColor" : "#10B981";
  const sublineColor = isMono ? "currentColor" : isLight ? "#64748B" : "#94A3B8";

  return (
    <div
      className={`brand-logo ${className}`}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "0.6rem",
        userSelect: "none",
        whiteSpace: "nowrap",
      }}
    >
      <HelpingHandDocumentMark size={size} variant={variant} />
      <div style={{ display: "inline-flex", flexDirection: "column", justifyContent: "center" }}>
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            fontWeight: 800,
            fontSize: "1.05rem",
            fontFamily: "var(--font-mistral), var(--font-display), sans-serif",
            letterSpacing: "-0.02em",
            lineHeight: 1,
          }}
        >
          <span style={{ color: primaryTextColor }}>Claim</span>
          <span style={{ color: saathiColor }}>Saathi</span>
          <span
            style={{
              fontSize: "0.625rem",
              fontFamily: "var(--font-mono), monospace",
              fontWeight: 700,
              letterSpacing: "0.06em",
              textTransform: "uppercase",
              padding: "1px 5px",
              marginLeft: "6px",
              borderRadius: "3px",
              backgroundColor: "rgba(250, 80, 15, 0.12)",
              color: "var(--mistral-flame)",
              border: "1px solid rgba(250, 80, 15, 0.25)",
            }}
          >
            AI
          </span>
        </div>
        {showTagline && (
          <span
            style={{
              fontSize: "0.6rem",
              fontFamily: "var(--font-mono), monospace",
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              marginTop: "3px",
              color: sublineColor,
              lineHeight: 1,
            }}
          >
            Claim Copilot • IRDAI Aligned
          </span>
        )}
      </div>
    </div>
  );
}
