import { NextResponse } from "next/server";
import { getServiceClient } from "@/lib/supabase/server";
import { errorJson, requireUser } from "@/lib/api/helpers";

// PATCH /api/rewrites/:id — accept (or un-accept) a rewrite suggestion.
// Ownership is enforced via the parent analysis's user_id.
export async function PATCH(
  request: Request,
  context: { params: Promise<{ id: string }> }
) {
  const { userId, error } = await requireUser();
  if (userId === null) return error;
  const { id } = await context.params;
  const body = await request.json().catch(() => null);
  if (typeof body?.accepted !== "boolean") {
    return errorJson("bad_input", "accepted must be true or false.", 400);
  }
  const supabase = getServiceClient()!;
  const { data: rewrite } = await supabase
    .from("resume_rewrites")
    .select("id, analysis_id, match_analyses(user_id)")
    .eq("id", id)
    .single();
  const owner = (rewrite?.match_analyses as { user_id?: string } | null)?.user_id;
  if (!rewrite || owner !== userId) return errorJson("not_found", "Rewrite not found.", 404);
  const { data, error: dbError } = await supabase
    .from("resume_rewrites")
    .update({ accepted: body.accepted })
    .eq("id", id)
    .select("id, original_bullet, rewritten_bullet, accepted")
    .single();
  if (dbError) return errorJson("db_failed", "Could not update rewrite.", 502);
  return NextResponse.json({ rewrite: data });
}
