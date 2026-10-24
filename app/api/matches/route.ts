import { NextResponse } from "next/server";
import { getServiceClient } from "@/lib/supabase/server";
import { errorJson, requireUser, ownedRow, audit } from "@/lib/api/helpers";
import { scoreResume, type Criterion } from "@/lib/scoring/engine";

// POST /api/matches — run the deterministic scoring engine on an owned
// resume + an owned JD whose criteria the candidate already approved.
export async function POST(request: Request) {
  const { userId, error } = await requireUser();
  if (userId === null) return error;
  const body = await request.json().catch(() => null);
  const resumeId = typeof body?.resume_id === "string" ? body.resume_id : "";
  const jdId = typeof body?.jd_id === "string" ? body.jd_id : "";
  if (!resumeId || !jdId) return errorJson("bad_input", "resume_id and jd_id are required.", 400);

  const resume = await ownedRow("resumes", resumeId, userId, "id, sections, parse_status");
  const jd = await ownedRow("job_descriptions", jdId, userId, "id, title, criteria");
  if (!resume || !jd) return errorJson("not_found", "Resume or job description not found.", 404);
  if (resume.parse_status !== "parsed") {
    return errorJson("not_parsed", "This resume has not been parsed successfully yet.", 409);
  }
  const criteria = (jd.criteria ?? []) as Criterion[];
  if (criteria.length === 0) {
    return errorJson("no_criteria", "This JD has no criteria yet. Extract or add criteria first.", 409);
  }

  const result = scoreResume((resume.sections ?? {}) as Record<string, string>, criteria);
  const supabase = getServiceClient()!;
  const { data, error: dbError } = await supabase
    .from("match_analyses")
    .insert({
      user_id: userId,
      resume_id: resumeId,
      jd_id: jdId,
      match_score: result.match_score,
      criteria_results: result.criteria_results,
      gaps: result.gaps,
    })
    .select("id, resume_id, jd_id, match_score, criteria_results, gaps, created_at")
    .single();
  if (dbError) return errorJson("db_failed", "Could not save the analysis.", 502);
  await audit(userId, "match_run", "match_analyses", data.id);
  return NextResponse.json({ analysis: data }, { status: 201 });
}

// GET /api/matches — recent analyses with JD titles (newest first).
export async function GET() {
  const { userId, error } = await requireUser();
  if (userId === null) return error;
  const supabase = getServiceClient()!;
  const { data, error: dbError } = await supabase
    .from("match_analyses")
    .select("id, resume_id, jd_id, match_score, gaps, created_at, job_descriptions(title, company)")
    .eq("user_id", userId)
    .order("created_at", { ascending: false })
    .limit(20);
  if (dbError) return errorJson("db_failed", "Could not load analyses.", 502);
  return NextResponse.json({ analyses: data ?? [] });
}
