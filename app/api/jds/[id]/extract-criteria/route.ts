import { NextResponse } from "next/server";
import { getServiceClient } from "@/lib/supabase/server";
import { errorJson, requireUser, ownedRow } from "@/lib/api/helpers";
import { extractCriteriaHeuristic } from "@/lib/scoring/extract";
import { extractCriteriaAi, isGroqConfigured } from "@/lib/ai/groq";

// POST /api/jds/:id/extract-criteria — (re)extract criteria for a JD.
// AI first when a Groq key is configured, heuristic fallback otherwise.
// The result is a DRAFT: the candidate edits it before any scoring runs.
export async function POST(
  _request: Request,
  context: { params: Promise<{ id: string }> }
) {
  const { userId, error } = await requireUser();
  if (userId === null) return error;
  const { id } = await context.params;
  const jd = await ownedRow("job_descriptions", id, userId, "id, raw_text");
  if (!jd) return errorJson("not_found", "Job description not found.", 404);

  let criteria = null;
  let source = "heuristic";
  if (isGroqConfigured()) {
    const ai = await extractCriteriaAi(jd.raw_text as string);
    if (ai) {
      criteria = ai;
      source = "ai";
    }
  }
  if (!criteria) criteria = extractCriteriaHeuristic(jd.raw_text as string);

  const supabase = getServiceClient()!;
  const { data, error: dbError } = await supabase
    .from("job_descriptions")
    .update({ criteria })
    .eq("id", id)
    .eq("user_id", userId)
    .select("id, criteria")
    .single();
  if (dbError) return errorJson("db_failed", "Could not save criteria.", 502);
  return NextResponse.json({ jd: data, criteria_source: source, ai_configured: isGroqConfigured() });
}
