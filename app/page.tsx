export default function Home() {
  return (
    <main className="mx-auto max-w-5xl px-6 py-16">
      <div className="text-center">
        <p className="mb-3 text-sm font-medium tracking-wide text-slate-500 dark:text-slate-400">
          HIRESENSE AI · CANDIDATE EDITION
        </p>
        <h1 className="text-4xl font-bold leading-tight">
          Know your match score before the company does.
        </h1>
        <p className="mt-4 text-lg text-slate-600 dark:text-slate-400">
          Paste a job description and get your resume scored criterion by
          criterion — every point backed by a quote from your own resume, every
          miss turned into a fixable gap. Then practise the interview.
        </p>
        <div className="mt-8 flex justify-center gap-3">
          <a href="/login" className="rounded-lg bg-slate-900 dark:bg-slate-100 px-5 py-3 font-medium text-white dark:text-slate-900">
            Sign in
          </a>
          <a href="/dashboard" className="rounded-lg border border-slate-300 dark:border-slate-700 px-5 py-3 font-medium">
            Go to dashboard
          </a>
        </div>
        <p className="mt-4 text-sm text-slate-500 dark:text-slate-400">
          Demo login: demo@hiresense.ai — use “Try the demo account” on the sign-in page.
        </p>
      </div>

      <section className="mt-16">
        <h2 className="text-center text-xl font-semibold">How a match score is built — no black box</h2>
        <p className="mt-2 text-center text-sm text-slate-600 dark:text-slate-400">
          Illustrative example from the design docs: a Frontend Intern JD against a sample resume.
          Score = Σ(weight × criterion score) / Σweights. The AI never computes a score.
        </p>
        <div className="mt-6 space-y-2">
          {[
            { name: "React", weight: 35, score: 70, note: "“Built a React dashboard…” — experience bullet, no quantified result" },
            { name: "JavaScript", weight: 25, score: 70, note: "“Wrote JavaScript utilities…” — experience bullet, no quantified result" },
            { name: "TypeScript", weight: 20, score: 0, note: "No evidence found → gap: build a small TypeScript project" },
            { name: "Git / GitHub", weight: 20, score: 100, note: "“Managed code with Git…” with action verb and context" },
          ].map((r) => (
            <div key={r.name} className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-200 dark:border-slate-800 px-4 py-3 text-sm">
              <span className="font-medium">{r.name} <span className="text-slate-500 dark:text-slate-400">· weight {r.weight}%</span></span>
              <span className="text-slate-600 dark:text-slate-400">{r.note}</span>
              <span className="font-semibold">{r.score}</span>
            </div>
          ))}
          <p className="pt-2 text-center text-lg font-bold">= 62.0 / 100 — and the one fix that matters most is TypeScript.</p>
        </div>
      </section>

      <section className="mt-16 grid gap-4 sm:grid-cols-2">
        {[
          { href: "/resume-lab", title: "Resume Lab", text: "Upload a PDF/DOCX resume, see its parsed sections and a rule-based ATS health score with every failed check named." },
          { href: "/jd-match", title: "JD Match", text: "Paste a JD, approve editable criteria and weights, then get evidence-backed scores, gaps, rewrites, a cover letter, and a tailored resume." },
          { href: "/interview", title: "Mock Interview", text: "HR, Technical, DSA, and Frontend tracks. Five questions, one at a time, scored on a fixed rubric with a final report." },
          { href: "/dashboard", title: "Prep Dashboard", text: "Gap-driven checklist, match score trend, and an application tracker from Applied to Offer." },
        ].map((m) => (
          <a key={m.href} href={m.href} className="rounded-xl border border-slate-200 dark:border-slate-800 p-5 hover:border-slate-400">
            <h3 className="font-semibold">{m.title}</h3>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{m.text}</p>
          </a>
        ))}
      </section>

      <p className="mt-12 text-center text-sm text-slate-500 dark:text-slate-400">
        Scoring is deterministic and explainable. AI features (criteria drafting, rewrites, interview
        questions/feedback) run on Groq when a key is configured; without one, honest deterministic
        fallbacks run instead and say so.
      </p>
    </main>
  );
}
