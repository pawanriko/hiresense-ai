import { NextResponse } from "next/server";
import { getServiceClient } from "@/lib/supabase/server";
import { errorJson, requireUser, ownedRow } from "@/lib/api/helpers";
import { pickQuestions, TRACKS, type Track } from "@/lib/interview/questions";
import { interviewQuestionsAi, isGroqConfigured } from "@/lib/ai/groq";

// POST /api/interviews — start a mock session (5 questions, one at a time).
// AI questions when Groq is configured, otherwise the deterministic bank.
export async function POST(request: Request) {
  const { userId, error } = await requireUser();
  if (userId === null) return error;
  const body = await request.json().catch(() => null);
  const track = (typeof body?.track === "string" ? body.track : "") as Track;
  const difficulty = typeof body?.difficulty === "string" ? body.difficulty : "medium";
  const resumeId = typeof body?.resume_id === "string" ? body.resume_id : null;
  const jdId = typeof body?.jd_id === "string" ? body.jd_id : null;
  if (!TRACKS.includes(track)) {
    return errorJson("bad_input", `track must be one of: ${TRACKS.join(", ")}.`, 400);
  }
  if (!["easy", "medium", "hard"].includes(difficulty)) {
    return errorJson("bad_input", "difficulty must be easy, medium, or hard.", 400);
  }

  let resumeText = "";
  let jdText = "";
  if (resumeId) {
    const resume = await ownedRow("resumes", resumeId, userId, "parsed_text");
    resumeText = (resume?.parsed_text as string | null) ?? "";
  }
  if (jdId) {
    const jd = await ownedRow("job_descriptions", jdId, userId, "raw_text");
    jdText = (jd?.raw_text as string | null) ?? "";
  }

  let questions: { question: string; topic: string }[] | null = null;
  let source = "bank";
  if (isGroqConfigured()) {
    const ai = await interviewQuestionsAi(track, difficulty, resumeText, jdText);
    if (ai) {
      questions = ai;
      source = "ai";
    }
  }
  if (!questions) {
    questions = pickQuestions(track, difficulty).map((q) => ({
      question: q.question,
      topic: q.topic,
    }));
  }

  const transcript = questions.map((q) => ({
    question: q.question,
    topic: q.topic,
    answer: null as string | null,
    feedback: null as string | null,
    scores: null as Record<string, number> | null,
    overall: null as number | null,
  }));

  const supabase = getServiceClient()!;
  const { data, error: dbError } = await supabase
    .from("mock_sessions")
    .insert({
      user_id: userId,
      resume_id: resumeId,
      jd_id: jdId,
      track,
      difficulty,
      status: "in_progress",
      transcript,
    })
    .select("id, track, difficulty, status, transcript, created_at")
    .single();
  if (dbError) return errorJson("db_failed", "Could not start the interview.", 502);
  return NextResponse.json({ session: data, question_source: source }, { status: 201 });
}

// GET /api/interviews — my sessions (newest first).
export async function GET() {
  const { userId, error } = await requireUser();
  if (userId === null) return error;
  const supabase = getServiceClient()!;
  const { data, error: dbError } = await supabase
    .from("mock_sessions")
    .select("id, track, difficulty, status, overall_score, created_at")
    .eq("user_id", userId)
    .order("created_at", { ascending: false })
    .limit(20);
  if (dbError) return errorJson("db_failed", "Could not load interviews.", 502);
  return NextResponse.json({ sessions: data ?? [] });
}
