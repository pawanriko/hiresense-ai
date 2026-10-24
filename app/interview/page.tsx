"use client";

import { useCallback, useEffect, useState } from "react";
import { TRACKS } from "@/lib/interview/questions";

interface ResumeItem { id: string; version: number; file_name: string; parse_status: string }
interface JdItem { id: string; title: string; company: string | null }
interface TranscriptItem { question: string; topic: string; answer: string | null; feedback: string | null; scores: Record<string, number> | null; overall: number | null }
interface Session { id: string; track: string; difficulty: string; status: string; overall_score: number | null; transcript: TranscriptItem[]; report: Report | null }
interface Report { topic_scores: { topic: string; score: number }[]; weakest_areas: string[]; weakest_question: TranscriptItem | null; feedback_source: string }
interface PastSession { id: string; track: string; difficulty: string; status: string; overall_score: number | null; created_at: string }

const DIMENSIONS = ["relevance", "depth", "structure", "confidence", "conciseness"] as const;

export default function InterviewPage() {
  const [resumes, setResumes] = useState<ResumeItem[]>([]);
  const [jds, setJds] = useState<JdItem[]>([]);
  const [track, setTrack] = useState<string>("HR");
  const [difficulty, setDifficulty] = useState("medium");
  const [resumeId, setResumeId] = useState("");
  const [jdId, setJdId] = useState("");
  const [session, setSession] = useState<Session | null>(null);
  const [answer, setAnswer] = useState("");
  const [lastFeedback, setLastFeedback] = useState<{ feedback: string; scores: Record<string, number>; overall: number; source: string } | null>(null);
  const [past, setPast] = useState<PastSession[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const loadLists = useCallback(async () => {
    const [r, j, s] = await Promise.all([fetch("/api/resumes"), fetch("/api/jds"), fetch("/api/interviews")]);
    if (r.ok) {
      const data = await r.json();
      setResumes((data.resumes ?? []).filter((x: ResumeItem) => x.parse_status === "parsed"));
    }
    if (j.ok) setJds((await j.json()).jds ?? []);
    if (s.ok) setPast((await s.json()).sessions ?? []);
  }, []);

  useEffect(() => { void loadLists(); }, [loadLists]);

  const current = session?.transcript.find((t) => t.answer === null) ?? null;
  const answeredCount = session?.transcript.filter((t) => t.answer !== null).length ?? 0;

  async function start() {
    setBusy(true);
    setMessage(null);
    const res = await fetch("/api/interviews", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ track, difficulty, resume_id: resumeId || null, jd_id: jdId || null }),
    });
    const data = await res.json();
    if (!res.ok) setMessage(data?.error?.message ?? "Could not start the interview.");
    else {
      setSession(data.session as Session);
      setLastFeedback(null);
      setAnswer("");
    }
    setBusy(false);
  }

  async function submitAnswer(event: React.FormEvent) {
    event.preventDefault();
    if (!session) return;
    setBusy(true);
    const res = await fetch(`/api/interviews/${session.id}/answer`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ answer }),
    });
    const data = await res.json();
    if (!res.ok) setMessage(data?.error?.message ?? "Could not score the answer.");
    else {
      setLastFeedback({ feedback: data.feedback, scores: data.scores, overall: data.overall, source: data.feedback_source });
      setSession(data.session as Session);
      setAnswer("");
      if (data.completed) void loadLists();
    }
    setBusy(false);
  }

  async function openReport(id: string) {
    const res = await fetch(`/api/interviews/${id}/report`);
    if (res.ok) {
      const data = await res.json();
      setSession(data.session as Session);
      setLastFeedback(null);
    }
  }

  async function pushRevisionTasks() {
    if (!session?.report) return;
    setBusy(true);
    for (const area of session.report.weakest_areas) {
      await fetch("/api/prep-tasks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: `Practise interview topic: ${area}`,
          source_gap: `Weakest area in your ${session.track} mock interview. Rehearse 2 answers on this topic and re-run a session.`,
        }),
      });
    }
    setMessage("Revision tasks for your weakest areas were added to the Prep Dashboard.");
    setBusy(false);
  }

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <h1 className="text-3xl font-bold">AI Mock Interview</h1>
      <p className="mt-1 text-slate-600 dark:text-slate-400">
        Five questions, one at a time, scored on a fixed rubric (relevance 30%, depth 25%, structure 20%,
        confidence 15%, conciseness 10%). Feedback is AI-generated when a Groq key is configured, otherwise an
        honest checklist score — always labelled.
      </p>
      {message && <p className="mt-4 rounded-lg bg-slate-100 dark:bg-slate-800 p-3 text-sm text-slate-700">{message}</p>}

      {!session && (
        <>
          <section className="mt-8 rounded-xl border border-slate-200 dark:border-slate-800 p-5">
            <h2 className="text-lg font-semibold">Start a session</h2>
            <div className="mt-3 flex flex-wrap gap-3">
              <select value={track} onChange={(e) => setTrack(e.target.value)} className="rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm">
                {TRACKS.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
              <select value={difficulty} onChange={(e) => setDifficulty(e.target.value)} className="rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm">
                <option value="easy">Easy</option>
                <option value="medium">Medium</option>
                <option value="hard">Hard</option>
              </select>
              <select value={resumeId} onChange={(e) => setResumeId(e.target.value)} className="rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm">
                <option value="">Resume (optional)…</option>
                {resumes.map((r) => <option key={r.id} value={r.id}>v{r.version} · {r.file_name}</option>)}
              </select>
              <select value={jdId} onChange={(e) => setJdId(e.target.value)} className="rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm">
                <option value="">JD (optional)…</option>
                {jds.map((j) => <option key={j.id} value={j.id}>{j.title}</option>)}
              </select>
              <button onClick={start} disabled={busy} className="rounded-lg bg-slate-900 dark:bg-slate-100 px-5 py-2.5 text-sm font-medium text-white dark:text-slate-900 disabled:opacity-40">
                {busy ? "Starting…" : "Start interview"}
              </button>
            </div>
          </section>

          {past.length > 0 && (
            <section className="mt-10">
              <h2 className="text-lg font-semibold">Past sessions</h2>
              <ul className="mt-3 divide-y divide-slate-100 dark:divide-slate-800 rounded-xl border border-slate-200 dark:border-slate-800">
                {past.map((s) => (
                  <li key={s.id} className="flex items-center justify-between px-4 py-3 text-sm">
                    <span>{s.track} · {s.difficulty} · {s.status}{s.overall_score != null ? ` · ${s.overall_score}/100` : ""}</span>
                    {s.status === "completed" ? (
                      <button onClick={() => void openReport(s.id)} className="underline">View report</button>
                    ) : (
                      <span className="text-slate-400">in progress</span>
                    )}
                  </li>
                ))}
              </ul>
            </section>
          )}
        </>
      )}

      {session && session.status === "in_progress" && current && (
        <section className="mt-8">
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Question {answeredCount + 1} of {session.transcript.length} · {session.track} · {session.difficulty}
          </p>
          <h2 className="mt-2 text-xl font-semibold">{current.question}</h2>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Topic: {current.topic}</p>
          <form onSubmit={submitAnswer} className="mt-4 space-y-3">
            <textarea value={answer} onChange={(e) => setAnswer(e.target.value)} rows={6} required placeholder="Answer out loud in your head, then type it here…" className="w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm" />
            <button disabled={busy} className="rounded-lg bg-slate-900 dark:bg-slate-100 px-5 py-2.5 text-sm font-medium text-white dark:text-slate-900 disabled:opacity-40">
              {busy ? "Scoring…" : "Submit answer"}
            </button>
          </form>
          {lastFeedback && (
            <div className="mt-6 rounded-xl border border-slate-200 dark:border-slate-800 p-5">
              <h3 className="font-semibold">Feedback ({lastFeedback.source === "ai" ? "AI rubric" : "checklist"}) — overall {lastFeedback.overall}/100</h3>
              <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">{lastFeedback.feedback}</p>
              <div className="mt-3 space-y-1">
                {DIMENSIONS.map((d) => (
                  <div key={d} className="flex items-center gap-2 text-sm">
                    <span className="w-28 capitalize text-slate-500 dark:text-slate-400">{d}</span>
                    <div className="h-2 flex-1 rounded bg-slate-100 dark:bg-slate-800"><div className="h-2 rounded bg-slate-900 dark:bg-slate-100" style={{ width: `${lastFeedback.scores[d] ?? 0}%` }} /></div>
                    <span>{lastFeedback.scores[d] ?? 0}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>
      )}

      {session && session.status === "completed" && (
        <section className="mt-8">
          <h2 className="text-2xl font-bold">Interview report — {session.overall_score}/100</h2>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{session.track} · {session.difficulty} · feedback: {session.report?.feedback_source ?? "checklist"}</p>
          <div className="mt-4 space-y-2">
            {(session.report?.topic_scores ?? []).map((t) => (
              <div key={t.topic} className="flex items-center gap-2 text-sm">
                <span className="w-40 text-slate-600 dark:text-slate-400">{t.topic}</span>
                <div className="h-2 flex-1 rounded bg-slate-100 dark:bg-slate-800"><div className="h-2 rounded bg-slate-900 dark:bg-slate-100" style={{ width: `${t.score}%` }} /></div>
                <span>{t.score}</span>
              </div>
            ))}
          </div>
          {(session.report?.weakest_areas ?? []).length > 0 && (
            <p className="mt-4 text-sm"><span className="font-medium">Weakest areas:</span> {session.report!.weakest_areas.join(", ")}</p>
          )}
          {session.report?.weakest_question && (
            <div className="mt-4 rounded-xl border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950 p-4 text-sm">
              <p className="font-medium">Weakest answer — practise this one again:</p>
              <p className="mt-1">Q: {session.report.weakest_question.question}</p>
              <p className="mt-1 text-slate-600 dark:text-slate-400">Your answer: {session.report.weakest_question.answer}</p>
              <p className="mt-1 text-slate-600 dark:text-slate-400">Feedback: {session.report.weakest_question.feedback}</p>
            </div>
          )}
          <div className="mt-4 flex gap-2">
            <button onClick={pushRevisionTasks} disabled={busy} className="rounded-lg bg-slate-900 dark:bg-slate-100 px-4 py-2 text-sm font-medium text-white dark:text-slate-900 disabled:opacity-40">Push revision tasks to dashboard</button>
            <button onClick={() => { setSession(null); setLastFeedback(null); }} className="rounded-lg border border-slate-300 dark:border-slate-700 px-4 py-2 text-sm">Start a new session</button>
          </div>
          <details className="mt-6 text-sm text-slate-600 dark:text-slate-400">
            <summary className="cursor-pointer font-medium text-slate-800">Full transcript</summary>
            <div className="mt-2 space-y-3">
              {session.transcript.map((t, i) => (
                <div key={i} className="rounded-lg border border-slate-100 dark:border-slate-800 p-3">
                  <p className="font-medium">Q{i + 1}: {t.question}</p>
                  <p className="mt-1">A: {t.answer}</p>
                  <p className="mt-1 text-slate-500 dark:text-slate-400">Score {t.overall}/100 — {t.feedback}</p>
                </div>
              ))}
            </div>
          </details>
        </section>
      )}
    </main>
  );
}
