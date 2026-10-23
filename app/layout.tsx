import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "HireSense AI — Candidate Edition",
  description:
    "Score your resume against any job description with evidence-backed matching, fix the gaps, and practise the interview.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
