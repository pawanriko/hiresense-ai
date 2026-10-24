import Link from "next/link";

// Shared bottom footer, rendered on every page via the root layout.
export default function Footer() {
  return (
    <footer className="mt-16 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900">
      <div className="mx-auto grid max-w-6xl gap-8 px-6 py-10 sm:grid-cols-3">
        <div>
          <p className="font-bold">HireSense AI</p>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
            Know your match score before the company does. Candidate-side interview prep:
            evidence-backed JD matching, gap fixes, and mock interviews.
          </p>
        </div>
        <nav aria-label="Product" className="flex flex-col gap-2 text-sm">
          <p className="font-semibold">Product</p>
          <Link href="/resume-lab" className="text-slate-600 dark:text-slate-400 hover:text-slate-900">Resume Lab</Link>
          <Link href="/jd-match" className="text-slate-600 dark:text-slate-400 hover:text-slate-900">JD Match</Link>
          <Link href="/interview" className="text-slate-600 dark:text-slate-400 hover:text-slate-900">Mock Interview</Link>
          <Link href="/dashboard" className="text-slate-600 dark:text-slate-400 hover:text-slate-900">Prep Dashboard</Link>
        </nav>
        <nav aria-label="Resources" className="flex flex-col gap-2 text-sm">
          <p className="font-semibold">Resources</p>
          <a href="https://github.com/pawanriko/hiresense-ai" className="text-slate-600 dark:text-slate-400 hover:text-slate-900">
            GitHub repository
          </a>
          <a href="https://github.com/pawanriko/hiresense-ai/tree/main/docs" className="text-slate-600 dark:text-slate-400 hover:text-slate-900">
            Design docs (architecture, scoring rubric)
          </a>
          <Link href="/login" className="text-slate-600 dark:text-slate-400 hover:text-slate-900">
            Demo login — demo@hiresense.ai
          </Link>
        </nav>
      </div>
      <div className="border-t border-slate-200 dark:border-slate-800">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2 px-6 py-4 text-xs text-slate-500 dark:text-slate-400">
          <span>© 2026 HireSense AI · Built by Pawan Kumar</span>
          <span>
            Scoring is deterministic and explainable; AI features are labelled when they run.
            Resumes are stored privately.
          </span>
        </div>
      </div>
    </footer>
  );
}
