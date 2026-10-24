import { NextResponse } from "next/server";
import { getServiceClient } from "@/lib/supabase/server";
import { errorJson, requireUser } from "@/lib/api/helpers";
import { extractCriteriaHeuristic } from "@/lib/scoring/extract";

// POST /api/jds — save a JD; criteria are drafted immediately with the
// heuristic extractor so the candidate can edit them before scoring.
export async function POST(request: Request) {
  const { userId, error } = await requireUser();
  if (userId === null) return error;
  const body = await request.json().catch(() => null);
  const title = typeof body?.title === "string" ? body.title.trim() : "";
  const rawText = typeof body?.raw_text === "string" ? body.raw_text : "";
  const company = typeof body?.company === "string" ? body.company.trim() : "";
  if (!title || rawText.trim().length < 30) {
    return errorJson("bad_input", "A title and a job description of at least 30 characters are required.", 400);
  }
  const supabase = getServiceClient()!;
  const criteria = extractCriteriaHeuristic(rawText);
  const { data, error: dbError } = await supabase
    .from("job_descriptions")
    .insert({ user_id: userId, title, company: company || null, raw_text: rawText, criteria })
    .select("id, title, company, raw_text, criteria, created_at")
    .single();
  if (dbError) return errorJson("db_failed", "Could not save the job description.", 502);
  return NextResponse.json({ jd: data, criteria_source: "heuristic" }, { status: 201 });
}

// GET /api/jds — list my JDs (newest first).
export async function GET() {
  const { userId, error } = await requireUser();
  if (userId === null) return error;
  const supabase = getServiceClient()!;
  const { data, error: dbError } = await supabase
    .from("job_descriptions")
    .select("id, title, company, criteria, created_at")
    .eq("user_id", userId)
    .order("created_at", { ascending: false });
  if (dbError) return errorJson("db_failed", "Could not load job descriptions.", 502);
  return NextResponse.json({ jds: data ?? [] });
}
