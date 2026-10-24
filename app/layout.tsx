import type { Metadata } from "next";
import Script from "next/script";
import "./globals.css";
import Header from "./components/Header";
import Footer from "./components/Footer";

// Runs before first paint: applies the stored theme (or system preference)
// so the page never flashes the wrong theme on load.
const THEME_SCRIPT = `(function(){try{var t=localStorage.getItem('hiresense-theme');if(t==='dark'||(!t&&window.matchMedia('(prefers-color-scheme: dark)').matches)){document.documentElement.classList.add('dark');}}catch(e){}})();`;

export const metadata: Metadata = {
  title: "HireSense AI — Candidate Edition",
  description:
    "Score your resume against any job description with evidence-backed matching, fix the gaps, and practise the interview.",
  openGraph: {
    title: "HireSense AI — Candidate Edition",
    description:
      "Know your match score before the company does. Evidence-backed JD matching, gap fixes, and mock interviews for candidates.",
    url: "https://hiresense-ai-nine.vercel.app",
    siteName: "HireSense AI",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="flex min-h-screen flex-col bg-white text-slate-900 antialiased dark:bg-slate-950 dark:text-slate-100">
        <Script id="theme-init" strategy="beforeInteractive">
          {THEME_SCRIPT}
        </Script>
        <Header />
        <div className="flex-1">{children}</div>
        <Footer />
      </body>
    </html>
  );
}
