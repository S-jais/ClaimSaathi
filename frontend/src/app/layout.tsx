import type { Metadata } from "next";
import Script from "next/script";
import "./globals.css";

export const metadata: Metadata = {
  title: "ClaimSaathi — Frontier Insurance Claim Intelligence",
  description:
    "AI-powered customer-side health insurance claim copilot. Understand your policy, decode rejections under IRDAI 2024 Master Circular, and build legally grounded appeals.",
  keywords: ["insurance claim", "health insurance", "claim rejection", "appeal letter", "IRDAI", "ClaimSaathi"],
  openGraph: {
    title: "ClaimSaathi — Frontier Insurance Claim Intelligence",
    description: "Navigate your health insurance reimbursement claim with AI-powered guidance.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <link rel="icon" href="/favicon.ico" />
        <Script id="theme-initializer" strategy="beforeInteractive">
          {`
            try {
              var stored = localStorage.getItem('theme');
              var prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
              var isDark = stored === 'dark' || ((stored === 'system' || stored === null) && prefersDark);
              if (isDark) {
                document.documentElement.classList.add('dark');
              } else {
                document.documentElement.classList.remove('dark');
              }
            } catch (e) {}
          `}
        </Script>
      </head>
      <body>{children}</body>
    </html>
  );
}
