"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

interface Analysis { id: string; match_score: number; created_at: string; job_descriptions: { title: string; company: string | null } | null }
interface Task { id: string; title: string; source_gap: string | null; status: string }
interface Application { id: string; company: string; role: string; status: string; notes: string | null }

const STATUSES = ["Applied", "Interview", "Offer", "Rejected"] as const;

export default function DashboardPage() {
  const [latestScore, setLatestScore] = useState<number | null>(null);
  const [latestAnalysisId, setLatestAnalysisId] = useState<string | null>(null);
  const [trend, setTrend] = useState<{ score: number; date: string }[]>([]);
  const [analyses, setAnalyses] = useState<Analysis[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [appCounts, setAppCounts] = useState<Record<string, number>>({});
  const [applications, setApplications] = useState<Application[]>([]);
  const [company, setCompany] = useState("");
  const [role, setRole] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    const [d, a] = await Promise.all([fetch("/api/dashboard"), fetch("/api/applications")]);
    if (d.ok) {
      const data = await d.json();
      setLatestScore(data.latest_score);
      setLatestAnalysisId(data.latest_analysis_id);
      setTrend(data.trend ?? []);
      setAnalyses(data.analyses ?? []);
      setTasks(data.tasks ?? []);
      setAppCounts(data.application_counts ?? {});
    }
    if (a.ok) setApplications((await a.json()).applications ?? []);
  }, []);

  useEffect(() => { void load(); }, [load]);

  async function setTaskStatus(id: string, status: string) {
    await fetch(`/api/prep-tasks/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    });
    await load();
  }

  async function setAppStatus(id: string, status: string) {
    await fetch(`/api/applications/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    });
    await load();
  }

  async function addApplication(event: React.FormEvent) {
    event.preventDefault();
    const res = await fetch("/api/applications", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ company, role }),
    });
    if (res.ok) {
      setCompany("");
      setRole("");
      await load();
    } else setMessage("Could not add the application.");
  }

  const maxTrend = Math.max(100, ...trend.map((t) => t.score));

  return (
    <main className="mx-auto max-w-4xl px-6 py-10">
      <header>
        <h1 className="text-3xl font-bold">Prep Dashboard</h1>
        <p className="mt-1 text-slate-600 dark:text-slate-400">Your gaps, your applications, your progress — in one place.</p>
      </header>
      {message && <p className="mt-4 text-sm text-slate-600 dark:text-slate-400">{message}</p>}

      <section className="mt-8 grid gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-slate-200 dark:border-slate-800 p-5">
          <h2 className="text-sm font-medium text-slate-500 dark:text-slate-400">Latest match score</h2>
          <p className="mt-1 text-3xl font-bold">{latestScore != null ? `${latestScore}/100` : "—"}</p>
          {latestAnalysisId && <Link href={`/jd-match?analysis=${latestAnalysisId}`} className="mt-1 block text-sm underline">View analysis</Link>}
        </div>
        <div className="rounded-xl border border-slate-200 dark:border-slate-800 p-5">
          <h2 className="text-sm font-medium text-slate-500 dark:text-slate-400">Open prep tasks</h2>
          <p className="mt-1 text-3xl font-bold">{tasks.filter((t) => t.status !== "done").length}</p>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{tasks.filter((t) => t.status === "done").length} done</p>
        </div>
        <div className="rounded-xl border border-slate-200 dark:border-slate-800 p-5">
          <h2 className="text-sm font-medium text-slate-500 dark:text-slate-400">Applications</h2>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
            {STATUSES.map((s) => `${s}: ${appCounts[s] ?? 0}`).join(" · ")}
          </p>
        </div>
      </section>

      <section className="mt-8 grid gap-4 sm:grid-cols-3">
        <Link href="/resume-lab" className="rounded-xl border border-slate-200 dark:border-slate-800 p-5 hover:border-slate-400">
          <h2 className="font-semibold">Resume Lab</h2>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">Upload, parse, and check ATS health.</p>
        </Link>
        <Link href="/jd-match" className="rounded-xl border border-slate-200 dark:border-slate-800 p-5 hover:border-slate-400">
          <h2 className="font-semibold">JD Match</h2>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">Score any JD with evidence quotes, then fix the gaps.</p>
        </Link>
        <Link href="/interview" className="rounded-xl border border-slate-200 dark:border-slate-800 p-5 hover:border-slate-400">
          <h2 className="font-semibold">Mock Interview</h2>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">HR, Technical, DSA, and Frontend tracks with rubric feedback.</p>
        </Link>
      </section>

      {trend.length > 0 && (
        <section className="mt-10">
          <h2 className="text-lg font-semibold">Match score trend</h2>
          <div className="mt-3 flex h-24 items-end gap-2">
            {trend.map((t, i) => (
              <div key={i} className="flex flex-1 flex-col items-center gap-1" title={`${t.score} on ${new Date(t.date).toLocaleDateString()}`}>
                <span className="text-xs text-slate-500 dark:text-slate-400">{t.score}</span>
                <div className="w-full rounded bg-slate-900 dark:bg-slate-100" style={{ height: `${Math.max(4, (t.score / maxTrend) * 80)}px` }} />
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="mt-10">
        <h2 className="text-lg font-semibold">Prep checklist (from your gaps)</h2>
        {tasks.length === 0 ? (
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">Nothing here yet — run a JD match and push its gaps here.</p>
        ) : (
          <ul className="mt-3 divide-y divide-slate-100 dark:divide-slate-800 rounded-xl border border-slate-200 dark:border-slate-800">
            {tasks.map((t) => (
              <li key={t.id} className="flex items-center justify-between gap-3 px-4 py-3 text-sm">
                <div>
                  <p className={t.status === "done" ? "line-through text-slate-400" : "font-medium"}>{t.title}</p>
                  {t.source_gap && <p className="text-slate-500 dark:text-slate-400">{t.source_gap}</p>}
                </div>
                <select value={t.status} onChange={(e) => void setTaskStatus(t.id, e.target.value)} className="rounded-lg border border-slate-300 dark:border-slate-700 px-2 py-1.5 text-sm">
                  <option value="todo">Todo</option>
                  <option value="doing">Doing</option>
                  <option value="done">Done</option>
                </select>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="mt-10">
        <h2 className="text-lg font-semibold">Application tracker</h2>
        <form onSubmit={addApplication} className="mt-3 flex flex-wrap gap-2">
          <input value={company} onChange={(e) => setCompany(e.target.value)} placeholder="Company" required className="rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm" />
          <input value={role} onChange={(e) => setRole(e.target.value)} placeholder="Role" required className="rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm" />
          <button className="rounded-lg bg-slate-900 dark:bg-slate-100 px-4 py-2 text-sm font-medium text-white dark:text-slate-900">Add application</button>
        </form>
        {applications.length === 0 ? (
          <p className="mt-3 text-sm text-slate-600 dark:text-slate-400">No applications tracked yet.</p>
        ) : (
          <ul className="mt-3 divide-y divide-slate-100 dark:divide-slate-800 rounded-xl border border-slate-200 dark:border-slate-800">
            {applications.map((a) => (
              <li key={a.id} className="flex items-center justify-between gap-3 px-4 py-3 text-sm">
                <span><span className="font-medium">{a.company}</span> · {a.role}</span>
                <select value={a.status} onChange={(e) => void setAppStatus(a.id, e.target.value)} className="rounded-lg border border-slate-300 dark:border-slate-700 px-2 py-1.5 text-sm">
                  {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              </li>
            ))}
          </ul>
        )}
      </section>

      {analyses.length > 0 && (
        <section className="mt-10">
          <h2 className="text-lg font-semibold">Recent analyses</h2>
          <ul className="mt-3 divide-y divide-slate-100 dark:divide-slate-800 rounded-xl border border-slate-200 dark:border-slate-800">
            {analyses.map((a) => (
              <li key={a.id} className="flex items-center justify-between px-4 py-3 text-sm">
                <span>{a.job_descriptions?.title ?? "JD"}{a.job_descriptions?.company ? ` · ${a.job_descriptions.company}` : ""}</span>
                <span><Link href={`/jd-match?analysis=${a.id}`} className="underline">{a.match_score}/100</Link> · {new Date(a.created_at).toLocaleDateString()}</span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </main>
  );
}
