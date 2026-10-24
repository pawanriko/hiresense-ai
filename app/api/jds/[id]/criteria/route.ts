import { NextResponse } from "next/server";
import { getServiceClient } from "@/lib/supabase/server";
import { errorJson, requireUser, ownedRow, validCriteria } from "@/lib/api/helpers";

// PUT /api/jds/:id/criteria — save the candidate's edited criteria/weights.
// Scoring only ever runs on the criteria the candidate approved here.
export async function PUT(
  request: Request,
  context: { params: Promise<{ id: string }> }
) {
  const { userId, error } = await requireUser();
  if (userId === null) return error;
  const { id } = await context.params;
  const jd = await ownedRow("job_descriptions", id, userId, "id");
  if (!jd) return errorJson("not_found", "Job description not found.", 404);
  const body = await request.json().catch(() => null);
  const criteria = validCriteria(body?.criteria);
  if (!criteria) {
    return errorJson("bad_input", "Criteria must be a non-empty list with a name and a weight (0–100) each.", 400);
  }
  const supabase = getServiceClient()!;
  const { data, error: dbError } = await supabase
    .from("job_descriptions")
    .update({ criteria })
    .eq("id", id)
    .eq("user_id", userId)
    .select("id, criteria")
    .single();
  if (dbError) return errorJson("db_failed", "Could not save criteria.", 502);
  return NextResponse.json({ jd: data });
}
