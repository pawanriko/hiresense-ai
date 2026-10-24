"use client";

import { useCallback, useEffect, useState } from "react";

interface ResumeItem {
  id: string;
  version: number;
  file_name: string;
  file_type: string;
  parse_status: string;
  parse_error?: string | null;
  sections?: Record<string, string>;
  ats_score: number | null;
  created_at: string;
}

interface AtsCheck { name: string; passed: boolean; detail: string }
interface AtsCategory { name: string; weight: number; score: number; checks: AtsCheck[] }

export default function ResumeLabPage() {
  const [items, setItems] = useState<ResumeItem[]>([]);
  const [latest, setLatest] = useState<ResumeItem | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [configured, setConfigured] = useState(true);
  const [ats, setAts] = useState<{ score: number; categories: AtsCategory[] } | null>(null);
  const [atsFor, setAtsFor] = useState<string | null>(null);

  async function showAts(item: ResumeItem) {
    setAtsFor(item.id);
    const res = await fetch(`/api/resumes/${item.id}`);
    if (res.ok) {
      const data = await res.json();
      setAts(data.ats);
      setLatest(data.resume as ResumeItem);
      await load();
    }
  }

  async function deleteResume(item: ResumeItem) {
    if (!window.confirm(`Delete v${item.version} (${item.file_name}) and its analyses? This cannot be undone.`)) return;
    const res = await fetch(`/api/resumes/${item.id}`, { method: "DELETE" });
    if (res.ok) {
      setMessage("Resume deleted, along with its analyses.");
      if (latest?.id === item.id) { setLatest(null); setAts(null); }
      await load();
    } else setMessage("Could not delete the resume.");
  }

  const load = useCallback(async () => {
    const res = await fetch("/api/resumes");
    if (res.ok) {
      const data = await res.json();
      setItems(data.resumes ?? []);
      setConfigured(data.configured !== false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function onUpload(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    setBusy(true);
    setMessage(null);
    try {
      const res = await fetch("/api/resumes", { method: "POST", body: data });
      const json = await res.json();
      if (!res.ok) {
        setMessage(json?.error?.message ?? "Upload failed.");
      } else {
        setLatest(json.resume as ResumeItem);
        setMessage(
          json.resume.parse_status === "parsed"
            ? "Resume uploaded and parsed. Sections detected are shown below."
            : `Uploaded, but parsing failed: ${json.resume.parse_error ?? "unknown error"}`
        );
        form.reset();
        await load();
      }
    } finally {
      setBusy(false);
    }
  }

  const sectionNames = latest?.sections ? Object.keys(latest.sections) : [];

  return (
    <main className="mx-auto max-w-4xl px-6 py-10">
      <h1 className="text-3xl font-bold">Resume Lab</h1>
      <p className="mt-1 text-slate-600 dark:text-slate-400">
        Upload a PDF or DOCX resume (max 10 MB). It is stored privately, parsed, split into
        sections, and scored by the rule-based ATS engine. Click a version to see its full ATS breakdown.
      </p>

      {!configured && (
        <div className="mt-6 rounded-lg bg-amber-50 dark:bg-amber-950 p-4 text-sm text-amber-800 dark:text-amber-200">
          Supabase is not configured yet, so uploads are disabled. Add the keys to .env.local first.
        </div>
      )}

      <form onSubmit={onUpload} className="mt-8 flex flex-wrap items-center gap-3">
        <input
          type="file"
          name="file"
          accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          required
          className="rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm"
        />
        <button
          type="submit"
          disabled={busy || !configured}
          className="rounded-lg bg-slate-900 dark:bg-slate-100 px-5 py-2.5 font-medium text-white dark:text-slate-900 disabled:opacity-40"
        >
          {busy ? "Uploading & parsing…" : "Upload resume"}
        </button>
      </form>
      {message && <p className="mt-4 text-sm text-slate-700">{message}</p>}

      {ats && atsFor === latest?.id && (
        <section className="mt-8">
          <h2 className="text-lg font-semibold">ATS health score: {ats.score}/100</h2>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Rule-based, JD-independent. Every deduction below names the failed check.</p>
          <div className="mt-3 space-y-3">
            {ats.categories.map((cat) => (
              <div key={cat.name} className="rounded-xl border border-slate-200 dark:border-slate-800 p-4">
                <div className="flex justify-between text-sm">
                  <span className="font-medium">{cat.name} <span className="text-slate-500 dark:text-slate-400">(weight {cat.weight}%)</span></span>
                  <span>{cat.score}/100</span>
                </div>
                <ul className="mt-2 space-y-1">
                  {cat.checks.map((c) => (
                    <li key={c.name} className="text-sm text-slate-600 dark:text-slate-400">
                      {c.passed ? "✓" : "✗"} {c.name} — {c.detail}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </section>
      )}

      {latest && sectionNames.length > 0 && (
        <section className="mt-8">
          <h2 className="text-lg font-semibold">Sections detected in v{latest.version}</h2>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            {sectionNames.map((name) => (
              <div key={name} className="rounded-xl border border-slate-200 dark:border-slate-800 p-4">
                <h3 className="text-sm font-semibold uppercase tracking-wide">{name}</h3>
                <p className="mt-2 line-clamp-4 whitespace-pre-wrap text-sm text-slate-600 dark:text-slate-400">
                  {latest.sections?.[name]}
                </p>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="mt-10">
        <h2 className="text-lg font-semibold">Your versions</h2>
        {items.length === 0 ? (
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">No uploads yet.</p>
        ) : (
          <ul className="mt-3 divide-y divide-slate-100 dark:divide-slate-800 rounded-xl border border-slate-200 dark:border-slate-800">
            {items.map((r) => (
              <li key={r.id} className="flex items-center justify-between gap-3 px-4 py-3 text-sm">
                <span>
                  <span className="font-medium">v{r.version}</span> · {r.file_name}
                  {r.ats_score != null ? ` · ATS ${r.ats_score}` : ""}
                </span>
                <span className="flex items-center gap-2 text-slate-500 dark:text-slate-400">
                  <span>{r.parse_status} · {new Date(r.created_at).toLocaleString()}</span>
                  {r.parse_status === "parsed" && (
                    <button onClick={() => void showAts(r)} className="rounded border border-slate-300 dark:border-slate-700 px-2 py-1 text-xs">ATS detail</button>
                  )}
                  <button onClick={() => void deleteResume(r)} className="rounded border border-red-200 dark:border-red-800 px-2 py-1 text-xs text-red-600 dark:text-red-400">Delete</button>
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
