"use client";

import { useCallback, useEffect, useState } from "react";

interface ResumeItem { id: string; version: number; file_name: string; parse_status: string }
interface JdItem { id: string; title: string; company: string | null; criteria: Criterion[] }
interface Criterion { name: string; category: string; weight: number; required: boolean }
interface CriterionResult { name: string; category: string; weight: number; score: number; status: string; evidence: string | null; section: string | null }
interface Gap { criterion: string; current_status: string; suggested_action: string }
interface Analysis { id: string; resume_id: string; jd_id: string; match_score: number; criteria_results: CriterionResult[]; gaps: Gap[]; created_at: string }
interface Rewrite { id: string; original_bullet: string; rewritten_bullet: string; accepted: boolean }

const STATUS_STYLE: Record<string, string> = {
  strong: "bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-200",
  present: "bg-sky-100 dark:bg-sky-950 text-sky-800 dark:text-sky-200",
  weak: "bg-amber-100 text-amber-800 dark:text-amber-200",
  missing: "bg-red-100 dark:bg-red-950 text-red-800 dark:text-red-200",
};

function download(filename: string, text: string) {
  const blob = new Blob([text], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export default function JdMatchPage() {
  const [resumes, setResumes] = useState<ResumeItem[]>([]);
  const [jds, setJds] = useState<JdItem[]>([]);
  const [resumeId, setResumeId] = useState("");
  const [jdId, setJdId] = useState("");
  const [jdTitle, setJdTitle] = useState("");
  const [jdCompany, setJdCompany] = useState("");
  const [jdText, setJdText] = useState("");
  const [criteria, setCriteria] = useState<Criterion[]>([]);
  const [criteriaSource, setCriteriaSource] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [rewrites, setRewrites] = useState<Rewrite[]>([]);
  const [rewriteSource, setRewriteSource] = useState<string | null>(null);
  const [coverLetter, setCoverLetter] = useState<string | null>(null);
  const [coverSource, setCoverSource] = useState<string | null>(null);
  const [tailored, setTailored] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const loadLists = useCallback(async () => {
    const [r, j] = await Promise.all([fetch("/api/resumes"), fetch("/api/jds")]);
    if (r.ok) {
      const data = await r.json();
      setResumes((data.resumes ?? []).filter((x: ResumeItem) => x.parse_status === "parsed"));
    }
    if (j.ok) {
      const data = await j.json();
      setJds(data.jds ?? []);
    }
  }, []);

  useEffect(() => { void loadLists(); }, [loadLists]);

  // Deep-link: /jd-match?analysis=<id> loads a past analysis.
  useEffect(() => {
    const id = new URLSearchParams(window.location.search).get("analysis");
    if (!id) return;
    void fetch(`/api/matches/${id}`).then(async (res) => {
      if (!res.ok) return;
      const data = await res.json();
      setAnalysis(data.analysis as Analysis);
      setJdId(data.analysis.jd_id);
      setResumeId(data.analysis.resume_id);
    });
  }, []);

  async function createJd(event: React.FormEvent) {
    event.preventDefault();
    setBusy("jd");
    setMessage(null);
    try {
      const res = await fetch("/api/jds", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: jdTitle, company: jdCompany, raw_text: jdText }),
      });
      const data = await res.json();
      if (!res.ok) {
        setMessage(data?.error?.message ?? "Could not save the JD.");
      } else {
        setJdId(data.jd.id);
        setCriteria(data.jd.criteria ?? []);
        setCriteriaSource(data.criteria_source ?? null);
        setAnalysis(null);
        await loadLists();
        setMessage("JD saved. Criteria drafted below — edit names and weights, then save before scoring.");
      }
    } finally { setBusy(null); }
  }

  function selectJd(id: string) {
    setJdId(id);
    const jd = jds.find((x) => x.id === id);
    setCriteria(jd?.criteria ?? []);
    setCriteriaSource(null);
    setAnalysis(null);
  }

  async function extractCriteria() {
    if (!jdId) return;
    setBusy("extract");
    const res = await fetch(`/api/jds/${jdId}/extract-criteria`, { method: "POST" });
    const data = await res.json();
    if (res.ok) {
      setCriteria(data.jd.criteria ?? []);
      setCriteriaSource(data.criteria_source ?? null);
      setMessage(
        data.criteria_source === "ai"
          ? "Criteria re-extracted with AI. Review and edit them — the AI draft is never scored as-is."
          : "AI is not configured (no Groq key), so criteria were drafted by keyword scan. Edit them freely — they are a draft, not a verdict."
      );
    } else setMessage(data?.error?.message ?? "Extraction failed.");
    setBusy(null);
  }

  async function saveCriteria() {
    if (!jdId) return;
    setBusy("criteria");
    const res = await fetch(`/api/jds/${jdId}/criteria`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ criteria }),
    });
    const data = await res.json();
    setMessage(res.ok ? "Criteria saved. These are the weights the scoring engine will use." : (data?.error?.message ?? "Could not save criteria."));
    setBusy(null);
  }

  async function runMatch() {
    if (!resumeId || !jdId) { setMessage("Pick a resume and a JD first."); return; }
    setBusy("match");
    setMessage(null);
    const res = await fetch("/api/matches", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ resume_id: resumeId, jd_id: jdId }),
    });
    const data = await res.json();
    if (!res.ok) setMessage(data?.error?.message ?? "Scoring failed.");
    else {
      setAnalysis(data.analysis as Analysis);
      setRewrites([]);
      setCoverLetter(null);
      setTailored(null);
    }
    setBusy(null);
  }

  async function pushGaps() {
    if (!analysis) return;
    setBusy("tasks");
    const res = await fetch(`/api/matches/${analysis.id}/prep-tasks`, { method: "POST" });
    const data = await res.json();
    setMessage(res.ok ? `${(data.tasks ?? []).length} gap tasks added to your Prep Dashboard.` : (data?.note ?? data?.error?.message ?? "Could not add tasks."));
    setBusy(null);
  }

  async function genRewrites() {
    if (!analysis) return;
    setBusy("rewrites");
    const res = await fetch(`/api/matches/${analysis.id}/rewrites`, { method: "POST" });
    const data = await res.json();
    if (res.ok) {
      setRewrites(data.rewrites ?? []);
      setRewriteSource(data.source ?? null);
      if ((data.rewrites ?? []).length === 0) setMessage(data.note ?? "Nothing to rewrite.");
    } else setMessage(data?.error?.message ?? "Rewrite generation failed.");
    setBusy(null);
  }

  async function toggleRewrite(rw: Rewrite) {
    const res = await fetch(`/api/rewrites/${rw.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ accepted: !rw.accepted }),
    });
    if (res.ok) {
      const data = await res.json();
      setRewrites((prev) => prev.map((x) => (x.id === rw.id ? data.rewrite : x)));
    }
  }

  async function genCoverLetter() {
    if (!analysis) return;
    setBusy("cover");
    const res = await fetch(`/api/matches/${analysis.id}/cover-letter`, { method: "POST" });
    const data = await res.json();
    if (res.ok) { setCoverLetter(data.letter); setCoverSource(data.source); }
    else setMessage(data?.error?.message ?? "Cover letter failed.");
    setBusy(null);
  }

  async function genTailored() {
    if (!analysis) return;
    setBusy("tailored");
    const res = await fetch(`/api/matches/${analysis.id}/tailored-resume`, { method: "POST" });
    const data = await res.json();
    if (res.ok) setTailored(data.content);
    else setMessage(data?.error?.message ?? "Tailored resume failed.");
    setBusy(null);
  }

  const totalWeight = criteria.reduce((s, c) => s + c.weight, 0);

  return (
    <main className="mx-auto max-w-4xl px-6 py-10">
      <h1 className="text-3xl font-bold">JD Match</h1>
      <p className="mt-1 text-slate-600 dark:text-slate-400">
        Paste a job description, approve the criteria and weights, then run the deterministic scoring engine.
        The AI only drafts criteria — it never computes your score.
      </p>
      {message && <p className="mt-4 rounded-lg bg-slate-100 dark:bg-slate-800 p-3 text-sm text-slate-700">{message}</p>}

      <section className="mt-8">
        <h2 className="text-lg font-semibold">1 · Job description</h2>
        <form onSubmit={createJd} className="mt-3 space-y-3">
          <div className="flex flex-wrap gap-3">
            <input value={jdTitle} onChange={(e) => setJdTitle(e.target.value)} placeholder="Role title, e.g. Frontend Intern" required className="flex-1 rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm" />
            <input value={jdCompany} onChange={(e) => setJdCompany(e.target.value)} placeholder="Company (optional)" className="rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm" />
          </div>
          <textarea value={jdText} onChange={(e) => setJdText(e.target.value)} placeholder="Paste the full job description here…" required rows={7} className="w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm" />
          <button disabled={busy === "jd"} className="rounded-lg bg-slate-900 dark:bg-slate-100 px-5 py-2.5 text-sm font-medium text-white dark:text-slate-900 disabled:opacity-40">
            {busy === "jd" ? "Saving…" : "Save JD & draft criteria"}
          </button>
        </form>
        {jds.length > 0 && (
          <div className="mt-4">
            <label className="text-sm text-slate-600 dark:text-slate-400">Or pick a saved JD: </label>
            <select value={jdId} onChange={(e) => selectJd(e.target.value)} className="rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm">
              <option value="">—</option>
              {jds.map((j) => <option key={j.id} value={j.id}>{j.title}{j.company ? ` · ${j.company}` : ""}</option>)}
            </select>
          </div>
        )}
      </section>

      {jdId && (
        <section className="mt-10">
          <h2 className="text-lg font-semibold">2 · Criteria — review and edit before scoring</h2>
          {criteriaSource && <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Draft source: {criteriaSource}. Total weight: {totalWeight} (weights are normalised by the engine, but keep them near 100).</p>}
          {criteria.length === 0 ? (
            <p className="mt-3 text-sm text-slate-600 dark:text-slate-400">No criteria detected. Click “Extract criteria” or add rows manually.</p>
          ) : (
            <div className="mt-3 space-y-2">
              {criteria.map((c, i) => (
                <div key={i} className="flex flex-wrap items-center gap-2">
                  <input value={c.name} onChange={(e) => setCriteria((prev) => prev.map((x, j) => (j === i ? { ...x, name: e.target.value } : x)))} className="flex-1 rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm" />
                  <input value={c.weight} type="number" min={0} max={100} onChange={(e) => setCriteria((prev) => prev.map((x, j) => (j === i ? { ...x, weight: Number(e.target.value) } : x)))} className="w-20 rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm" />
                  <label className="flex items-center gap-1 text-sm text-slate-600 dark:text-slate-400">
                    <input type="checkbox" checked={c.required} onChange={(e) => setCriteria((prev) => prev.map((x, j) => (j === i ? { ...x, required: e.target.checked } : x)))} /> Required
                  </label>
                  <button onClick={() => setCriteria((prev) => prev.filter((_, j) => j !== i))} className="rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm">Remove</button>
                </div>
              ))}
            </div>
          )}
          <div className="mt-3 flex flex-wrap gap-2">
            <button onClick={() => setCriteria((prev) => [...prev, { name: "", category: "skill", weight: 10, required: false }])} className="rounded-lg border border-slate-300 dark:border-slate-700 px-4 py-2 text-sm">Add criterion</button>
            <button onClick={extractCriteria} disabled={busy === "extract"} className="rounded-lg border border-slate-300 dark:border-slate-700 px-4 py-2 text-sm disabled:opacity-40">Extract criteria</button>
            <button onClick={saveCriteria} disabled={busy === "criteria"} className="rounded-lg bg-slate-900 dark:bg-slate-100 px-4 py-2 text-sm font-medium text-white dark:text-slate-900 disabled:opacity-40">Save criteria</button>
          </div>
        </section>
      )}

      <section className="mt-10">
        <h2 className="text-lg font-semibold">3 · Run the match</h2>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <select value={resumeId} onChange={(e) => setResumeId(e.target.value)} className="rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm">
            <option value="">Pick a resume…</option>
            {resumes.map((r) => <option key={r.id} value={r.id}>v{r.version} · {r.file_name}</option>)}
          </select>
          <button onClick={runMatch} disabled={busy === "match" || !resumeId || !jdId} className="rounded-lg bg-slate-900 dark:bg-slate-100 px-5 py-2.5 text-sm font-medium text-white dark:text-slate-900 disabled:opacity-40">
            {busy === "match" ? "Scoring…" : "Run match"}
          </button>
        </div>
        {resumes.length === 0 && <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">No parsed resumes yet — upload one in the Resume Lab first.</p>}
      </section>

      {analysis && (
        <section className="mt-10">
          <h2 className="text-2xl font-bold">Match score: {analysis.match_score}/100</h2>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Score = Σ(weight × criterion score) / Σweights. Every point below is backed by a quote from your resume.</p>
          <div className="mt-4 space-y-3">
            {analysis.criteria_results.map((r) => (
              <div key={r.name} className="rounded-xl border border-slate-200 dark:border-slate-800 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-medium">{r.name} <span className="text-sm text-slate-500 dark:text-slate-400">· weight {r.weight}</span></span>
                  <span className={`rounded-full px-3 py-1 text-xs font-medium ${STATUS_STYLE[r.status] ?? "bg-slate-100 dark:bg-slate-800"}`}>{r.status} · {r.score}</span>
                </div>
                <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
                  {r.evidence ? <>“{r.evidence}” <span className="text-slate-400">({r.section})</span></> : "No evidence found in this resume."}
                </p>
              </div>
            ))}
          </div>

          {analysis.gaps.length > 0 && (
            <div className="mt-6">
              <h3 className="text-lg font-semibold">Gaps — each one is fixable</h3>
              <ul className="mt-2 space-y-2">
                {analysis.gaps.map((g) => (
                  <li key={g.criterion} className="rounded-xl border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950 p-4 text-sm">
                    <span className="font-medium">{g.criterion} ({g.current_status})</span> — {g.suggested_action}
                  </li>
                ))}
              </ul>
              <button onClick={pushGaps} disabled={busy === "tasks"} className="mt-3 rounded-lg bg-slate-900 dark:bg-slate-100 px-4 py-2 text-sm font-medium text-white dark:text-slate-900 disabled:opacity-40">
                {busy === "tasks" ? "Adding…" : "Push gaps to Prep Dashboard"}
              </button>
            </div>
          )}

          <div className="mt-8 flex flex-wrap gap-2">
            <button onClick={genRewrites} disabled={busy === "rewrites"} className="rounded-lg border border-slate-300 dark:border-slate-700 px-4 py-2 text-sm disabled:opacity-40">Generate bullet rewrites</button>
            <button onClick={genCoverLetter} disabled={busy === "cover"} className="rounded-lg border border-slate-300 dark:border-slate-700 px-4 py-2 text-sm disabled:opacity-40">Generate cover letter</button>
            <button onClick={genTailored} disabled={busy === "tailored"} className="rounded-lg border border-slate-300 dark:border-slate-700 px-4 py-2 text-sm disabled:opacity-40">Generate tailored resume</button>
          </div>

          {rewrites.length > 0 && (
            <div className="mt-6">
              <h3 className="text-lg font-semibold">Bullet rewrites {rewriteSource ? <span className="text-sm font-normal text-slate-500 dark:text-slate-400">({rewriteSource === "ai" ? "AI-generated" : "template draft — edit before using"})</span> : null}</h3>
              <div className="mt-2 space-y-3">
                {rewrites.map((rw) => (
                  <div key={rw.id} className="rounded-xl border border-slate-200 dark:border-slate-800 p-4 text-sm">
                    <p className="text-slate-500 dark:text-slate-400">Original: {rw.original_bullet}</p>
                    <p className="mt-1 font-medium">Rewrite: {rw.rewritten_bullet}</p>
                    <button onClick={() => void toggleRewrite(rw)} className="mt-2 rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-1.5 text-xs">
                      {rw.accepted ? "✓ Accepted — click to undo" : "Accept this rewrite"}
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {coverLetter && (
            <div className="mt-6">
              <h3 className="text-lg font-semibold">Cover letter {coverSource ? <span className="text-sm font-normal text-slate-500 dark:text-slate-400">({coverSource === "ai" ? "AI-generated" : "template"})</span> : null}</h3>
              <pre className="mt-2 whitespace-pre-wrap rounded-xl border border-slate-200 dark:border-slate-800 p-4 text-sm">{coverLetter}</pre>
              <button onClick={() => download("cover-letter.txt", coverLetter)} className="mt-2 rounded-lg border border-slate-300 dark:border-slate-700 px-4 py-2 text-sm">Download .txt</button>
            </div>
          )}

          {tailored && (
            <div className="mt-6">
              <h3 className="text-lg font-semibold">Tailored resume draft</h3>
              <pre className="mt-2 whitespace-pre-wrap rounded-xl border border-slate-200 dark:border-slate-800 p-4 text-sm">{tailored}</pre>
              <button onClick={() => download("tailored-resume.md", tailored)} className="mt-2 rounded-lg border border-slate-300 dark:border-slate-700 px-4 py-2 text-sm">Download .md</button>
            </div>
          )}
        </section>
      )}
    </main>
  );
}
