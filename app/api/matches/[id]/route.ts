import { NextResponse } from "next/server";
import { errorJson, requireUser, ownedRow } from "@/lib/api/helpers";

// GET /api/matches/:id — full analysis (owned only).
export async function GET(
  _request: Request,
  context: { params: Promise<{ id: string }> }
) {
  const { userId, error } = await requireUser();
  if (userId === null) return error;
  const { id } = await context.params;
  const analysis = await ownedRow(
    "match_analyses",
    id,
    userId,
    "id, resume_id, jd_id, match_score, criteria_results, gaps, created_at, job_descriptions(title, company, raw_text), resumes(file_name, version)"
  );
  if (!analysis) return errorJson("not_found", "Analysis not found.", 404);
  return NextResponse.json({ analysis });
}
