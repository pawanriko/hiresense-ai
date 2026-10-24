import { NextResponse } from "next/server";
import { getServiceClient } from "@/lib/supabase/server";
import { errorJson, requireUser, ownedRow } from "@/lib/api/helpers";
import { scoreAnswerChecklist } from "@/lib/interview/questions";
import { scoreAnswerAi, isGroqConfigured } from "@/lib/ai/groq";

interface TranscriptItem {
  question: string;
  topic: string;
  answer: string | null;
  feedback: string | null;
  scores: Record<string, number> | null;
  overall: number | null;
}

// POST /api/interviews/:id/answer — score one answer, advance to the next
// question, or finish the session with a report when it was the last one.
export async function POST(
  request: Request,
  context: { params: Promise<{ id: string }> }
) {
  const { userId, error } = await requireUser();
  if (userId === null) return error;
  const { id } = await context.params;
  const session = await ownedRow("mock_sessions", id, userId, "id, status, transcript");
  if (!session) return errorJson("not_found", "Interview session not found.", 404);
  if (session.status !== "in_progress") {
    return errorJson("already_done", "This interview is already finished.", 409);
  }
  const body = await request.json().catch(() => null);
  const answer = typeof body?.answer === "string" ? body.answer.trim() : "";
  if (answer.length < 5) {
    return errorJson("bad_input", "Please write an answer of at least a few words.", 400);
  }

  const transcript = (session.transcript ?? []) as TranscriptItem[];
  const index = transcript.findIndex((t) => t.answer === null);
  if (index === -1) return errorJson("already_done", "All questions are answered.", 409);
  const current = transcript[index];

  // AI rubric scoring when configured, checklist scoring otherwise (labelled).
  let scores: Record<string, number> = {
    relevance: 0,
    depth: 0,
    structure: 0,
    confidence: 0,
    conciseness: 0,
  };
  let feedback = "";
  let feedbackSource = "checklist";
  if (isGroqConfigured()) {
    const ai = await scoreAnswerAi(current.question, answer);
    if (ai) {
      scores = {
        relevance: ai.relevance,
        depth: ai.depth,
        structure: ai.structure,
        confidence: ai.confidence,
        conciseness: ai.conciseness,
      };
      feedback = ai.feedback;
      feedbackSource = "ai";
    }
  }
  if (feedbackSource === "checklist") {
    const topicKeywords = current.topic.toLowerCase().split(/[^a-z]+/).filter(Boolean);
    const checked = scoreAnswerChecklist(current.question, answer, topicKeywords);
    scores = {
      relevance: checked.relevance,
      depth: checked.depth,
      structure: checked.structure,
      confidence: checked.confidence,
      conciseness: checked.conciseness,
    };
    feedback = checked.feedback;
  }
  const overall = Math.round(
    scores.relevance * 0.3 +
      scores.depth * 0.25 +
      scores.structure * 0.2 +
      scores.confidence * 0.15 +
      scores.conciseness * 0.1
  );
  transcript[index] = { ...current, answer, feedback, scores, overall };

  const done = transcript.every((t) => t.answer !== null);
  let report: Record<string, unknown> | null = null;
  let overallScore: number | null = null;
  if (done) {
    const answered = transcript.filter((t) => t.overall !== null);
    overallScore = Math.round(
      answered.reduce((s, t) => s + (t.overall ?? 0), 0) / Math.max(1, answered.length)
    );
    const byTopic = new Map<string, number[]>();
    for (const t of answered) {
      const arr = byTopic.get(t.topic) ?? [];
      arr.push(t.overall ?? 0);
      byTopic.set(t.topic, arr);
    }
    const topicScores = [...byTopic.entries()].map(([topic, vals]) => ({
      topic,
      score: Math.round(vals.reduce((s, v) => s + v, 0) / vals.length),
    }));
    const weakest = [...topicScores].sort((a, b) => a.score - b.score).slice(0, 2);
    report = {
      topic_scores: topicScores,
      weakest_areas: weakest.map((w) => w.topic),
      weakest_question: [...answered].sort((a, b) => (a.overall ?? 0) - (b.overall ?? 0))[0] ?? null,
      feedback_source: feedbackSource,
    };
  }

  const supabase = getServiceClient()!;
  const update: Record<string, unknown> = { transcript };
  if (done) {
    update.status = "completed";
    update.overall_score = overallScore;
    update.report = report;
  }
  const { data, error: dbError } = await supabase
    .from("mock_sessions")
    .update(update)
    .eq("id", id)
    .eq("user_id", userId)
    .select("id, status, overall_score, transcript, report")
    .single();
  if (dbError) return errorJson("db_failed", "Could not save the answer.", 502);

  const next = done ? null : transcript.find((t) => t.answer === null) ?? null;
  return NextResponse.json({
    feedback,
    scores,
    overall,
    feedback_source: feedbackSource,
    completed: done,
    next_question: next ? { question: next.question, topic: next.topic } : null,
    report,
    session: data,
  });
}
